import json, subprocess, sys
SRC = sys.argv[1]; OUT = sys.argv[2]; DUR = 73.933
# паузы между предложениями: (начало, конец, сколько паузы оставить)
P = [(8.64, 9.34, .2), (15.06, 15.98, .2), (25.84, 26.48, .2), (32.68, 33.68, .2), (35.8, 36.78, .2),
     (46.5, 47.6, .2), (54.96, 55.74, .2), (60.98, 61.76, .45), (63.28, 64.72, .25), (66.6, 67.5, .2)]
# план для каждого куска между склейками (1.0 — общий, больше — ближе)
Z = [1.0, 1.12, 1.2, 1.0, 1.3, 1.0, 1.12, 1.0, 1.3, 1.0, 1.12]   # где фото (куски 0 и 3) — общий план
keep, t = [], 0.0
for a, b, k in P:
    cut_a = round((a + k / 2) * 30) / 30; cut_b = round((b - k / 2) * 30) / 30
    keep.append((t, cut_a)); t = cut_b
keep.append((t, round(DUR * 30) / 30))
fc, cc = '', ''
for i, (a, b) in enumerate(keep):
    fc += f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b-a-0.012:.3f}:d=0.012[a{i}];"
    cc += f"[v{i}][a{i}]"
fc += f"{cc}concat=n={len(keep)}:v=1:a=1[v][a]"
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '12', '-c:a', 'aac', '-b:a', '256k', OUT], check=True)
segs, t = [], 0.0
for (a, b), z in zip(keep, Z):
    n = round((b - a) * 30) / 30
    segs.append({'s': round(t, 3), 'e': round(t + (b - a), 3), 'z': z}); t += b - a
json.dump(segs, open(OUT + '.segs.json', 'w'), indent=1)
print(len(keep), 'segments', round(t, 2), 's')
