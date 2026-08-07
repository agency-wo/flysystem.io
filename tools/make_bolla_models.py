"""Miniature dei singoli modelli Bolla, estratte dalle pagine del catalogo.

Servono a dare una faccia a ogni misura: prima l'elenco dei modelli era solo
testo, e sul telefono si riduceva a una colonna di numeri con i nomi schiacciati.

Ogni ritaglio e 3:4 e viene preso dentro il blocco fotografico della pagina
(niente margini di carta, niente didascalie, niente logo).

usage: python make_bolla_models.py
"""
from pathlib import Path

import fitz
import pillow_avif  # noqa: F401
from PIL import Image

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "img" / "bolla" / "modelli"
PDF = ROOT / "assets" / "pdf" / "fly-system-bolla.pdf"

# slug, pagina, box frazionario del blocco fotografico, ancoraggio verticale
# del ritaglio 3:4 (0 = alto, 0.5 = centro, 1 = basso)
JOBS = [
    ("r400", 4, (0.017, 0.012, 0.455, 0.496), 0.5),
    ("r500", 5, (0.551, 0.012, 0.989, 0.496), 0.5),
    ("r650", 6, (0.017, 0.012, 0.455, 0.496), 0.5),
    # la foto della 800 in catalogo e un montaggio in corso: qui va una sala
    # vera della stessa linea, il dato esatto lo porta comunque la riga
    ("r800", 5, (0.551, 0.504, 0.989, 0.992), 0.5),
    ("r1000", 7, (0.518, 0.090, 0.928, 0.730), 0.45),
    ("g500", 9, (0.066, 0.534, 0.491, 0.862), 0.5),
    ("g400", 12, (0.551, 0.012, 0.983, 0.496), 0.5),
    ("suite", 13, (0.017, 0.012, 0.455, 0.496), 0.5),
]

WIDTHS = (240, 480)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    for slug, page, box, anchor in JOBS:
        pg = doc[page - 1]
        z = 2600 / max(pg.rect.width, pg.rect.height)
        pix = pg.get_pixmap(matrix=fitz.Matrix(z, z))
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        l, t, r, b = box
        im = im.crop((round(l * im.width), round(t * im.height),
                      round(r * im.width), round(b * im.height)))
        # ritaglio 3:4 dentro il blocco
        target_h = round(im.width * 4 / 3)
        if target_h <= im.height:
            top = round((im.height - target_h) * anchor)
            im = im.crop((0, top, im.width, top + target_h))
        else:
            target_w = round(im.height * 3 / 4)
            left = round((im.width - target_w) / 2)
            im = im.crop((left, 0, left + target_w, im.height))
        for w in WIDTHS:
            h = round(im.height * w / im.width)
            rs = im.resize((w, h), Image.LANCZOS)
            rs.save(OUT / f"{slug}-{w}.avif", quality=60)
            rs.save(OUT / f"{slug}-{w}.webp", quality=78, method=6)
            rs.save(OUT / f"{slug}-{w}.jpg", quality=80, optimize=True, progressive=True)
        print(f"  {slug}: p{page} -> {im.size}")


if __name__ == "__main__":
    main()
