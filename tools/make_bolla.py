"""Estrae la galleria Bolla dal catalogo Bolle Luxury + foto glamping invernale.

Rende le pagine a 2400px, ritaglia le foto (frazioni), auto-trim dei margini
carta, codifica AVIF/WebP/JPEG a 480/960(/1440) in assets/img/bolla/.

usage: python make_bolla.py <bolla.pdf> <sorgenti-dir>
"""
import sys
from pathlib import Path

import fitz
import pillow_avif  # noqa: F401
from PIL import Image, ImageFilter

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "img" / "bolla"

# (slug, pagina, (x0,y0,x1,y1) frazioni pagina, widths)
JOBS = [
    ("dusk-garden",     2,  (0.050, 0.070, 0.950, 0.528), (480, 960, 1440)),
    # V14: "costa" e uscito. Era lo scatto bocciato dal cliente: doppia
    # esposizione, la cupola sovrapposta alle luci della citta e i palloncini
    # rossi tagliati a meta sul bordo. Non si sostituisce con un ritaglio
    # qualsiasi, si toglie e basta.
    ("notte-palme",     5,  (0.510, 0.008, 0.985, 0.472), (480, 960)),
    ("glamping-aerial", 9,  (0.050, 0.070, 0.950, 0.528), (480, 960, 1440)),
    # "tavolo" e passato alla scheda del modello 400, dove la tavola
    # apparecchiata illustra esattamente cio che la scheda descrive. In
    # galleria al suo posto entra l'amaca sotto la cupola specchiata.
    ("amaca",           12, (0.550, 0.502, 0.984, 0.990), (480, 960)),
    # V15: "vista-mare" e uscito. Era la foto piu debole della galleria (primo
    # piano occupato da un cuscino blu) ed era finita nello spazio piu largo
    # della pagina per via della regola figure:last-child, dove un file da
    # 710 px veniva reso a 1296 css: x3,65, il peggio del sito.
    ("suite",           13, (0.015, 0.025, 0.475, 0.498), (480, 960)),
]

INSET = 0.016  # taglio finale: elimina gli angoli arrotondati delle foto in pagina


def autotrim(im: Image.Image, thr=222, frac=0.90) -> Image.Image:
    """Rimuove bordi quasi-carta (min-channel > thr su > frac dei pixel)."""
    px = im.load()
    w, h = im.size

    def row_paper(y):
        n = sum(1 for x in range(w) if min(px[x, y][:3]) > thr)
        return n / w > frac

    def col_paper(x):
        n = sum(1 for y in range(h) if min(px[x, y][:3]) > thr)
        return n / h > frac

    top = 0
    while top < h - 1 and row_paper(top):
        top += 1
    bot = h - 1
    while bot > top and row_paper(bot):
        bot -= 1
    left = 0
    while left < w - 1 and col_paper(left):
        left += 1
    right = w - 1
    while right > left and col_paper(right):
        right -= 1
    return im.crop((left, top, right + 1, bot + 1))


def encode(im: Image.Image, slug: str, widths):
    """Codifica le uscite.

    Due scelte di V15, entrambe motivate dal fatto che le fotografie del
    catalogo Bolla partono da raster di 344x543 px:

    - maschera di contrasto dopo il ricampionamento. Non inventa dettaglio, ma
      recupera nitidezza percepita su un'immagine gia ingrandita, ed e comunque
      meglio del ridimensionamento bilineare che farebbe il browser se gli
      lasciassimo stirare un file troppo piccolo;
    - qualita alzata da 62 a 78 (AVIF). Su fotografie gia morbide il q62
      aggiungeva impasto proprio dove si nota di piu.
    """
    widths = sorted({min(w, im.width) for w in widths})
    for w in widths:
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS)
        r = r.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=3))
        r.save(OUT / f"{slug}-{w}.avif", quality=78)
        r.save(OUT / f"{slug}-{w}.webp", quality=84, method=6)
        r.save(OUT / f"{slug}-{w}.jpg", quality=86, optimize=True, progressive=True)
    print(f"  {slug}: master {im.width}x{im.height}, widths {[w for w in widths if w <= im.width]}")


def main(pdf: Path, sorgenti: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    for slug, pno, (x0, y0, x1, y1), widths in JOBS:
        page = doc[pno - 1]
        scale = 2400 / max(page.rect.width, page.rect.height)
        pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
        crop = im.crop((round(im.width * x0), round(im.height * y0),
                        round(im.width * x1), round(im.height * y1)))
        crop = autotrim(crop)
        ix, iy = round(crop.width * INSET), round(crop.height * INSET)
        crop = crop.crop((ix, iy, crop.width - ix, crop.height - iy))
        encode(crop, slug, widths)

    winter = Image.open(sorgenti / "fly1.jpeg").convert("RGB")
    encode(winter, "glamping-inverno", (480, 960, 1080))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
