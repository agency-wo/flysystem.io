"""Rigenera un'immagine del sito ingrandendo con modello il raster ORIGINALE.

Il punto che fa la differenza fra un buon risultato e un pasticcio: le immagini
Bolla oggi sul sito sono gia un ingrandimento Lanczos 2,1x di un raster da
344 px. Passare QUELLE al modello significa fargli ricostruire sopra i nostri
artefatti. Qui si parte sempre dall'originale nativo.

Catena:
  1. raster originale (xref del PDF, oppure il .jpeg del cliente)
  2. ingrandimento 4x con realesrgan-ncnn-vulkan (GPU, in locale)
  3. ritaglio all'inquadratura gia approvata, confrontando con cio che
     serviamo adesso, cosi la composizione non cambia
  4. riduzione alle larghezze bersaglio, Lanczos piu maschera di contrasto
  5. codifica AVIF/WebP/JPEG

uso:
  python tools/enhance.py <cartella/nome> pdf:<catalogo>:<xref> [larghezze] [modello]
  python tools/enhance.py <cartella/nome> file:<_sorgenti/fly8.jpeg> [larghezze] [modello]

  modello: realesrgan-x4plus (generativo, default) | realesrnet-x4plus (fedele)
"""
import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz
import pillow_avif  # noqa: F401
from PIL import Image, ImageFilter

GAN = "realesrgan-x4plus"   # generativo
NET = "realesrnet-x4plus"  # fedele

ROOT = Path(__file__).parent.parent
IMG = ROOT / "assets" / "img"
BIN = ROOT / "tools" / "bin" / "realesrgan-ncnn-vulkan.exe"
MODELS = ROOT / "tools" / "bin" / "models"


# ---------------------------------------------------------------------------
# Chi va ingrandito, da dove, con quale modello.
#
# GRUPPO A, generativo (realesrgan-x4plus): cupole, pergole, architettura.
#   La texture ricostruita e erba, cielo, vetro: non e una specifica di
#   prodotto, e il guadagno di nitidezza e enorme.
#
# GRUPPO B, fedele (realesrnet-x4plus): porte, gres, copertine.
#   Verificato sui provini: su una porta laccata i due modelli danno lo stesso
#   risultato, e sul pavimento in gres il generativo LEVIGA la venatura del
#   marmo mentre il fedele la conserva. Quindi qui il fedele non e una
#   rinuncia, e la scelta migliore anche sul piano della resa.
#
# (slug, sorgente, larghezze, modello, correzione dominante opzionale)
JOBS = [
    # --- Bolla, dal raster nativo del catalogo (344-691 px) ---
    ("bolla/notte-palme",      "pdf:fly-system-bolla:21", (480, 960, 1376), GAN, None),
    ("bolla/amaca",            "pdf:fly-system-bolla:57", (480, 960, 1376), GAN, None),
    ("bolla/suite",            "pdf:fly-system-bolla:61", (480, 960, 1376), GAN, None),
    ("bolla/dusk-garden",      "pdf:fly-system-bolla:4",  (480, 960, 1440, 2400), GAN, None),
    ("bolla/glamping-aerial",  "pdf:fly-system-bolla:39", (480, 960, 1440, 2400), GAN, None),

    # --- schede modello Bolla ---
    ("bolla/modelli/r400",  "pdf:fly-system-bolla:52", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/r500",  "pdf:fly-system-bolla:21", (240, 480, 800, 1030), GAN, None),
    # la 650 e ripresa con LED verdi: la dominante va neutralizzata come in V14,
    # altrimenti l'ingrandimento restituisce una sala verde molto piu nitida
    ("bolla/modelli/r650",  "pdf:fly-system-bolla:26", (240, 480, 800, 1030), GAN, 0.55),
    ("bolla/modelli/r800",  "pdf:fly-system-bolla:22", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/r1000", "pdf:fly-system-bolla:32", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/g400",  "pdf:fly-system-bolla:56", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/g500",  "pdf:fly-system-bolla:51", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/suite", "pdf:fly-system-bolla:61", (240, 480, 800, 1030), GAN, None),

    # --- fotografie del cliente: il .jpeg E gia l'originale ---
    ("bolla/glamping-inverno", "file:_sorgenti/fly1.jpeg", (480, 960, 1440, 2160), GAN, None),
    ("home/selezione",         "file:_sorgenti/fly8.jpeg", (480, 960, 1440, 2880), GAN, None),
    ("outdoor/montaggio",      "file:_sorgenti/perg2.jpeg", (480, 960, 1280, 2592), GAN, None),
    ("outdoor/tramonto",       "file:_sorgenti/fly2.jpeg", (480, 960, 1600, 2880), GAN, None),
    ("outdoor/rooftop",        "file:_sorgenti/fly4.jpeg", (480, 960, 1600), GAN, None),
    ("contatti/lead",          "file:_sorgenti/fly9.jpeg", (480, 960, 1440, 2400), GAN, None),

    # --- architettura: la nostra stessa immagine e l'originale piu grande ---
    ("home/hero-edificio", "file:assets/img/home/hero-edificio-1920.jpg",
     (480, 960, 1600, 1920, 2880), GAN, None),
]



def firma(im, n=24):
    b = im.convert("L").resize((n, n), Image.LANCZOS).tobytes()
    med = sum(b) / len(b)
    return [1 if p > med else 0 for p in b]


def distanza(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def ritaglio_che_combacia(orig, riferimento):
    """Il taglio dell'originale che riproduce l'inquadratura attuale."""
    tr = riferimento.width / riferimento.height
    f_rif = firma(riferimento)
    W, H = orig.size
    h = round(W / tr)
    if h <= H:
        best, mig = 10 ** 9, None
        for k in range(21):
            top = round((H - h) * k / 20)
            c = orig.crop((0, top, W, top + h))
            d = distanza(firma(c), f_rif)
            if d < best:
                best, mig = d, c
        return mig, best
    w = round(H * tr)
    best, mig = 10 ** 9, None
    for k in range(21):
        left = round((W - w) * k / 20)
        c = orig.crop((left, 0, left + w, H))
        d = distanza(firma(c), f_rif)
        if d < best:
            best, mig = d, c
    return mig, best


def originale(spec):
    """Restituisce il raster nativo, senza margini di carta ne testo di pagina."""
    tipo, resto = spec.split(":", 1)
    if tipo == "pdf":
        catalogo, xref = resto.rsplit(":", 1)
        doc = fitz.open(ROOT / "assets" / "pdf" / f"{catalogo}.pdf")
        info = doc.extract_image(int(xref))
        return Image.open(io.BytesIO(info["image"])).convert("RGB")
    return Image.open(ROOT / resto).convert("RGB")


def ingrandisci(im, modello, scala=4):
    if not BIN.exists():
        raise SystemExit(f"manca {BIN}: vedi README per riscaricarlo")
    tmp = Path(tempfile.mkdtemp())
    try:
        src, dst = tmp / "in.png", tmp / "out.png"
        im.save(src)
        # -t 256: la 3050 ha 4 GB, senza piastrellatura una sorgente grande
        # esaurisce la memoria a 4x
        r = subprocess.run(
            [str(BIN), "-i", str(src), "-o", str(dst), "-n", modello,
             "-s", str(scala), "-m", str(MODELS), "-t", "256", "-f", "png"],
            capture_output=True, text=True)
        if not dst.exists():
            raise SystemExit(f"ingrandimento fallito:\n{r.stderr[-800:]}")
        return Image.open(dst).convert("RGB")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def neutralizza(im, forza):
    """Riduce una dominante di colore verso il grigio del mondo (vedi V14)."""
    from PIL import ImageStat
    r, g, b = ImageStat.Stat(im).mean[:3]
    grigio = (r + g + b) / 3
    f = [1 + (grigio / c - 1) * forza for c in (r, g, b)]
    print(f"    dominante corretta: R{f[0]:.3f} G{f[1]:.3f} B{f[2]:.3f}")
    return im.point(sum(([min(255, round(i * k)) for i in range(256)] for k in f), []))


def main(nome, spec, larghezze, modello, corr=None):
    out = IMG / Path(nome).parent
    slug = Path(nome).name
    attuali = sorted(out.glob(f"{slug}-*.jpg"), key=lambda p: Image.open(p).width)
    if not attuali:
        raise SystemExit(f"nessuna immagine attuale per {nome}: non so quale ritaglio tenere")
    riferimento = Image.open(attuali[-1]).convert("RGB")

    orig = originale(spec)
    print(f"  originale {orig.width}x{orig.height}  (serviamo {riferimento.width}x{riferimento.height})")

    grande = ingrandisci(orig, modello)
    print(f"  ingrandita {grande.width}x{grande.height} con {modello}")

    if corr:
        grande = neutralizza(grande, corr)
    crop, d = ritaglio_che_combacia(grande, riferimento)
    print(f"  ritaglio {crop.width}x{crop.height}, distanza dal riferimento {d}/576")

    for w in sorted({min(w, crop.width) for w in larghezze}):
        h = round(crop.height * w / crop.width)
        r = crop.resize((w, h), Image.LANCZOS)
        r = r.filter(ImageFilter.UnsharpMask(radius=1.0, percent=40, threshold=3))
        r.save(out / f"{slug}-{w}.avif", quality=78)
        r.save(out / f"{slug}-{w}.webp", quality=84, method=6)
        r.save(out / f"{slug}-{w}.jpg", quality=86, optimize=True, progressive=True)
        print(f"    {slug}-{w}: {w}x{h}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--tutto":
        solo = sys.argv[2] if len(sys.argv) > 2 else ""
        for nome, spec, larghezze, modello, corr in JOBS:
            if solo and not nome.startswith(solo):
                continue
            print("")
            print("== " + nome)
            try:
                main(nome, spec, larghezze, modello, corr)
            except SystemExit as e:
                print("   SALTATA: " + str(e))
    else:
        larghezze = [int(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else "480,960")]
        modello = sys.argv[4] if len(sys.argv) > 4 else GAN
        main(sys.argv[1], sys.argv[2], larghezze, modello)
