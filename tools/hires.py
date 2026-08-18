"""Rigenera un'immagine del sito dal raster ORIGINALE incorporato nel PDF.

Perche non renderizzare la pagina, che e il metodo usato finora: il rendering
di pagina eredita i margini di carta bianchi e soprattutto i nomi di altri
marchi stampati nella pagina ("SLIDING FLOOR", "STARGLASS", "MC"), che poi
vanno ritagliati via a mano. Il raster incorporato e la sola fotografia, alla
sua risoluzione piena, senza niente sopra.

Trova anche da solo il ritaglio: l'immagine attuale del sito e quasi sempre un
taglio dell'originale, quindi prova le posizioni verticali e tiene quella che
somiglia di piu a cio che stiamo gia servendo, cosi la composizione approvata
non cambia.

    python tools/hires.py <cartella/nome> <catalogo> <xref> [larghezze]

esempio:
    python tools/hires.py home/notte fly-system-vetrate-panoramiche 138 480,960,1440,2217
"""
import io
import sys
from pathlib import Path

import fitz
import pillow_avif  # noqa: F401
from PIL import Image, ImageFilter

ROOT = Path(__file__).parent.parent
IMG = ROOT / "assets" / "img"


def firma(im, n=24):
    im = im.convert("L").resize((n, n), Image.LANCZOS)
    b = im.tobytes()
    med = sum(b) / len(b)
    return [1 if p > med else 0 for p in b]


def distanza(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def ritaglio_che_combacia(orig, riferimento):
    """Cerca il taglio dell'originale che riproduce l'inquadratura attuale."""
    tr = riferimento.width / riferimento.height
    f_rif = firma(riferimento)
    W, H = orig.size
    h = round(W / tr)
    if h <= H:
        migliore, best = None, 10 ** 9
        for k in range(0, 21):
            top = round((H - h) * k / 20)
            c = orig.crop((0, top, W, top + h))
            d = distanza(firma(c), f_rif)
            if d < best:
                best, migliore = d, c
        return migliore, best
    w = round(H * tr)
    migliore, best = None, 10 ** 9
    for k in range(0, 21):
        left = round((W - w) * k / 20)
        c = orig.crop((left, 0, left + w, H))
        d = distanza(firma(c), f_rif)
        if d < best:
            best, migliore = d, c
    return migliore, best


def main(nome, catalogo, xref, larghezze):
    out = IMG / Path(nome).parent
    slug = Path(nome).name
    esistenti = sorted(out.glob(f"{slug}-*.jpg"), key=lambda p: Image.open(p).width)
    if not esistenti:
        raise SystemExit(f"nessuna immagine attuale per {nome}: non so quale ritaglio tenere")
    riferimento = Image.open(esistenti[-1]).convert("RGB")

    doc = fitz.open(ROOT / "assets" / "pdf" / f"{catalogo}.pdf")
    info = doc.extract_image(int(xref))
    orig = Image.open(io.BytesIO(info["image"])).convert("RGB")
    print(f"  originale: {orig.width}x{orig.height}  (attuale {riferimento.width}x{riferimento.height})")

    crop, d = ritaglio_che_combacia(orig, riferimento)
    print(f"  ritaglio scelto: {crop.width}x{crop.height}, distanza dal riferimento {d}/576")

    for w in sorted({min(w, crop.width) for w in larghezze}):
        h = round(crop.height * w / crop.width)
        r = crop.resize((w, h), Image.LANCZOS)
        r = r.filter(ImageFilter.UnsharpMask(radius=1.0, percent=45, threshold=3))
        r.save(out / f"{slug}-{w}.avif", quality=78)
        r.save(out / f"{slug}-{w}.webp", quality=84, method=6)
        r.save(out / f"{slug}-{w}.jpg", quality=86, optimize=True, progressive=True)
        print(f"    {slug}-{w}: {w}x{h}")


if __name__ == "__main__":
    larghezze = [int(x) for x in (sys.argv[4].split(",") if len(sys.argv) > 4 else "480,960,1440".split(","))]
    main(sys.argv[1], sys.argv[2], sys.argv[3], larghezze)
