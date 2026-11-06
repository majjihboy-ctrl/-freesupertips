"""Renders the daily "free tips" social flyer as a PNG (1080x1350).

Pure Pillow, no DB access here -- views.flyer_png() feeds it the tips.
Fonts are bundled in predictions/static/fonts so rendering also works on
serverless hosts that have no system fonts.
"""
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
GOLD = "#f5c518"
DARK = "#0b3d2a"
MID = "#0f5132"
SOFT = "#b9d8c8"
FONT_DIR = settings.BASE_DIR / "predictions" / "static" / "fonts"


def _font(weight, size):
    return ImageFont.truetype(str(FONT_DIR / f"Poppins-{weight}.ttf"), size)


def _fit(draw, text, weight, size, max_w, min_size=24):
    """Largest font (<= size) whose rendering of `text` fits max_w."""
    while size > min_size and draw.textlength(text, font=_font(weight, size)) > max_w:
        size -= 2
    return _font(weight, size)


def _center(draw, text, y, font, fill):
    w = draw.textlength(text, font=font)
    draw.text(((W - w) / 2, y), text, font=font, fill=fill)


def render_flyer(tips, date_label="", title_top="FREE TIPS", title_bottom="TODAY",
                 cta="Get more free tips: matchpro.site"):
    """tips: list of (match_name, pick_label, confidence_or_None), max 3."""
    tips = tips[:3]
    img = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(
            int(8 + 7 * (1 - t) + 4 * t),
            int(40 + 33 * (1 - t)),
            int(30 + 15 * (1 - t) + 25 * t * 0.4),
        ))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for r, a in ((300, 22), (200, 16)):
        od.ellipse([W // 2 - r, H - 260 - r, W // 2 + r, H - 260 + r],
                   outline=(255, 255, 255, a), width=4)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)

    head = "MATCHDAY PRO" + (f"  \u2022  {date_label.upper()}" if date_label else "")
    _center(d, head, 60, _font("Medium", 34), SOFT)
    _center(d, title_top, 120, _font("Bold", 130), GOLD)
    _center(d, title_bottom, 250, _font("Bold", 130), "#ffffff")
    d.rounded_rectangle([W // 2 - 190, 410, W // 2 + 190, 420], radius=5, fill=GOLD)

    y = 460
    for match, pick, conf in tips:
        d.rounded_rectangle([70, y, W - 70, y + 190], radius=28, fill="#ffffff")
        d.rounded_rectangle([70, y, 90, y + 190], radius=10, fill=GOLD)
        text_w = (W - 330 - 120) if conf is not None else (W - 140 - 120)
        d.text((120, y + 28), match, font=_fit(d, match, "Medium", 38, text_w), fill=DARK)
        d.text((120, y + 90), pick, font=_fit(d, pick, "Bold", 52, text_w), fill=MID)
        if conf is not None:
            d.rounded_rectangle([W - 290, y + 45, W - 100, y + 145], radius=22, fill=MID)
            c = f"{int(conf)}%"
            cf = _font("Bold", 52)
            d.text((W - 195 - d.textlength(c, font=cf) / 2, y + 50), c, font=cf, fill=GOLD)
            lf = _font("Regular", 22)
            d.text((W - 195 - d.textlength("confidence", font=lf) / 2, y + 112),
                   "confidence", font=lf, fill="#cfe8da")
        y += 215

    d.rounded_rectangle([70, 1130, W - 70, 1235], radius=52, fill=GOLD)
    cf = _fit(d, cta, "Bold", 44, W - 200)
    _center(d, cta, 1152, cf, DARK)
    _center(d, "Model estimates, not guarantees  \u2022  18+ Gamble responsibly",
            1265, _font("Regular", 26), SOFT)

    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
