"""Prepara le foto della sezione Outdoor/Pergole + poster del video promo.

usage: python make_outdoor.py <sorgenti-dir> <poster-frame.png>
output: assets/img/outdoor/{tramonto,montaggio}-*.{avif,webp,jpg}
        assets/img/home/pergole-poster.jpg
"""
import sys
from pathlib import Path

import pillow_avif  # noqa: F401
from PIL import Image

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "img" / "outdoor"

JOBS = [
    ("tramonto",  "fly2.jpeg",  (480, 960, 1600)),
    # rooftop (fly4.jpeg) e uscita dal sito su richiesta del titolare.
    # Il sorgente resta fra i sorgenti; rigenerarla qui non la rimette in
    # pagina, servono anche il <figure> in index.html e una griglia che la ospiti.
    ("montaggio", "perg2.jpeg", (480, 960, 1280)),
]


def main(src: Path, poster: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, fname, widths in JOBS:
        im = Image.open(src / fname).convert("RGB")
        widths = sorted({min(w, im.width) for w in widths})
        for w in widths:
            h = round(im.height * w / im.width)
            r = im.resize((w, h), Image.LANCZOS)
            r.save(OUT / f"{slug}-{w}.avif", quality=62)
            r.save(OUT / f"{slug}-{w}.webp", quality=80, method=6)
            r.save(OUT / f"{slug}-{w}.jpg", quality=82, optimize=True, progressive=True)
        print(f"  {slug}: {im.width}x{im.height} -> {widths}")

    p = Image.open(poster).convert("RGB")
    p.save(ROOT / "assets" / "img" / "home" / "pergole-poster.jpg",
           quality=80, optimize=True, progressive=True)
    print("  pergole-poster.jpg", p.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
