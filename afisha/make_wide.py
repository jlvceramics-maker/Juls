"""Широкая афиша 2880x1260 в двух вариантах.

poster_wide.png          — фото на весь холст (масштаб 1.92; фон размыт, а пара
                           берётся с крупного скриншота и всё равно уменьшается);
poster_wide_gradient.png — фото слева перетекает в бордовый, текст на бордовом.
Запуск: python3 afisha/make_wide.py
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import make_poster as mp

W, H = 2880, 1260
BURGUNDY = (74, 12, 26)
FONT = str(mp.HERE / "Oswald-600.ttf")


def shade(img, x_from, color, strength, y_from=None):
    """Плавное затемнение (или перетекание в цвет) вправо, а при y_from — и вниз."""
    xs = np.clip((np.arange(W) - x_from) / (W - x_from), 0, 1)
    a = (xs * xs * (3 - 2 * xs))[None, :].repeat(H, 0)          # smoothstep
    if y_from is not None:
        ys = np.clip((np.arange(H) - y_from) / (H - y_from), 0, 1) ** 1.3
        a = np.maximum(a, ys[:, None].repeat(W, 1) * 0.8)
    mask = Image.fromarray((a * strength * 255).astype(np.uint8))
    return Image.composite(Image.new("RGB", (W, H), color), img.convert("RGB"), mask)


def text_block(img, x0, title=132):
    """БАЛ / «ВЫШЕ НАС / ТОЛЬКО ЗВЁЗДЫ» / вход и зал — по убыванию, слева направо."""
    f = lambda size: ImageFont.truetype(FONT, size)
    lines = [
        (f(250), 650, "БАЛ", mp.RED),
        (f(title), 805, "«ВЫШЕ НАС", mp.GRAY),
        (f(title), 945, "ТОЛЬКО ЗВЁЗДЫ»", mp.GRAY),
        (f(68), 1090, "ВХОД ПО ПРИГЛАШЕНИЯМ", mp.GRAY),
        (f(68), 1180, "КРАСНОЗНАМЁННЫЙ ЗАЛ", mp.GRAY),
    ]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
    right = 0
    for font, base, s, c in lines:
        ds.text((x0 + 4, base + 4), s, font=font, fill=(0, 0, 0, 190), anchor="ls")
        d.text((x0, base), s, font=font, fill=c, anchor="ls")
        right = max(right, x0 + d.textlength(s, font=font))
    out = Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(7)))
    out = Image.alpha_composite(out, layer)
    # красная линия между названием и местом, как на эмблеме
    ImageDraw.Draw(out).rectangle([x0, 985, right, 995], fill=mp.RED)
    print("text block:", x0, "->", round(right))
    return out


def save(img, name):
    img = img.convert("RGB")
    img.save(mp.HERE / f"{name}.png")
    img.save(mp.HERE / f"{name}.jpg", quality=95)
    print("ok", name, img.size)


# 1) фото на весь холст: пара крупно слева от центра, текст в свободной правой части
mp.set_geometry(W, H, W / 1500, offset_y=600)
img = shade(mp.photo_layer(), 1650, (0, 0, 0), 0.62, y_from=900)
save(text_block(mp.emblem(img, h=350, margin=70, top=46), 1800), "poster_wide")

# 2) фото слева перетекает в бордовый, текст на бордовом
mp.set_geometry(W, H, 1.40, offset_y=120)
img = shade(mp.photo_layer(), 1250, BURGUNDY, 1.0)
img = shade(img, 1250, BURGUNDY, 1.0)      # второй проход: справа чистый цвет
save(text_block(mp.emblem(img, h=350, margin=70, top=46), 1840, title=124),
     "poster_wide_gradient")
