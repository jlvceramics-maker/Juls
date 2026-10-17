"""Афиша бала «Выше нас только звёзды», 1920x1080.

Пара в центре резкая, остальное размыто; эмблема ЦДРА справа вверху;
текст внизу шрифтом Oswald в цветах эмблемы.
Запуск: python3 afisha/make_poster.py  ->  afisha/poster.png
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
W, H = 1920, 1080
RED = (227, 30, 36)
GRAY = (179, 179, 179)

SCALE = W / 1500          # фото 1500x1000 -> 1920x1280
OFFSET_Y = 190            # обрезаем сверху, чтобы внизу осталось место под текст

BLUR = 7                  # радиус размытия фона: лёгкое, но заметное

# Пара берётся с крупного скриншота оригинала (couple_hires.jpg, 1390x2000):
# в photo.jpg (1500x1000, пришло сжатым через чат) она слишком мелкая.
# Скриншот -> photo.jpg: подобие без поворота, найдено по SIFT-точкам (OpenCV).
HI_SCALE, HI_DX, HI_DY = 0.431683, 388.785, 69.845


def hi_to_canvas(x, y):
    return (x * HI_SCALE + HI_DX) * SCALE, (y * HI_SCALE + HI_DY) * SCALE - OFFSET_Y


def photo_to_hi(x, y):
    return (x - HI_DX) / HI_SCALE, (y - HI_DY) / HI_SCALE


# пару вырезает нейросеть rembg (isnet-general-use) на кропе скриншота;
# танцоров за спиной кавалера отрезаем по линии его спины
# (координаты — кроп photo.jpg с началом в (370, 330))
CUT_RIGHT = [(486, 0), (489, 125), (490, 185), (470, 198), (445, 210), (440, 240),
             (440, 270), (428, 300), (420, 360), (420, 560), (432, 590)]
# просвет пола между платьем и ногой кавалера — тоже фон
GAP = [(349, 364), (356, 380), (359, 420), (362, 500), (357, 518), (330, 520),
       (320, 500), (321, 450), (333, 405), (344, 378)]
# грудь и ближний погон кавалера нейросеть считает полупрозрачными — закрашиваем
# (координаты скриншота)
FORCE = [(800, 868), (860, 858), (905, 848), (960, 880), (960, 1100), (800, 1100),
         (790, 950)]
PATCH = [(1040, 900), (1082, 902), (1088, 972), (1042, 976)]   # нашивка на рукаве
HI_CROP = (0, 560, 1300, 1990)
MASK_FILE = HERE / "couple_mask.png"


def couple_mask():
    """Маска пары на скриншоте (кэшируется в couple_mask.png)."""
    if MASK_FILE.exists():
        return Image.open(MASK_FILE).convert("L")
    from rembg import remove, new_session
    hi = Image.open(HERE / "couple_hires.jpg").convert("RGB")
    seg = remove(hi.crop(HI_CROP), session=new_session("isnet-general-use"), only_mask=True)
    keep = Image.new("L", seg.size, 0)
    to_crop = lambda pts: [tuple(np.subtract(photo_to_hi(x + 370, y + 330), HI_CROP[:2]))
                           for x, y in pts]
    cut = to_crop(CUT_RIGHT)
    ImageDraw.Draw(keep).polygon([(0, -2000)] + [(cut[0][0], -2000)] + cut + [(0, 3000)], fill=255)
    ImageDraw.Draw(keep).polygon(to_crop(GAP), fill=0)
    seg = Image.fromarray(np.minimum(np.asarray(seg), np.asarray(
        keep.filter(ImageFilter.GaussianBlur(4)))))
    full = Image.new("L", hi.size, 0)
    full.paste(seg, HI_CROP[:2])
    ImageDraw.Draw(full).polygon(FORCE, fill=255)
    ImageDraw.Draw(full).polygon(PATCH, fill=255)
    full.save(MASK_FILE)
    return full


def place_hires(img):
    """Скриншот (или его маску) в координаты афиши: уменьшение, а не растяжение."""
    x0, y0 = hi_to_canvas(0, 0)
    k = HI_SCALE * SCALE
    small = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    out = Image.new(img.mode, (W, H), 0)
    out.paste(small, (round(x0), round(y0)))
    return out


def match_colors(img, ref, mask):
    """Скриншот светлее и бледнее оригинала: подгоняем каналы линейно по паре."""
    sel = np.asarray(mask) > 200
    a, r = np.asarray(img, np.float32), np.asarray(ref, np.float32)
    out = np.empty_like(a)
    for c in range(3):
        k, b = np.polyfit(a[..., c][sel], r[..., c][sel], 1)
        out[..., c] = a[..., c] * k + b
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def photo_layer():
    src = Image.open(HERE / "photo.jpg").convert("RGB")
    big = src.resize((W, round(1000 * SCALE)), Image.LANCZOS)
    sharp = big.crop((0, OFFSET_Y, W, OFFSET_Y + H))
    couple = place_hires(Image.open(HERE / "couple_hires.jpg").convert("RGB"))
    hard = place_hires(couple_mask())
    couple = match_colors(couple, sharp, hard)
    couple = couple.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=3))

    keep = 1 - np.asarray(hard.point(lambda v: 255 if v > 20 else 0).filter(ImageFilter.MaxFilter(9)), np.float32) / 255
    rgb = np.asarray(sharp, np.float32)
    def blur(a, r):
        # три прохода бокс-фильтра ~ гаусс; PIL не размывает float-картинки
        for _ in range(3):
            for ax in (0, 1):
                pad = [(0, 0), (0, 0)]
                pad[ax] = (r + 1, r)
                c = np.cumsum(np.pad(a, pad, mode="edge"), axis=ax)
                a = (np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax)
                     - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
        return a
    num = np.dstack([blur(rgb[..., c] * keep, BLUR) for c in range(3)])
    den = blur(keep, BLUR)[..., None]
    blurred = Image.fromarray(np.clip(num / np.maximum(den, 1e-3), 0, 255).astype(np.uint8))

    mask = hard.filter(ImageFilter.GaussianBlur(0.8))
    return Image.composite(couple, blurred, mask)


def bottom_shade(img):
    shade = Image.new("L", (1, H), 0)
    for y in range(H):
        t = max(0.0, (y - 760) / (H - 760))
        shade.putpixel((0, y), int(215 * t ** 1.4))
    shade = shade.resize((W, H))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(black, img, shade)


def emblem(img):
    em = Image.open(HERE / "emblem.png").convert("RGBA")
    h = 300
    em = em.resize((round(em.width * h / em.height), h), Image.LANCZOS)
    x, y = W - em.width - 60, 40
    # мягкая тень, чтобы серый не терялся на светлом потолке
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    a = em.split()[3].point(lambda v: v * 0.55)
    glow.paste((0, 0, 0, 255), (x, y), a)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    out = Image.alpha_composite(img.convert("RGBA"), glow)
    out.alpha_composite(em, (x, y))
    return out


def text(img):
    font = ImageFont.truetype(str(HERE / "Oswald-600.ttf"), 72)
    parts = [("БАЛ ", RED), ("«ВЫШЕ НАС ТОЛЬКО ЗВЁЗДЫ»", GRAY),
             ("    25 ОКТЯБРЯ ", RED), ("В 15.00", GRAY)]
    x0, base = 70, 1020
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
    x = x0
    for s, c in parts:
        ds.text((x + 3, base + 3), s, font=font, fill=(0, 0, 0, 200), anchor="ls")
        d.text((x, base), s, font=font, fill=c, anchor="ls")
        x += d.textlength(s, font=font)
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    out = Image.alpha_composite(img, shadow)
    out = Image.alpha_composite(out, layer)
    # красная линия как на эмблеме
    ImageDraw.Draw(out).rectangle([x0, base + 22, x, base + 30], fill=RED)
    return out


img = bottom_shade(photo_layer())
img = text(emblem(img))
img.convert("RGB").save(HERE / "poster.png")
img.convert("RGB").save(HERE / "poster.jpg", quality=95)
print("ok", img.size)
