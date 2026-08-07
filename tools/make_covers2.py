"""Copertine dei cataloghi come serie fotografica unica.

Prima ogni copertina era la pagina 1 del PDF: tre avevano la toppa bianca del
rebrand visibile dietro il logo, una era una tavola RAL da 90 campioni saturi,
due erano pagine piene arancio e zafferano, e quella dell'ammiraglia Bolla era
solo il logo su bianco (sembrava un'immagine mancante). Diverse mostravano
ancora il vecchio logo. In tutto sono circa il 40% della superficie del sito.

Ora sono 14 fotografie reali, tutte allo stesso rapporto 1:1,375, senza testo:
il titolo resta nel markup, quindi nitido, accessibile e traducibile.

usage: python make_covers2.py <cartella-ritagli>
"""
import sys
from pathlib import Path

import pillow_avif  # noqa: F401
from PIL import Image

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "img" / "cataloghi" / "covers"
RATIO = 1.375
WIDTHS = (480, 960)

# le pagine di questo catalogo sono impaginate ruotate di 90 gradi
ROTATE = {"vetrate": -90}


def main(src: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob("*.png")):
        slug = f.stem
        if "_" in slug or slug in {"ALL"} or slug.endswith("prev"):
            continue
        im = Image.open(f).convert("RGB")
        if slug in ROTATE:
            im = im.rotate(ROTATE[slug], expand=True)
        # normalizza al rapporto della serie
        want_h = round(im.width * RATIO)
        if want_h <= im.height:
            top = round((im.height - want_h) / 2)
            im = im.crop((0, top, im.width, top + want_h))
        else:
            want_w = round(im.height / RATIO)
            left = round((im.width - want_w) / 2)
            im = im.crop((left, 0, left + want_w, im.height))
        for w in WIDTHS:
            h = round(w * RATIO)
            rs = im.resize((w, h), Image.LANCZOS)
            rs.save(OUT / f"c-{slug}-{w}.avif", quality=62)
            rs.save(OUT / f"c-{slug}-{w}.webp", quality=80, method=6)
            rs.save(OUT / f"c-{slug}-{w}.jpg", quality=82, optimize=True, progressive=True)
        print(f"  c-{slug}: {im.size}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
