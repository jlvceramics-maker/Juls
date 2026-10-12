import json, subprocess, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, WORDS, OUT, VID, FONTS = sys.argv[1:6]
W, H, FPS = 928, 1696, 30
INTER = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
PF = FONTS + '/playfair-display-{sub}-{w}-normal.woff'

# ---------- captions ----------
FIX = {'утешителей,': 'Утешитель,', 'святой': 'Святой', 'дух': 'Дух', 'троицы.': 'Троицы.',
       'парельцам': 'по рельсам', 'унес': 'унёс', 'сладче,': 'слаще,', 'постась': 'ипостась'}
ACCENT = {'КОМФОРТ', 'КОМФОРТОМ', 'КОМФОРТУ', 'ИДОЛУ', 'СИМВОЛИЧНО', 'РОБОТА', 'ЛЮБИТЬ',
          'УТЕШИТЕЛЬ', 'СВЯТОЙ', 'ДУХ'}

raw = json.load(open(WORDS))['chunks']
words = []
for i, c in enumerate(raw):
    t = c['text'].strip()
    if t == 'и' and i + 1 < len(raw) and raw[i + 1]['text'].strip() == 'постась':
        continue  # whisper split "ипостась" into "и постась"
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

font = ImageFont.truetype(INTER, 58)
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

# ---------- picture-in-picture clips (motion graphics in old-film style) ----------
PW, PH = 300, 400                      # окно поверх видео, справа сверху над плечом
PX, PY = W - PW - 28, 120
rng = np.random.default_rng(3)
INK = np.array([52, 32, 19], np.float32)
yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
VIGN = (1 - 0.55 * np.clip(np.sqrt(((xx / PW - .5) * 1.2) ** 2 + ((yy / PH - .5)) ** 2) / .72, 0, 1) ** 2)[..., None]

def load_icon(name, width):
    im = Image.open(f'{VID}/icon-{name}.png').convert('RGBA')
    h = int(im.height * width / im.width)
    return np.asarray(im.resize((width, h), Image.LANCZOS))[..., 3].astype(np.float32) / 255

def stamp(canvas, mask, cx, cy, color, alpha=1.0):
    h, w = mask.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(PW, x0 + w), min(PH, y0 + h)
    if xa >= xb or ya >= yb:
        return
    m = mask[ya - y0:yb - y0, xa - x0:xb - x0, None] * alpha
    canvas[ya:yb, xa:xb] = canvas[ya:yb, xa:xb] * (1 - m) + np.asarray(color, np.float32) * m

def old_film(img, t, tone=(1.0, 0.86, 0.64)):
    lum = img.mean(axis=2, keepdims=True)
    img = lum * np.array(tone, np.float32)
    img *= 0.93 + 0.07 * np.sin(t * 47.0) * np.sin(t * 13.0)      # мерцание
    img = img * VIGN + rng.normal(0, 9, (PH, PW, 1))                # зерно
    if rng.random() < 0.35:                                          # царапина
        x = int(rng.integers(10, PW - 10)); img[:, x:x + 1] *= 0.6
    return img

def paper_bg(c1=(232, 214, 182), c2=(196, 168, 124)):
    k = np.clip(yy / PH, 0, 1)[..., None]
    return np.asarray(c1, np.float32) * (1 - k) + np.asarray(c2, np.float32) * k

def small_font(size, weight=400, sub='cyrillic'):
    return ImageFont.truetype(PF.format(sub=sub, w=weight), size)

def caption_strip(img, text, sub='cyrillic'):
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle((0, PH - 46, PW, PH), fill=(40, 24, 14))
    d.text((PW / 2, PH - 16), text.upper(), font=ImageFont.truetype(INTER, 21), fill=(240, 222, 190), anchor='ms')
    return np.asarray(im, np.float32)

DOVE = load_icon('dove', 200)
TRAIN = load_icon('steam-locomotive', 190)
ROBOT = load_icon('robot-antennas', 200)

def clip_dove(t):
    img = paper_bg((246, 232, 200), (206, 178, 130))
    ang = np.arctan2(xx - PW / 2, yy + 60)                           # лучи света сверху
    rays = (0.5 + 0.5 * np.sin(ang * 22 + t * 0.8)) ** 3 * np.clip(1 - yy / PH, 0, 1)
    img += rays[..., None] * 38
    cy = -40 + min(1, t / 2.2) ** 0.6 * 210 + 6 * np.sin(t * 2.4)   # голубь спускается
    stamp(img, DOVE, PW / 2 + 5 * np.sin(t * 1.3), cy, INK)
    img = old_film(img, t)
    return caption_strip(img, 'Утешитель')

SMOKE = [dict(x0=rng.uniform(-30, 30), r0=rng.uniform(10, 16), ph=rng.uniform(0, 1)) for _ in range(14)]

def clip_train(t):
    img = paper_bg((236, 220, 190), (210, 186, 146))
    ground = 300
    img[ground:] = img[ground:] * 0.82
    off = (t * 140) % 34                                             # шпалы бегут
    for i in range(-1, PW // 34 + 2):
        x = int(i * 34 - off)
        img[ground + 4:ground + 14, max(0, x):max(0, min(PW, x + 14))] = INK * 0.9
    img[ground:ground + 4] = INK
    tx = -100 + t * 90                                               # паровоз въезжает слева
    bob = 1.5 * np.sin(t * 25)
    tm = TRAIN.shape
    stamp(img, TRAIN, tx, ground - tm[0] / 2 + 2 + bob, INK)
    chim_x, chim_y = tx - tm[1] * 0.25, ground - tm[0] * 0.95
    for s in SMOKE:                                                  # клубы дыма
        a = (t * 0.9 + s['ph']) % 1.0
        r = s['r0'] * 1.5 * (1 + 2.6 * a)
        cx, cy = chim_x - a * 120 + s['x0'] * a, chim_y - a * 150
        m = np.clip(1 - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r, 0, 1) ** 0.7
        stamp_alpha = (1 - a) * 0.9
        img = img * (1 - m[..., None] * stamp_alpha) + np.array([70, 60, 52], np.float32) * m[..., None] * stamp_alpha
    img = old_film(img, t)
    img += rng.normal(0, 1.2, (1, 1, 1))                             # дрожание кадра
    img = np.roll(img, int(rng.integers(-1, 2)), axis=0)
    return caption_strip(img, '1830', sub='latin')

def clip_robot(t):
    base = np.zeros((PH, PW, 3), np.float32) + np.array([18, 26, 34], np.float32)
    base += (np.sin(yy * 0.9) > 0.6)[..., None] * 10                 # строки развёртки
    stamp(base, ROBOT, PW / 2, PH * 0.45, (140, 200, 230))
    if int(t * 6) % 5 == 0:                                          # глитч
        y0 = int(rng.integers(40, PH - 80)); hgt = int(rng.integers(8, 30))
        base[y0:y0 + hgt] = np.roll(base[y0:y0 + hgt], int(rng.integers(-25, 25)), axis=1)
    blink = 1.0 if (t % 1.2) > 0.12 else 0.2
    for ex in (0.405, 0.595):                                        # светящиеся глаза
        g = np.clip(1 - np.sqrt((xx - PW * ex) ** 2 + (yy - PH * 0.418) ** 2) / 26, 0, 1) ** 2
        base += g[..., None] * np.array([90, 230, 255], np.float32) * blink
    base = base * VIGN + rng.normal(0, 6, (PH, PW, 1))
    return caption_strip(base, 'человек → робот')

PIPS = [
    dict(s=4.3, e=9.0, f=clip_dove),
    dict(s=27.1, e=33.0, f=clip_train),
    dict(s=56.9, e=59.7, f=clip_robot),
]
IN, OUTD = 0.35, 0.3

mask = Image.new('L', (PW, PH), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, PW - 1, PH - 1), 26, fill=255)
FRAME_MASK = mask
shadow = Image.new('RGBA', (PW + 60, PH + 60), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle((30, 36, 30 + PW, 36 + PH), 30, fill=(0, 0, 0, 140))
SHADOW = shadow.filter(ImageFilter.GaussianBlur(14))

def pip_layer(p, t):
    lt = t - p['s']
    a_in = min(1, lt / IN); a_out = min(1, (p['e'] - t) / OUTD)
    a = max(0, min(a_in, a_out))
    ease = 1 - (1 - a_in) ** 3
    frame = Image.fromarray(np.clip(p['f'](lt), 0, 255).astype(np.uint8)).convert('RGBA')
    framed = Image.new('RGBA', (PW, PH), (0, 0, 0, 0)); framed.paste(frame, (0, 0), FRAME_MASK)
    ImageDraw.Draw(framed).rounded_rectangle((1, 1, PW - 2, PH - 2), 26, outline=(226, 186, 110, 255), width=3)
    dx = int((1 - ease) * 60)
    return framed, SHADOW, a, PX + dx, PY

# ---------- render ----------
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', SRC, '-vf', f'scale={W}:{H}:flags=lanczos,fps={FPS}',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                        '-r', str(FPS), '-i', '-', '-i', SRC, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264',
                        '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                        '-movflags', '+faststart', '-shortest', OUT], stdin=subprocess.PIPE)
CAP_Y = int(H * 0.68)
n = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    t = n / FPS
    img = Image.frombytes('RGB', (W, H), buf).convert('RGBA')
    for p in PIPS:
        if p['s'] <= t < p['e']:
            framed, sh, a, x, y = pip_layer(p, t)
            if a < 1:
                framed.putalpha(Image.eval(framed.getchannel('A'), lambda v: int(v * a)))
                sh = sh.copy(); sh.putalpha(Image.eval(sh.getchannel('A'), lambda v: int(v * a)))
            img.alpha_composite(sh, (x - 30, y - 30))
            img.alpha_composite(framed, (x, y))
    for c in caps:
        if c['s'] <= t < c['e']:
            ci = c['img']
            k = min(1, (t - c['s']) / 0.09)
            sc = 0.88 + 0.12 * k
            if sc < 1:
                ci = ci.resize((max(1, int(ci.width * sc)), max(1, int(ci.height * sc))), Image.LANCZOS)
            img.alpha_composite(ci, (int(W / 2 - ci.width / 2), int(CAP_Y - ci.height / 2)))
            break
    enc.stdin.write(img.convert('RGB').tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print('frames', n, 'captions', len(caps))
