"""Deriva il nuovo set logo Fly System dal foglio alllogosflysystem.jpeg.

Estrae il lockup orizzontale (in alto) e l'app icon (in basso a destra),
scontorna il fondo bianco con rampa alpha mantenendo i gradienti del logo.

usage: python prep_logo2.py <sheet.jpg> <img-dir>
outputs: logo-header.png, logo-600.png, favicon-48.png, favicon-192.png,
         apple-touch-icon.png, favicon.svg (wrapper con PNG embedded)
"""
import base64
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HI, LO = 238, 205  # min-channel: >=HI trasparente, <=LO opaco, in mezzo rampa


def white_key(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, _ = px[x, y]
            m = min(r, g, b)
            if m >= HI:
                px[x, y] = (255, 255, 255, 0)
            elif m > LO:
                px[x, y] = (r, g, b, round(255 * (HI - m) / (HI - LO)))
    return rgba


def bbox_dark(im: Image.Image, thr: int = 235) -> tuple:
    gray = im.convert("L").point(lambda v: 255 if v < thr else 0)
    return gray.getbbox()


def main(src: Path, img_dir: Path):
    sheet = Image.open(src).convert("RGB")
    print(f"sheet: {sheet.width}x{sheet.height}")

    # ---- lockup orizzontale (meta' superiore del foglio) ----
    top = sheet.crop((0, 0, sheet.width, round(sheet.height * 0.60)))
    l, t, r, b = bbox_dark(top)
    pad = round(sheet.width * 0.012)
    lockup = top.crop((max(0, l - pad), max(0, t - pad),
                       min(top.width, r + pad), min(top.height, b + pad)))
    print(f"lockup: {lockup.width}x{lockup.height} ratio={lockup.width/lockup.height:.3f}")
    keyed = white_key(lockup)
    for name, h in (("logo-header", 120), ("logo-600", 600)):
        w = round(keyed.width * h / keyed.height)
        out = keyed.resize((w, h), Image.LANCZOS)
        out.save(img_dir / f"{name}.png", optimize=True)
        kb = (img_dir / f"{name}.png").stat().st_size / 1024
        print(f"  {name}.png = {w}x{h} ({kb:.1f} KB)")

    # ---- app icon (regione inferiore destra) ----
    zone = sheet.crop((round(sheet.width * 0.62), round(sheet.height * 0.62),
                       sheet.width, sheet.height))
    zl, zt, zr, zb = bbox_dark(zone, thr=200)  # tile navy scuro
    tile = zone.crop((zl, zt, zr, zb))
    side = min(tile.width, tile.height)
    tile = tile.crop((0, 0, side, side))
    print(f"tile: {side}x{side}")

    # inset 9%: taglia gli angoli arrotondati bianchi gia' presenti nel tile
    ins = round(side * 0.09)
    core = tile.crop((ins, ins, side - ins, side - ins))

    # apple-touch: quadrato pieno (iOS maschera da solo)
    core.resize((180, 180), Image.LANCZOS).save(img_dir / "apple-touch-icon.png", optimize=True)

    # favicon: tile con angoli arrotondati trasparenti
    for name, s in (("favicon-48", 48), ("favicon-192", 192)):
        icon = core.resize((s, s), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1),
                                               radius=round(s * 0.22), fill=255)
        icon.putalpha(mask)
        icon.save(img_dir / f"{name}.png", optimize=True)
        kb = (img_dir / f"{name}.png").stat().st_size / 1024
        print(f"  {name}.png = {s}x{s} ({kb:.1f} KB)")

    # favicon.svg: wrapper con il PNG 192 embedded (nitido alle taglie tab)
    b64 = base64.b64encode((img_dir / "favicon-192.png").read_bytes()).decode()
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" '
           'viewBox="0 0 192 192"><image width="192" height="192" '
           f'href="data:image/png;base64,{b64}"/></svg>')
    (img_dir / "favicon.svg").write_text(svg, encoding="utf-8")
    print(f"  favicon.svg = {(img_dir / 'favicon.svg').stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
