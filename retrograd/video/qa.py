"""Проверка готового видео перед отправкой."""
import subprocess, sys, json, wave, numpy as np
V = sys.argv[1]; CUTS = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] else []
PHOTO = [float(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[3] else []
ok = True
def bad(msg):
    global ok; ok = False; print('  ✗', msg)
pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,duration,r_frame_rate,color_space,nb_frames:format=duration',
                                '-of', 'json', V], capture_output=True, text=True).stdout)
vs = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]; as_ = [s for s in pr['streams'] if s['codec_type'] == 'audio'][0]
vd, ad = float(vs['duration']), float(as_['duration'])
print(f"1. Формат: {vs['width']}x{vs['height']}, {vs['r_frame_rate']} кадр/с, цвет {vs.get('color_space')}, видео {vd:.2f} c, звук {ad:.2f} c")
if (vs['width'], vs['height']) != (1080, 1920): bad('размер не 1080x1920')
if vs.get('color_space') != 'bt709': bad('цветовое пространство не bt709')
if abs(vd - ad) > 0.1: bad(f'длина звука и видео расходится на {abs(vd-ad):.2f} c')
# кадры
b = subprocess.run(['ffmpeg', '-v', 'error', '-i', V, '-vf', 'scale=96:170,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
f = np.frombuffer(b, np.uint8).reshape(-1, 170, 96).astype(np.float32)
d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)); med = float(np.median(d))
dupes = [round((i + 1) / 30, 2) for i in np.where(d < 0.02)[0]]
print(f"2. Повторяющиеся (застывшие) кадры: {len(dupes)}")
if dupes: bad(f'повторы кадров на {dupes[:10]}')
spikes = [(i + 1) / 30 for i in np.where(d > med * 4)[0]]
near = lambda t, L, w: any(abs(t - x) < w for x in L)
unexpected = [round(t, 2) for t in spikes if not near(t, CUTS, 0.04) and not near(t, PHOTO, 0.45)]
print(f"3. Резкие изменения кадра: {len(spikes)}, из них неожиданных (не склейка и не фото): {len(unexpected)}")
for c in CUTS:
    k = round(c * 30); win = d[k - 3:k + 3]; n_big = int((win > med * 4).sum())
    if n_big != 1: bad(f'склейка {c:.2f} c: {n_big} резких кадров вместо одного (дёрганье)')
if unexpected: print('   (проверить глазами:', unexpected[:12], ')')
# звук: щелчки/обрывы на стыках
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', V, '-ac', '1', '-ar', '48000', '/tmp/qa.wav'])
w = wave.open('/tmp/qa.wav'); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
jumps = np.abs(np.diff(x)); thr = max(0.25, float(np.percentile(jumps, 99.99)) * 1.5)
pops = [round(i / 48000, 2) for i in np.where(jumps > thr)[0]]
print(f"4. Звук: пик {np.abs(x).max():.2f}, щелчки-обрывы: {len(pops)}")
if np.abs(x).max() > 0.99: bad('звук перегружен (клиппинг)')
if pops: bad(f'резкие скачки звука на {pops[:10]}')
for c in CUTS:
    i = int(c * 48000); seg = x[i - 2400:i + 2400]
    if len(seg) and np.abs(np.diff(seg)).max() > 0.3: bad(f'щелчок звука на склейке {c:.2f} c')
print('ИТОГ:', 'всё чисто' if ok else 'есть проблемы')
