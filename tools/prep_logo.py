"""Trim white margins from the clean logo, emit header PNGs, report ratio + colors.

usage: python prep_logo.py <src.jpg> <img-dir>
"""
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

def main(src: Path, img_dir: Path):
    im = Image.open(src).convert("RGB")
    # bbox of non-near-white pixels
    gray = im.convert("L").point(lambda v: 255 if v < 240 else 0)
    bbox = gray.getbbox()
    pad = round(im.width * 0.015)
    l, t, r, b = bbox
    logo = im.crop((max(0, l - pad), max(0, t - pad),
                    min(im.width, r + pad), min(im.height, b + pad)))
    ratio = logo.width / logo.height
    print(f"cropped: {logo.width}x{logo.height}  ratio={ratio:.3f}")

    # key white to alpha AND snap the two ink colors to flat brand values.
    # (removes JPEG noise -> crisper edges + far smaller PNG; grey min-chan=132 stays safe)
    BLU, STEEL = (0x30, 0x48, 0x90), (0x84, 0x84, 0x9C)
    rgba = logo.convert("RGBA")
    px = rgba.load()
    HI, LO = 240, 214  # min-channel: >=HI transparent, <=LO opaque
    for y in range(rgba.height):
        for x in range(rgba.width):
            r_, g_, b_, _ = px[x, y]
            m = min(r_, g_, b_)
            if m >= HI:
                px[x, y] = (255, 255, 255, 0)
                continue
            a = 255 if m <= LO else round(255 * (HI - m) / (HI - LO))
            db = (r_ - BLU[0]) ** 2 + (g_ - BLU[1]) ** 2 + (b_ - BLU[2]) ** 2
            ds = (r_ - STEEL[0]) ** 2 + (g_ - STEEL[1]) ** 2 + (b_ - STEEL[2]) ** 2
            snap = BLU if db <= ds else STEEL
            px[x, y] = (snap[0], snap[1], snap[2], a)

    # header asset (shown ~34px tall; 120px covers up to ~3.5x DPR) + OG source
    for name, h in (("logo-header", 120), ("logo-600", 600)):
        w = round(rgba.width * h / rgba.height)
        out = rgba.resize((w, h), Image.LANCZOS)
        out.save(img_dir / f"{name}.png", optimize=True)
        kb = (img_dir / f"{name}.png").stat().st_size / 1024
        print(f"  {name}.png = {w}x{h} ({kb:.1f} KB)")

    cnt = Counter()
    for pxv in logo.getdata():
        if sum(pxv) < 690:
            cnt[(px[0] // 12 * 12, px[1] // 12 * 12, px[2] // 12 * 12)] += 1
    _ = cnt

if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
