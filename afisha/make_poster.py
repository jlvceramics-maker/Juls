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

# контур пары в координатах афиши 1920x1080
COUPLE = [
    (875, 290), (900, 278), (927, 288), (932, 320), (950, 322), (975, 318), (982, 298),
    (1002, 282), (1028, 275), (1052, 284), (1067, 310), (1062, 346), (1046, 362), (1080,
    378), (1094, 420), (1098, 475), (1078, 498), (1052, 515), (1040, 560), (1036, 630),
    (1028, 690), (1026, 780), (1026, 860), (1020, 910), (988, 932), (920, 928), (860,
    948), (780, 954), (680, 914), (618, 864), (558, 794), (522, 754), (518, 728), (560,
    702), (650, 658), (740, 603), (810, 558), (852, 510), (852, 465), (860, 410), (866,
    378), (880, 358)]


def photo_layer():
    src = Image.open(HERE / "photo.jpg").convert("RGB")
    big = src.resize((W, round(1000 * SCALE)), Image.LANCZOS)
    sharp = big.crop((0, OFFSET_Y, W, OFFSET_Y + H))

    hard = Image.new("L", (W, H), 0)
    ImageDraw.Draw(hard).polygon(COUPLE, fill=255)

    # размываем фон без пары, иначе вокруг неё светлый ореол от белого платья
    keep = 1 - np.asarray(hard.filter(ImageFilter.MaxFilter(15)), np.float32) / 255
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
    num = np.dstack([blur(rgb[..., c] * keep, 14) for c in range(3)])
    den = blur(keep, 14)[..., None]
    blurred = Image.fromarray(np.clip(num / np.maximum(den, 1e-3), 0, 255).astype(np.uint8))

    mask = hard.filter(ImageFilter.GaussianBlur(4))
    return Image.composite(sharp, blurred, mask)


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
