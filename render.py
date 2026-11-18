#!/usr/bin/env python3
"""Bounty Balls video generator.

    python3 render.py configs/soft_gold.yaml              # full quality
    python3 render.py configs/soft_gold.yaml --preview    # fast low-res check
    python3 render.py configs/soft_gold.yaml --still 75   # single frame PNG
    python3 render.py configs/x.yaml --set timing.speed=1.2 --set machine.pieces=3

Pipeline: config -> machine calibration -> soft-body simulation (cached)
-> Blender/Cycles scene -> frames -> label overlay (+ optional SFX)
-> MP4 H.264."""
import argparse
import hashlib
import json
import os
import pickle
import sys
import time

import numpy as np
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from bb import config as C  # noqa: E402
from bb.machine import Machine, ease_in_out  # noqa: E402


def parse_set(items):
    over = {}
    for it in items or []:
        key, _, val = it.partition("=")
        d = over
        parts = key.split(".")
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = yaml.safe_load(val)
    return over


def sim_key(cfg):
    keys = {k: cfg[k] for k in ("machine", "timing", "effects")}
    keys["steps"] = [s["softness"] for s in cfg["progression"]["steps"]]
    keys["fps"] = cfg["render"]["fps"]
    # invalidate the cache when the simulation code itself changes
    for mod in ("machine", "softbody", "colliders", "meshgen"):
        with open(os.path.join(ROOT, "bb", mod + ".py"), "rb") as fh:
            keys[mod] = hashlib.sha1(fh.read()).hexdigest()
    return hashlib.sha1(json.dumps(keys, sort_keys=True, default=str).encode()).hexdigest()[:12]


def material_state(cfg, mc, f):
    steps = cfg["progression"]["steps"]
    morph = cfg["progression"]["morph"]
    si, lf, t = mc.step_of_frame(f)
    b = steps[si]["material"]
    a = steps[si - 1]["material"] if si > 0 else b
    mode = morph.get("mode", "spread")
    if mode == "cut" or a == b:
        return (b, b, 1.0, "fade")
    prog = ease_in_out(t / max(morph.get("duration", 0.8), 1e-6))
    return (a, b, prog, mode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", nargs="?", default=os.path.join(ROOT, "configs", "soft_gold.yaml"))
    ap.add_argument("--preview", action="store_true", help="half-res, few samples")
    ap.add_argument("--draft", action="store_true", help="tiny & noisy, to check motion fast")
    ap.add_argument("--threads", type=int, help="CPU threads for Cycles")
    ap.add_argument("--still", type=int, help="render a single frame to PNG and exit")
    ap.add_argument("--frames", help="render only a range a:b (for splitting work)")
    ap.add_argument("--set", action="append", help="override, e.g. --set render.samples=32")
    ap.add_argument("--fresh", action="store_true", help="ignore cached simulation and frames")
    ap.add_argument("--no-encode", action="store_true")
    ap.add_argument("--audio", action="store_true", help="add synthesized SFX")
    args = ap.parse_args()

    over = parse_set(args.set)
    if args.preview:
        over = C.deep_merge({"render": {"render_scale": 0.5, "samples": 12}}, over)
    if args.draft:
        over = C.deep_merge({"render": {"render_scale": 0.25, "samples": 3, "denoise": True}}, over)
    if args.threads:
        over = C.deep_merge({"render": {"threads": args.threads}}, over)
    if args.audio:
        over = C.deep_merge({"audio": {"enabled": True}}, over)
    cfg = C.load(args.config, over)
    name = cfg["name"] + ("_preview" if args.preview else "") + ("_draft" if args.draft else "")
    work = os.path.join(ROOT, "work", name)
    frames_dir = os.path.join(work, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    t0 = time.time()
    log = lambda *a: print(f"[{time.time() - t0:7.1f}s]", *a, flush=True)  # noqa: E731

    # ---------------------------------------------------------- simulate
    key = sim_key(cfg)
    cache = os.path.join(ROOT, "work", f"sim_{cfg['name']}_{key}.pkl")
    mc = Machine(cfg)
    if os.path.exists(cache) and not args.fresh:
        with open(cache, "rb") as fh:
            data = pickle.load(fh)
        cfg["machine"]["gates"] = data["gates"]
        hole = data["hole"]
        log(f"simulation loaded from cache ({os.path.basename(cache)})")
    else:
        log("calibrating machine...")
        hole = mc.calibrate(log)
        log(f"simulating {len(cfg['progression']['steps'])} steps, {mc.total_frames} frames...")
        data = mc.simulate(hole, log=log)
        data["gates"] = cfg["machine"]["gates"]
        data["hole"] = hole
        with open(cache, "wb") as fh:
            pickle.dump(data, fh)
    mc = Machine(cfg, hole_offset=hole)

    frames = list(range(mc.total_frames))
    if args.frames:
        a, _, b = args.frames.partition(":")
        frames = frames[int(a or 0):int(b) if b else None]
    if args.still is not None:
        frames = [args.still]

    # ---------------------------------------------------------- render
    import bpy  # noqa: F401  (imported late: heavy)
    from bb.scene import Scene
    log("building scene...")
    sc = Scene(cfg, mc, hole)
    fps = cfg["render"]["fps"]
    for i, f in enumerate(frames):
        path = os.path.join(frames_dir, f"f_{f:04d}.png")
        if args.still is not None:
            path = os.path.join(ROOT, "work", f"{name}_still_{f:04d}.png")
        elif os.path.exists(path) and not args.fresh:
            continue
        soft = cfg["progression"]["steps"][mc.step_of_frame(f)[0]]["softness"] > 0.02
        sc.set_frame(f, data["positions"][f], material_state(cfg, mc, f), f / fps, soft=soft)
        sc.scene.render.filepath = path
        ts = time.time()
        import bpy
        bpy.ops.render.render(write_still=True)
        log(f"frame {f} ({i + 1}/{len(frames)}) {time.time() - ts:.1f}s")
    if args.still is not None:
        log(f"still written: {path}")
        return
    if args.no_encode or args.frames:
        return

    # ---------------------------------------------------------- encode
    from bb.post import encode, synth_audio
    all_frames = range(mc.total_frames)
    paths = [os.path.join(frames_dir, f"f_{f:04d}.png") for f in all_frames]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        log(f"{len(missing)} frames missing, not encoding yet")
        return
    labels = [cfg["progression"]["steps"][mc.step_of_frame(f)[0]]["label"] for f in all_frames]
    audio = None
    if cfg["audio"]["enabled"]:
        audio = os.path.join(work, "sfx.wav")
        synth_audio(data["impacts"], cfg["progression"]["steps"], fps, mc.total_frames,
                    audio, cfg["audio"]["volume"])
    out = cfg["output"]
    if args.preview or args.draft:
        out = out.replace(".mp4", "_draft.mp4" if args.draft else "_preview.mp4")
    out = os.path.join(ROOT, out)
    encode(paths, labels, cfg, out, audio)
    log(f"video written: {out}")


if __name__ == "__main__":
    main()
