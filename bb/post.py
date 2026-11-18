"""Post: label overlay, optional synthesized SFX and H.264 encoding."""
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def find_font(name):
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", name], capture_output=True, text=True)
        if out.returncode == 0 and os.path.exists(out.stdout.strip()):
            return out.stdout.strip()
    except FileNotFoundError:
        pass
    return None


class Labeler:
    """Bold white label with dark outline + soft drop shadow (the
    channel's '25% Soft' style). Cached per text."""

    def __init__(self, cfg, size):
        o = cfg["overlay"]
        self.enabled = o["enabled"]
        self.W, self.H = size
        self.px = int(o["size"] * self.H)
        path = find_font(o["font"])
        self.font = ImageFont.truetype(path, self.px) if path else ImageFont.load_default(self.px)
        self.y = o["y"]
        self.stroke = max(1, int(o["stroke"] * self.px))
        self.cache = {}

    def layer(self, text):
        if text in self.cache:
            return self.cache[text]
        W, H = self.W, self.H
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        bbox = d.textbbox((0, 0), text, font=self.font, stroke_width=self.stroke)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (W - tw) / 2 - bbox[0]
        y = self.y * H - th / 2 - bbox[1]
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x, y + self.px * 0.06), text, font=self.font, fill=(20, 10, 15, 150),
                                stroke_width=self.stroke, stroke_fill=(20, 10, 15, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(self.px * 0.06))
        lay.alpha_composite(sh)
        d.text((x, y), text, font=self.font, fill=(255, 255, 255, 255),
               stroke_width=self.stroke, stroke_fill=(38, 30, 34, 255))
        self.cache[text] = lay
        return lay

    def apply(self, img, text):
        if not self.enabled or not text:
            return img
        im = img.convert("RGBA")
        im.alpha_composite(self.layer(text))
        return im.convert("RGB")


# ---------------------------------------------------------------- audio
def synth_audio(impacts, steps, fps, total_frames, path, volume=0.8, sr=44100):
    """Soft procedural SFX: metallic 'tink' for hard impacts, low squish
    for soft ones, plus a soft click when the label changes."""
    n = int(total_frames / fps * sr) + sr
    out = np.zeros(n)
    rng = np.random.default_rng(3)

    def add(at, sig):
        i = int(at * sr)
        j = min(n, i + len(sig))
        out[i:j] += sig[:j - i]

    for f in range(total_frames):
        si = min(f // (total_frames // len(steps)), len(steps) - 1)
        s = steps[si]["softness"]
        for amp in impacts.get(f, []):
            if amp < 1.2:
                continue
            a = min(1.0, amp / 7.0)
            t = np.arange(int(0.35 * sr)) / sr
            if s < 0.4:
                sig = sum(np.sin(2 * np.pi * fr * t) * np.exp(-t * dc) * w
                          for fr, dc, w in ((1850, 18, 0.5), (3120, 26, 0.3), (5400, 40, 0.15)))
                sig += np.sin(2 * np.pi * 110 * t) * np.exp(-t * 30) * 0.6
            else:
                noise = rng.standard_normal(len(t))
                k = np.exp(-t * (25 - 12 * s))
                ker = np.ones(int(30 + 120 * s)) / (30 + 120 * s)
                sig = np.convolve(noise, ker, "same") * k * 6
                sig += np.sin(2 * np.pi * (140 - 80 * t) * t) * np.exp(-t * 14) * 0.7
            add(f / fps, sig * a * (1 - 0.4 * s))
    for i in range(len(steps)):
        t = np.arange(int(0.08 * sr)) / sr
        add(i * total_frames / len(steps) / fps, np.sin(2 * np.pi * 900 * t) * np.exp(-t * 60) * 0.25)
    peak = np.abs(out).max() or 1.0
    out = np.tanh(out / peak * 1.5) / np.tanh(1.5) * volume * 0.9
    pcm = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- encode
def encode(frame_paths, labels, cfg, out_path, audio_path=None):
    W, H = cfg["render"]["resolution"]
    fps = cfg["render"]["fps"]
    lab = Labeler(cfg, (W, H))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if audio_path:
        cmd += ["-i", audio_path]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(cfg["render"]["crf"]),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart"]
    if audio_path:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for p, text in zip(frame_paths, labels):
        img = Image.open(p).convert("RGB")
        if img.size != (W, H):
            img = img.resize((W, H), Image.LANCZOS)
        img = lab.apply(img, text)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
