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

# ---------- cutaway cards ----------
def mixed_font_text(d, xy_center, text, size, weight, fill, anchor_y):
    """Playfair Display: cyrillic + latin subsets, choose per character."""
    fc = ImageFont.truetype(PF.format(sub='cyrillic', w=weight), size)
    fl = ImageFont.truetype(PF.format(sub='latin', w=weight), size)
    pick = lambda ch: fc if 'Ѐ' <= ch <= 'ӿ' else fl
    total = sum(pick(ch).getlength(ch) for ch in text)
    x = xy_center[0] - total / 2
    for ch in text:
        f = pick(ch)
        d.text((x, anchor_y), ch, font=f, fill=fill, anchor='ls')
        x += f.getlength(ch)

def paper():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    base = np.array([238, 224, 198], float); edge = np.array([196, 170, 128], float)
    r = np.sqrt((x - .5) ** 2 * 1.6 + (y - .45) ** 2)
    k = np.clip(r / .75, 0, 1)[..., None] ** 1.6
    img = base * (1 - k) + edge * k
    rng = np.random.default_rng(7)
    img += rng.normal(0, 5, (H, W, 1))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

INK = (58, 36, 22)

def make_card(icon, title, sub, small):
    bg = paper()
    d = ImageDraw.Draw(bg)
    d.rectangle((40, 40, W - 40, H - 40), outline=INK + (150,), width=3)
    d.rectangle((54, 54, W - 54, H - 54), outline=INK + (90,), width=1)
    if title:
        mixed_font_text(d, (W / 2, 0), title, 92, 700, INK, int(H * .52))
    if sub:
        mixed_font_text(d, (W / 2, 0), sub, 54, 400, INK, int(H * .565))
    if small:
        mixed_font_text(d, (W / 2, 0), small, 34, 400, INK + (200,), int(H * .60))
    ic = Image.open(f'{VID}/icon-{icon}.png').convert('RGBA')
    a = np.array(ic); a[..., :3] = INK; ic = Image.fromarray(a)
    return bg, ic

CARDS = [
    dict(s=4.45, e=8.95, card=make_card('freedom-dove', 'COMFORTER', 'Утешитель', 'Евангелие от Иоанна, 14:16'), icon_w=430, icon_y=.30),
    dict(s=27.25, e=32.95, card=make_card('steam-locomotive', '15 сентября 1830', 'Ливерпуль — Манчестер', 'первая междугородняя железная дорога'), icon_w=560, icon_y=.32),
    dict(s=57.05, e=59.40, card=make_card('robot-antennas', '', '', ''), icon_w=520, icon_y=.36),
]
FADE = 0.25

def card_frame(c, t):
    bg, ic = c['card']
    p = (t - c['s']) / (c['e'] - c['s'])
    z = 1.0 + 0.07 * p
    w = int(c['icon_w'] * z); h = int(ic.height * w / ic.width)
    icr = ic.resize((w, h), Image.LANCZOS)
    fr = bg.copy()
    fr.alpha_composite(icr, (int(W / 2 - w / 2), int(H * c['icon_y'] - h / 2)))
    return np.asarray(fr.convert('RGB'), dtype=np.float32)

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
    frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    for c in CARDS:
        if c['s'] - FADE <= t <= c['e'] + FADE:
            a = min(1, (t - (c['s'] - FADE)) / FADE, ((c['e'] + FADE) - t) / FADE)
            a = max(0, min(1, a))
            frame = frame * (1 - a) + card_frame(c, min(max(t, c['s']), c['e'])) * a
    img = Image.fromarray(frame.astype(np.uint8), 'RGB').convert('RGBA')
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
json.dump([{'s': round(c['s'], 2), 'e': round(c['e'], 2), 'text': ' '.join(c['toks'])} for c in caps],
          open(OUT + '.captions.json', 'w'), ensure_ascii=False, indent=1)
print('frames', n, 'captions', len(caps))
