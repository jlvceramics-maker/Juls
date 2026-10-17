"""Fake dolly zoom (vertigo) on a talking-head clip.

The person is cut out with Apple Vision (personmask.swift), the background behind them
is rebuilt from a clean plate, then only the background is scaled around the frame centre
while the person keeps the same size. Background grows = camera pulls back while zooming in.

    python3 scripts/dollyzoom.py <in.mp4> <out.mp4> [start end scale]
"""
import json, math, os, shutil, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, SR = 30, 48000


def run(cmd): subprocess.run(cmd, check=True)


def ease(x):  # in-out cubic, as in camera-kit.js
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def scale_at(t, start, end, scale):  # log interpolation: no braking towards the end
    k = ease((t - start) / (end - start))
    return math.exp(math.log(scale) * k)


def push_pull(img, known):
    """Fill unknown pixels from their surroundings (plain wall -> smooth fill)."""
    levels, cur_i, cur_w = [], img * known[..., None], known.astype(np.float32)
    while min(cur_w.shape) > 4:
        levels.append((cur_i, cur_w))
        h, w = cur_w.shape[0] // 2 * 2, cur_w.shape[1] // 2 * 2
        ci, cw = cur_i[:h, :w], cur_w[:h, :w]
        cur_i = (ci[0::2, 0::2] + ci[1::2, 0::2] + ci[0::2, 1::2] + ci[1::2, 1::2])
        cur_w = (cw[0::2, 0::2] + cw[1::2, 0::2] + cw[0::2, 1::2] + cw[1::2, 1::2])
    filled = cur_i / np.maximum(cur_w, 1e-6)[..., None]
    for ci, cw in reversed(levels):
        up = np.repeat(np.repeat(filled, 2, 0), 2, 1)
        up = np.pad(up, ((0, ci.shape[0] - up.shape[0]), (0, ci.shape[1] - up.shape[1]), (0, 0)), mode="edge")
        a = np.clip(cw, 0, 1)[..., None]
        filled = a * (ci / np.maximum(cw, 1e-6)[..., None]) + (1 - a) * up
    return filled


def whoosh(dur, start, end, path):
    """Rising tone 110 -> 520 Hz plus rising noise over the move (camera-moves: sound of dolly zoom)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.clip((t - start) / (end - start), 0, 1)
    f = 110 * (520 / 110) ** k
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    rng = np.random.default_rng(7)
    noise = np.convolve(rng.standard_normal(n), np.ones(24) / 24, mode="same")
    env = np.where(t < start, 0, np.where(t < end, k ** 1.6, np.exp(-(t - end) / 0.18)))
    sig = (0.55 * tone + 0.9 * noise) * env * 0.22
    pcm = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def apply(src, out, start=0.2, end=2.2, scale=1.45):
    work = out + ".work"
    shutil.rmtree(work, ignore_errors=True)
    fr, mk = f"{work}/frames", f"{work}/masks"
    os.makedirs(fr)
    run(["ffmpeg", "-v", "error", "-i", src, f"{fr}/%05d.png"])
    tool = f"{HERE}/.personmask"
    if not os.path.exists(tool):
        run(["swiftc", "-O", f"{HERE}/personmask.swift", "-o", tool])
    run([tool, fr, mk])
    names = sorted(os.listdir(fr))

    def load(n):
        f = np.asarray(Image.open(f"{fr}/{n}").convert("RGB"), np.float32)
        m = Image.open(f"{mk}/{n}").convert("L")
        h = Image.fromarray(((np.asarray(m.filter(ImageFilter.GaussianBlur(14))) > 4) * 255).astype(np.uint8))
        h = np.asarray(h.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255  # person + margin = hole in the wall
        a = np.asarray(m.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
        return f, a, h

    # clean plate: per pixel average of frames where that pixel is surely wall, holes filled from around
    acc, cnt = None, None
    for n in names:
        f, _, h = load(n)
        k = (h < 0.01).astype(np.float32)
        acc = f * k[..., None] if acc is None else acc + f * k[..., None]
        cnt = k if cnt is None else cnt + k
    seen = (cnt > 0).astype(np.float32)
    plate = acc / np.maximum(cnt, 1)[..., None]
    # never-seen wall gets the wall's own colour row by row (bright pixels only), not a smear of the painting
    lum = plate.mean(2)
    wall = np.zeros_like(plate)
    for y in range(plate.shape[0]):
        ok = seen[y] > 0
        if ok.sum() < 20: continue
        l = lum[y][ok]
        pick = plate[y][ok][l >= np.percentile(l, 60)]
        wall[y] = np.median(pick, 0)
    rows = (seen.sum(1) >= 20).astype(np.float32)
    wall = push_pull(wall, np.repeat(rows[:, None], plate.shape[1], 1))
    soft = np.asarray(Image.fromarray(wall.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(20)), np.float32)
    seen = np.asarray(Image.fromarray((seen * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32)[..., None] / 255
    plate = np.where((cnt > 0)[..., None], plate, soft)
    plate = plate * seen + soft * (1 - seen)  # never-seen wall: smooth, no pyramid blocks

    H, W = plate.shape[:2]
    os.makedirs(f"{work}/out")
    for i, n in enumerate(names):
        f, alpha, h = load(n)
        alpha = alpha[..., None]
        t = i / FPS
        s = scale_at(t, start, end, scale)
        if s > 1.0005:
            bg = f * (1 - h[..., None]) + plate * h[..., None]
            bw, bh = round(W * s), round(H * s)
            big = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).resize((bw, bh), Image.LANCZOS)
            x0, y0 = (bw - W) // 2, (bh - H) // 2
            bg = np.asarray(big.crop((x0, y0, x0 + W, y0 + H)), np.float32)
            f = f * alpha + bg * (1 - alpha)
        Image.fromarray(f.clip(0, 255).astype(np.uint8)).save(f"{work}/out/{i:05d}.png")

    dur = len(names) / FPS
    whoosh(dur, start, end, f"{work}/whoosh.wav")
    run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", f"{work}/out/%05d.png", "-i", src,
         "-i", f"{work}/whoosh.wav",
         "-filter_complex", "[2:a]aresample=48000,pan=stereo|c0=c0|c1=c0[w];[1:a][w]amix=inputs=2:normalize=0:duration=first[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out])
    shutil.rmtree(work)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    apply(a[0], a[1], *map(float, a[2:5]))
