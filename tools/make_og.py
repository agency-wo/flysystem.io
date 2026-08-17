"""Compose the branded Open Graph image (1200x630): paper panel with logo + hero photo.

usage: python make_og.py <hero-master.png> <logo.png> <font.ttf> <out.jpg>

Pillow non legge i woff2: converti prima il font spedito nel sito, poi passa il
TTF ottenuto.

    python -c "from fontTools.ttLib import TTFont; f=TTFont('assets/fonts/Switzer-Medium.woff2'); f.flavor=None; f.save('%TEMP%/sw.ttf')"
    python tools/make_og.py assets/img/home/hero-edificio-1920.jpg assets/img/logo-600.png %TEMP%/sw.ttf assets/img/og/og-default.jpg
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PAPER, NAVY, BLU = "#F1F2F3", "#14171D", "#304890"

def main(hero_p: Path, logo_p: Path, font_p: Path, out: Path):
    W, H, PANEL = 1200, 630, 470
    canvas = Image.new("RGB", (W, H), PAPER)

    # photo right, cover-cropped (generic cover: works for any source aspect)
    hero = Image.open(hero_p).convert("RGB")
    target_w, target_h = W - PANEL, H
    scale = max(target_w / hero.width, target_h / hero.height)
    hero = hero.resize((int(hero.width * scale), int(hero.height * scale)), Image.LANCZOS)
    hx = (hero.width - target_w) // 2
    hy = (hero.height - target_h) // 2
    canvas.paste(hero.crop((hx, hy, hx + target_w, hy + target_h)), (PANEL, 0))

    d = ImageDraw.Draw(canvas)
    # navy divider hairline
    d.rectangle([PANEL - 2, 0, PANEL, H], fill=NAVY)

    # logo centered in panel upper half (transparent PNG, alpha composited)
    logo = Image.open(logo_p).convert("RGBA")
    lw = 300
    lh = round(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    canvas.paste(logo, ((PANEL - lw) // 2, 190), logo)

    # tracked uppercase line
    font = ImageFont.truetype(str(font_p), 21)
    text = "P R O D U Z I O N E   I T A L I A N A"
    tw = d.textlength(text, font=font)
    d.text(((PANEL - tw) / 2, 190 + lh + 40), text, font=font, fill=BLU)

    # thin rule with end ticks (dim motif)
    y = 190 + lh + 100
    x1, x2 = 70, PANEL - 70
    d.line([x1, y, x2, y], fill=NAVY, width=1)
    d.line([x1, y - 6, x1, y + 6], fill=NAVY, width=1)
    d.line([x2, y - 6, x2, y + 6], fill=NAVY, width=1)
    small = ImageFont.truetype(str(font_p), 17)
    loc = "IN ITALIA E NEL MONDO"
    lw2 = d.textlength(loc, font=small)
    d.rectangle([(PANEL - lw2) / 2 - 14, y - 12, (PANEL + lw2) / 2 + 14, y + 12], fill=PAPER)
    d.text(((PANEL - lw2) / 2, y - 9), loc, font=small, fill=NAVY)

    canvas.save(out, quality=86, optimize=True, progressive=True)
    print(f"og: {W}x{H} -> {out}")

if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
