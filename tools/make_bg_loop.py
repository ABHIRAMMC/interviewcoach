"""Render the app's background video: an 8-second, seamless HD loop of magenta-purple
particles drifting through darkness.

Everything is generated in code (no downloads, no stock footage) and piped straight into
ffmpeg, so the committed `static/bg.mp4` can always be rebuilt with:

    python tools/make_bg_loop.py

Requires numpy + Pillow, and an ffmpeg binary (pip install imageio-ffmpeg works too --
this script finds it automatically).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

W, H = 1920, 1080          # HD
FPS = 24
SECONDS = 8
FRAMES = FPS * SECONDS
MARGIN = 140               # off-screen band where particles wrap (and fade out)
PERIOD = H + 2 * MARGIN    # vertical travel per loop -> guarantees a seamless loop

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
BG = np.array([5, 3, 14], dtype=np.float32)           # near-black plum, matches the app theme

MAGENTA = np.array([255, 60, 172], dtype=np.float32)
PURPLE = np.array([124, 77, 255], dtype=np.float32)
VIOLET = np.array([186, 104, 255], dtype=np.float32)
PINK = np.array([255, 159, 243], dtype=np.float32)
PALETTE = [MAGENTA, PURPLE, VIOLET, PINK, np.array([224, 75, 255], dtype=np.float32)]


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover - environment without ffmpeg
        sys.exit("No ffmpeg found. Install ffmpeg or `pip install imageio-ffmpeg`.")


def _nebula(phase: float, small=(120, 68)):
    """Slow breathing magenta/purple haze, computed tiny and upscaled (cheap + smooth)."""
    w, h = small
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = np.zeros((h, w, 3), dtype=np.float32)
    blobs = [
        (0.22, 0.30, 0.55, PURPLE, 0.13),
        (0.78, 0.22, 0.42, MAGENTA, 0.085),
        (0.55, 0.86, 0.60, VIOLET, 0.10),
        (0.05, 0.90, 0.38, MAGENTA, 0.06),
    ]
    for bx, by, size, colour, strength in blobs:
        cx = (bx + 0.06 * np.sin(2 * np.pi * phase + bx * 7)) * w
        cy = (by + 0.05 * np.cos(2 * np.pi * phase + by * 5)) * h
        radius = size * w
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * radius ** 2)
        breathe = 0.75 + 0.25 * np.sin(2 * np.pi * phase + by * 3)
        out += np.exp(-d2)[..., None] * colour * (strength * breathe)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
    return img.resize((W, H), Image.BICUBIC)


def _particles(count: int = 170, seed: int = 11):
    """Particle table. Vertical speed is an exact multiple of PERIOD/SECONDS so every
    particle lands back where it started after 8 seconds -> the loop has no seam."""
    rnd = np.random.default_rng(seed)
    speed_unit = PERIOD / SECONDS
    depth = rnd.random(count) ** 1.5                       # bias toward small/far
    layer = np.where(depth < 0.55, 0, np.where(depth < 0.88, 1, 2))
    speed = np.where(layer == 0, speed_unit, np.where(layer == 1, speed_unit, 2 * speed_unit))
    return dict(
        x=rnd.random(count) * (W + 240) - 120,
        y=rnd.random(count) * PERIOD - MARGIN,
        depth=depth,
        speed=speed,
        sigma=4.0 + 34.0 * depth ** 1.4,
        alpha=0.12 + 0.40 * depth,
        colour=np.array([PALETTE[int(c)] for c in rnd.integers(0, len(PALETTE), count)]),
        sway_amp=rnd.uniform(10, 90, count),
        sway_phase=rnd.random(count) * 2 * np.pi,
        sway_freq=rnd.integers(1, 3, count),
        twinkle_phase=rnd.random(count) * 2 * np.pi,
    )


def _splat(buf, cx, cy, sigma, colour, alpha):
    """Additive soft disc (gaussian falloff) with a local bounding box."""
    r = int(np.ceil(sigma * 3.4))   # wide enough that the kernel edge is invisible
    bh, bw = buf.shape[:2]
    x0, x1 = max(0, int(cx) - r), min(bw, int(cx) + r + 1)
    y0, y1 = max(0, int(cy) - r), min(bh, int(cy) + r + 1)
    if x0 >= x1 or y0 >= y1:
        return
    yy = np.arange(y0, y1, dtype=np.float32)[:, None] - cy
    xx = np.arange(x0, x1, dtype=np.float32)[None, :] - cx
    k = np.exp(-(xx * xx + yy * yy) / (2 * sigma * sigma))
    k *= alpha
    buf[y0:y1, x0:x1] += k[..., None] * colour


def _stars(seed: int = 5, count: int = 260):
    rnd = np.random.default_rng(seed)
    return dict(x=rnd.integers(0, W, count), y=rnd.integers(0, H, count),
                r=rnd.integers(1, 3, count), phase=rnd.random(count) * 2 * np.pi)


STARS = _stars()


def frame(i: int, parts) -> Image.Image:
    t = i / FPS
    phase = i / FRAMES

    img = np.array(_nebula(phase), dtype=np.float32) + BG
    buf = np.zeros((H, W, 3), dtype=np.float32)

    # twinkling starfield (period = one loop)
    for x, y, r, ph in zip(STARS["x"], STARS["y"], STARS["r"], STARS["phase"]):
        tw = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * phase + ph))
        _splat(buf, x, y, 1.1 + r * 0.6, PINK if r > 1 else np.array([220, 220, 255], np.float32),
               0.09 * tw)

    sw = np.sin(2 * np.pi * parts["sway_freq"] * phase + parts["sway_phase"]) * parts["sway_amp"]
    ys = (parts["y"] - parts["speed"] * t + MARGIN) % PERIOD - MARGIN     # exact loop
    twinkle = 0.72 + 0.28 * np.sin(2 * np.pi * phase + parts["twinkle_phase"])
    for n in range(len(parts["x"])):
        y = ys[n]
        fade = np.clip(min((y + MARGIN) / 60.0, (H + MARGIN - y) / 60.0), 0.0, 1.0)
        if fade <= 0:
            continue
        _splat(buf, parts["x"][n] + sw[n], y, parts["sigma"][n],
               parts["colour"][n], parts["alpha"][n] * fade * twinkle[n])

    glow = Image.fromarray(np.clip(buf, 0, 255).astype(np.uint8), "RGB")
    img += np.array(glow, dtype=np.float32)
    bloom = glow.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
    img += 0.45 * np.array(bloom.resize((W, H), Image.BICUBIC), dtype=np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def main():
    STATIC.mkdir(exist_ok=True)
    parts = _particles()
    out = STATIC / "bg.mp4"
    cmd = [
        _ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "slower", "-crf", "30", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-g", str(FPS * 2), "-profile:v", "high", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    poster_written = False
    for i in range(FRAMES):
        im = frame(i, parts)
        if not poster_written:
            im.save(STATIC / "bg.jpg", quality=82, optimize=True)
            poster_written = True
        proc.stdin.write(im.tobytes())
        if i % 24 == 0:
            print(f"  frame {i}/{FRAMES}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    size = out.stat().st_size / 1024
    print(f"{out.relative_to(ROOT)}  {size:.0f} KB  ({SECONDS}s, {W}x{H}, {FPS}fps, seamless)")


if __name__ == "__main__":
    main()
