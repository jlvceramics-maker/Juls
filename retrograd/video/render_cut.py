import json, subprocess, sys, re, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, WORDS, OUT, VID, FONTS, MODE = sys.argv[1:7]
W, H, FPS = 1080, 1920, 30
INTER = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
PF = FONTS + '/playfair-display-{sub}-{w}-normal.woff'

# ---------- captions ----------
FIX = {'утешителей,': 'Утешитель,', 'святой': 'Святой', 'дух': 'Дух', 'троицы.': 'Троицы.',
       'парельцам': 'по рельсам', 'унес': 'унёс', 'сладче,': 'слаще,', 'сладче': 'слаще,', 'постась': 'ипостась',
       'парель': 'по рельсам', 'называйте': 'называть', 'иностранная': 'индустриальная', 'иностранальная': 'индустриальная', 'бытовое': 'бытовые', 'удобство.': 'удобства.', 'ровазе': 'трава', 'линей.': 'зеленее.', 'парельством,': 'по рельсам,', 'зелени.': 'зеленее.', 'Идолу.': 'идолу.', 'индустриальной': 'индустриальная', 'революции': 'революция', 'от': 'а'}
ACCENT = {'КОМФОРТ', 'КОМФОРТОМ', 'КОМФОРТУ', 'ИДОЛУ', 'СИМВОЛИЧНО', 'РОБОТА', 'ЛЮБИТЬ',
          'УТЕШИТЕЛЬ', 'СВЯТОЙ', 'ДУХ'}

raw = json.load(open(WORDS))['chunks']
words = []
for i, c in enumerate(raw):
    t = c['text'].strip()
    if t == 'и' and i + 1 < len(raw) and raw[i + 1]['text'].strip() == 'постась':
        continue  # whisper split "ипостась" into "и постась"
    if t == 'сам' and i > 0 and raw[i - 1]['text'].strip() == 'парель':
        continue  # "парель сам" -> "по рельсам"
    t = FIX.get(t, t)
    if t.startswith('- '):
        t = t[2:]
    words.append({'t': t, 's': c['timestamp'][0], 'e': c['timestamp'][1]})
if words and (words[-1]['e'] is None):
    words[-1]['e'] = words[-1]['s'] + 0.6

FUNC = {'в', 'и', 'на', 'с', 'об', 'о', 'при', 'для', 'как', 'со', 'а', 'по'}
chunks, cur = [], []
for i, w in enumerate(words):
    if cur:
        prev = cur[-1]
        text_len = sum(len(x['t']) for x in cur) + len(w['t'])
        glue = prev['t'].lower() in FUNC  # не оставляем предлог/союз в конце строки
        if (re.search(r'[.,!?—]$', prev['t']) or w['s'] - prev['e'] > 0.35
                or (not glue and (len(cur) >= 3 or text_len > 15)) or text_len > 20):
            carry = []
            if len(cur) > 1 and cur[-1]['t'].lower() in FUNC and not re.search(r'[.,!?—]$', cur[-1]['t']):
                carry = [cur.pop()]  # предлог/союз переносим в следующую строку
            chunks.append(cur); cur = carry
    cur.append(w)
chunks.append(cur)
caps = []
for i, ch in enumerate(chunks):
    s = ch[0]['s']
    nxt = chunks[i + 1][0]['s'] if i + 1 < len(chunks) else None
    e = ch[-1]['e'] + 0.25
    if nxt is not None and nxt - ch[-1]['e'] < 0.6:
        e = nxt
    if nxt is not None:
        e = min(e, nxt)
    toks = [re.sub(r'[.,:;«»"]', '', x['t']).upper() for x in ch]
    caps.append({'s': s, 'e': e, 'toks': [t for t in toks if t]})

font = ImageFont.truetype(INTER, 66)
PILL = (59, 36, 23)          # тёмно-коричневая подложка
GOLD = (244, 197, 110)

def caption_img(toks):
    space = font.getlength(' ')
    widths = [font.getlength(t) for t in toks]
    tw = sum(widths) + space * (len(toks) - 1)
    asc, desc = font.getmetrics()
    padx, pady = 26, 14
    cap_h = font.getbbox('ЖЁ')[3] - font.getbbox('Ж')[1]
    box_w, box_h = int(tw + 2 * padx), int(cap_h + 2 * pady + 6)
    im = Image.new('RGBA', (box_w + 40, box_h + 40), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 24, 20 + box_w, 24 + box_h), 22, fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, 20 + box_w, 20 + box_h), 22, fill=PILL + (238,))
    x = 20 + padx
    top = 20 + pady - font.getbbox('Ж')[1] + 2
    for t, wd in zip(toks, widths):
        d.text((x, top), t, font=font, fill=GOLD if t.strip('?!') in ACCENT else (255, 255, 255))
        x += wd + space
    return im

for c in caps:
    c['img'] = caption_img(c['toks'])

# ---------- photos + punch-in zooms ----------
IMGDIR = '/tmp/claude-0/-home-user-Juls/7d14dc2a-5247-5de2-a64d-0d6d0bac923d/images'
PHOTOS = [
    dict(s=3.5, e=8.7, path=IMGDIR + '/5.jpg'),    # Святой Дух — Пятидесятница
    dict(s=25.4, e=31.1, path=IMGDIR + '/6.jpg'),  # первый поезд
]
# Склейки по кадрам: вырезаем середину пауз прямо из кадров исходника, план меняется ровно на склейке
PAUSES = [(8.64, 9.34, .2), (15.06, 15.98, .2), (25.84, 26.48, .2), (32.68, 33.68, .2), (35.8, 36.78, .2),
          (46.5, 47.6, .2), (54.96, 55.74, .2), (63.28, 64.72, .25)]
ZSEQ = [1.0, 1.12, 1.2, 1.0, 1.3, 1.12, 1.0, 1.25, 1.0]
KEEP, a = [], 0
for p0, p1, k in PAUSES:
    KEEP.append((a, round((p0 + k / 2) * FPS))); a = round((p1 - k / 2) * FPS)
KEEP.append((a, 10 ** 9))
FX, FY = 0.47, 0.34
IN_T, OUT_T = 0.35, 0.8                # въезд 0.35 с, плавный отъезд 0.8 с                  # центр лица в кадре
if MODE == 'bottom':
    BOX = (70, int(H * 0.565), W - 70, int(H * 0.905))   # нижняя половина, выше интерфейса Instagram
    CAP_PHOTO_Y = int(H * 0.525)
else:
    BOX = (70, int(H * 0.22), W - 70, int(H * 0.66))   # по центру
    CAP_PHOTO_Y = int(H * 0.74)
CAP_Y = int(H * 0.68)
FADE = 0.35
R = 0

def prep_photo(p):
    im = Image.open(p['path']).convert('RGB')
    bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
    sc = min(bw / im.width, bh / im.height)
    w, h = int(im.width * sc), int(im.height * sc)
    big = im.resize((int(w * 1.08), int(h * 1.08)), Image.LANCZOS)
    p['w'], p['h'], p['big'] = w, h, big
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), R, fill=255)
    p['mask'] = m
    sh = Image.new('RGBA', (w + 80, h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 48, 40 + w, 48 + h), R, fill=(0, 0, 0, 150))
    p['shadow'] = sh.filter(ImageFilter.GaussianBlur(18))
    p['base'] = im.resize((w, h), Image.LANCZOS).convert('RGBA')
    p['x'] = (W - w) // 2
    p['y'] = BOX[1] + (bh - h) // 2

for p in PHOTOS:
    prep_photo(p)

def photo_layer(p, t):
    lt = t - p['s']
    a = max(0.0, min(1.0, lt / 0.06, (p['e'] - t) / 0.12))      # быстрое появление, короткое исчезновение
    k = min(1.0, lt / 0.2)
    pop = 1 + 0.08 * __import__('math').sin(k * 3.14159) * (1 - k * 0.5) if k < 1 else 1.0   # «выпрыгивание» с лёгким перелётом
    sc = (0.82 + 0.18 * (1 - (1 - k) ** 3)) * pop
    w, h = max(1, int(p['w'] * sc)), max(1, int(p['h'] * sc))
    card = p['base'].resize((w, h), Image.LANCZOS)
    return card, a, p['x'] + (p['w'] - w) // 2, p['y'] + (p['h'] - h) // 2

def fade(im, a):
    if a >= 1:
        return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im

dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', SRC, '-vf', 'scale=in_color_matrix=bt709:in_range=tv:out_range=full,format=rgb24', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                        '-r', str(FPS), '-i', '-', '-vf', 'scale=out_color_matrix=bt709:out_range=tv:in_range=full,format=yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-c:v', 'libx264',
                        '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', OUT + '.video.mp4'], stdin=subprocess.PIPE)
src_n = 0
n = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    seg = next((i for i, (ka, kb) in enumerate(KEEP) if ka <= src_n < kb), None)
    src_n += 1
    if seg is None:
        continue
    t = n / FPS
    img = Image.frombytes('RGB', (W, H), buf)
    z = ZSEQ[seg]
    if z > 1.0:
        cw, ch = W / z, H / z
        cx = min(max(FX * W, cw / 2), W - cw / 2); cy = min(max(FY * H, ch / 2), H - ch / 2)
        img = img.resize((W, H), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    img = img.convert('RGBA')
    photo_on = False
    for p in PHOTOS:
        if p['s'] <= t < p['e']:
            photo_on = True
            card, a, x, y = photo_layer(p, t)
            img.alpha_composite(fade(card, a), (x, y))
    cy_cap = CAP_PHOTO_Y if photo_on else CAP_Y
    for c in caps:
        if c['s'] <= t < c['e']:
            ci = c['img']
            k = min(1, (t - c['s']) / 0.09)
            sc = 0.88 + 0.12 * k
            if sc < 1:
                ci = ci.resize((max(1, int(ci.width * sc)), max(1, int(ci.height * sc))), Image.LANCZOS)
            img.alpha_composite(ci, (int(W / 2 - ci.width / 2), int(cy_cap - ci.height / 2)))
            break
    enc.stdin.write(img.convert('RGB').tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
# звук: те же куски по точным временам кадров, с микро-фейдами на стыках
fc, cc = '', ''
for i, (ka, kb) in enumerate(KEEP):
    ta, tb = ka / FPS, min(kb / FPS, 10 ** 5)
    end = f':{tb:.4f}' if kb < 10 ** 9 else ''
    fc += f"[1:a]atrim={ta:.4f}{end},asetpts=PTS-STARTPTS,afade=t=in:d=0.01[a{i}];"
    cc += f"[a{i}]"
fc += f"{cc}concat=n={len(KEEP)}:v=0:a=1[a]"
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', OUT + '.video.mp4', '-i', SRC, '-filter_complex', fc, '-map', '0:v', '-map', '[a]',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', OUT], check=True)
print('frames', n, 'captions', len(caps))
