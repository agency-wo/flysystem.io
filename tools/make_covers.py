"""Genera le copertine dei cataloghi (p1 del PDF) in AVIF/WebP/JPEG a 480/960.

usage: python make_covers.py <pdf> <slug> [pagina]
output: assets/img/cataloghi/covers/c-<slug>-{480,960}.{avif,webp,jpg}
"""
import sys
from pathlib import Path

import fitz
import pillow_avif  # noqa: F401
from PIL import Image

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "img" / "cataloghi" / "covers"


def main(pdf: Path, slug: str, pageno: int = 1):
    doc = fitz.open(pdf)
    page = doc[pageno - 1]
    scale = 2000 / max(page.rect.width, page.rect.height)
    pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    print(f"master: {im.width}x{im.height}")
    for w in (480, 960):
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS)
        r.save(OUT / f"c-{slug}-{w}.avif", quality=62)
        r.save(OUT / f"c-{slug}-{w}.webp", quality=80, method=6)
        r.save(OUT / f"c-{slug}-{w}.jpg", quality=82, optimize=True, progressive=True)
        print(f"  c-{slug}-{w}: {w}x{h}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
