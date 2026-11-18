"""Configuration: defaults reproduce the reference look; a YAML file only
needs to override what changes."""
import copy
import os
import yaml

DEFAULTS = {
    "name": "video",
    "output": "renders/{name}.mp4",
    "seed": 7,
    "render": {
        "resolution": [1080, 1920],   # final video size
        "render_scale": 0.6667,       # frames are rendered at this fraction and
                                      # upscaled on encode (1.0 = native, ~2.3x slower)
        "threads": 0,                 # 0 = all cores
        "persistent_data": False,     # faster, but Cycles 5.x corrupts shaders over long runs
        "fps": 30,
        "samples": 20,
        "adaptive_threshold": 0.03,
        "denoise": True,
        "view_transform": "AgX",
        "look": "AgX - Base Contrast",
        "exposure": 0.0,
        "crf": 16,
        "piece_subdivision": 2,   # render-time smoothing of the soft pieces
        "motion_blur": False,
        "motion_blur_shutter": 0.35,
    },
    "camera": {
        "focal_length": 76.0,
        "location": [0.0, -6.4, 4.3],
        "target": [0.0, 0.0, 2.38],
        "shift_x": 0.0,
        "shift_y": 0.0,
    },
    "lighting": {
        "preset": "studio_soft",
        "intensity": 1.0,
        "key_angle": 35.0,         # degrees, azimuth of the key softbox (left)
        "background": "#B9A1A8",   # mauve seamless backdrop (sRGB hex)
        "world_strength": 0.25,
    },
    "machine": {
        "pieces": 2,
        "piece_shape": "sphere",   # sphere | capsule | rounded_cube | coin
        "piece_size": 0.26,
        "piece_detail": 4,
        "orientation": -24.0,      # degrees, rotates the whole layout around Z
        "gates": [
            {"radius": 1.0, "height": 3.15, "wire": 0.028, "sleeve": 0.16, "span": 74},
            {"radius": 0.82, "height": 2.42, "wire": 0.026, "sleeve": 0.145, "span": 74},
        ],
        "pedestal": {
            "half_width": 1.1,
            "height": 1.62,
            "hole_radius": 0.205,
            "sink_radius": 0.62,     # gentle conical dish around the hole
            "sink_depth": 0.07,
            "hole_offset": 0.0,      # 0 = one central hole (reference); 'auto' = one hole per piece where it lands
            "trim": 0.05,
        },
        "trim_material": "gold",
        "body_material": "concrete",
    },
    "timing": {
        "step_duration": 3.3,      # seconds (video time) per softness / material step
        "speed": 1.3,              # >1 = snappier motion (machine time per video second)
        "spawn_height": 4.9,
        "gate_close": [0.0, 0.55], # [start, duration] of gates closing (all)
        "gate_open": [1.0, 2.25],  # start time of each gate opening
        "gate_turn": 0.75,          # duration of a gate turn
        "substeps": 14,
    },
    "progression": {
        "label": "{pct}% Soft",
        # shorthand (expanded to steps when 'steps' is empty)
        "softness": [0.0, 0.25, 0.5, 0.75, 1.0],
        "materials": ["gold"],
        "steps": [],
        "morph": {"mode": "spread", "duration": 0.9},
    },
    "effects": {
        "deform_intensity": 1.0,   # multiplies softness
        "texture_detail": 1.0,     # multiplies bump/micro detail
    },
    "overlay": {
        "enabled": True,
        "font": "Inter Black",
        "size": 0.072,             # fraction of frame height
        "y": 0.165,                # vertical centre, fraction of height
        "stroke": 0.11,            # stroke width as fraction of font size
    },
    "audio": {"enabled": False, "volume": 0.8},
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load(path=None, overrides=None):
    data = {}
    if path:
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        data.setdefault("name", os.path.splitext(os.path.basename(path))[0])
    cfg = deep_merge(DEFAULTS, data)
    cfg = deep_merge(cfg, overrides or {})
    cfg["output"] = cfg["output"].format(name=cfg["name"])
    pr = cfg["progression"]
    if not pr["steps"]:
        mats = pr["materials"] or ["gold"]
        soft = pr["softness"] or [0.0]
        n = max(len(mats), len(soft))
        pr["steps"] = [{"softness": soft[min(i, len(soft) - 1)],
                        "material": mats[min(i, len(mats) - 1)]} for i in range(n)]
    for st in pr["steps"]:
        st.setdefault("softness", 0.0)
        st.setdefault("material", "gold")
        if "label" not in st:
            st["label"] = pr["label"].format(
                pct=int(round(st["softness"] * 100)),
                material=st["material"].replace("_", " ").title())
    return cfg
