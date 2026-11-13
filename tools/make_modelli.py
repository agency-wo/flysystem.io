"""Le tavole tecniche delle quattro misure Bolla.

NON SONO QUELLO CHE LE SCHEDE MONTANO OGGI. Le schede portano fotografie di
installazioni reali, ingrandite col modello fedele (le voci "pagina:" di
enhance.py). Queste tavole sono state fatte, guardate e messe da parte su
decisione del cliente, che le vuole fotografiche. Restano qui perche' il
disegno quotato e' l'unica immagine che dimostra la misura di cui parla la
scheda, e se un giorno servira' una sezione tecnica si rigenera da qui.
Scrivono con prefisso "tec-" proprio per non sovrascrivere le fotografie.

PERCHE' UN TOOL NUOVO E NON make_bolla_models.py. Quello ritaglia FOTOGRAFIE
dalle pagine del catalogo da 16, per la gamma vecchia (r400...g500, suite).
Qui la gamma e' quella del catalogo nuovo, 300/400/500/600 UP, e l'immagine
non e' una fotografia ma il disegno tecnico quotato. Sono due sorgenti e due
gamme diverse: tenerli separati e' piu' onesto che piegare l'uno all'altro.

COSA PRODUCE. Una tavola 3:4 per misura, perche' 3:4 e' il riquadro che
.modello__foto monta gia': il markup della scheda non cambia di una riga.
Dentro, il prospetto quotato sopra e la vista tridimensionale sotto, cioe' i
due disegni che nel catalogo stanno affiancati e che in orizzontale non
entrerebbero mai in un riquadro verticale.

PERCHE' SI RENDE LA PAGINA. Il prospetto, che e' la parte che porta le QUOTE,
e' vettoriale: reso a 400 dpi resta nitido a qualunque misura, senza modello e
senza il tetto di risoluzione che hanno le fotografie di questo catalogo. La
vista 3D accanto e' invece un raster da circa 430 px posato a 103 dpi: quella
non migliora, e infatti sta nella banda piu' piccola.

DUE COSE CHE RESTANO FUORI DA OGNI RITAGLIO. Il numero di pagina stampato in
basso (sta fra 0,95 e 0,97 dell'altezza: il fondo dei ritagli si ferma prima),
e qualunque cartellino "Credit:". Nella prima prova il numero di pagina era
entrato nelle tavole 300 e 500 e, gonfiandone l'altezza, le aveva anche
rimpicciolite rispetto alle altre due: la famiglia sembrava sbagliata di scala
per un motivo che non era di disegno.

I colori non restano nero su bianco: si rimappano sui token del sito, --paper
e --ink, con l'antialiasing che scorre fra i due.

    python tools/make_modelli.py
"""
import os
from pathlib import Path

import fitz
import pillow_avif  # noqa: F401
from PIL import Image

ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "img" / "bolla" / "modelli"
PDF = ROOT / "_sorgenti" / "Fly_System_Bolla_Capsula_Catalogue_261112_135714.pdf"
PAGINE_ATTESE = 124

# --paper e --ink di assets/css/style.css
PAPER = (0xF1, 0xF2, 0xF3)
INK = (0x14, 0x17, 0x1D)

# slug, pagina, prospetto quotato, vista 3D   (frazioni di pagina)
JOBS = [
    ("tec-300up", 18, (0.028, 0.685, 0.382, 0.935), (0.384, 0.592, 0.892, 0.958)),
    ("tec-400up", 19, (0.070, 0.645, 0.468, 0.935), (0.478, 0.567, 0.978, 0.934)),
    ("tec-500up", 20, (0.024, 0.662, 0.436, 0.935), (0.438, 0.607, 0.906, 0.945)),
    ("tec-600up", 21, (0.066, 0.666, 0.512, 0.935), (0.514, 0.595, 0.985, 0.936)),
]

DPI = 400
MASTER = 1200                      # 3:4, poi si riduce alle larghezze del sito
LARGHEZZE = (240, 480, 800, 1030)  # le stesse delle schede di prima


def taglia(im, soglia=248):
    """Via il bianco attorno: il disegno si allinea al proprio contenuto, non
    al punto in cui il catalogo lo aveva posato nella pagina."""
    g = im.convert("L")
    bbox = g.point(lambda v: 255 if v < soglia else 0).getbbox()
    return im.crop(bbox) if bbox else im


def tinge(im):
    """Bianco -> --paper, nero -> --ink, e le vie di mezzo in proporzione."""
    g = im.convert("L")
    tav = []
    for canale in range(3):
        for v in range(256):
            tav.append(round(INK[canale] + (PAPER[canale] - INK[canale]) * (v / 255.0)))
    return Image.merge("RGB", (g, g, g)).point(tav)


def dentro(im, larg, alt):
    z = min(larg / im.width, alt / im.height)
    return im.resize((max(1, round(im.width * z)), max(1, round(im.height * z))),
                     Image.LANCZOS)


def tavola(pagina, rp, r3):
    def ritaglia(r):
        l, t, rr, b = r
        return taglia(pagina.crop((round(l * pagina.width), round(t * pagina.height),
                                   round(rr * pagina.width), round(b * pagina.height))))

    prospetto, vista = tinge(ritaglia(rp)), tinge(ritaglia(r3))

    alt = MASTER * 4 // 3
    marg = round(MASTER * 0.085)
    stacco = round(MASTER * 0.045)
    tela = Image.new("RGB", (MASTER, alt), PAPER)
    utile = MASTER - 2 * marg
    banda_p = round(alt * 0.40)
    banda_v = alt - banda_p - stacco - 2 * marg

    a = dentro(prospetto, utile, banda_p)
    b = dentro(vista, utile, banda_v)
    tela.paste(a, ((MASTER - a.width) // 2, marg + (banda_p - a.height) // 2))
    tela.paste(b, ((MASTER - b.width) // 2, marg + banda_p + stacco + (banda_v - b.height) // 2))
    return tela


def main():
    if not PDF.exists():
        raise SystemExit(f"manca {PDF}: e' l'originale del cliente")
    doc = fitz.open(PDF)
    if doc.page_count != PAGINE_ATTESE:
        raise SystemExit(
            f"{PDF.name} ha {doc.page_count} pagine invece di {PAGINE_ATTESE}: "
            "i ritagli qui sotto sono misurati su quello e qui non valgono")
    OUT.mkdir(parents=True, exist_ok=True)

    for slug, n, rp, r3 in JOBS:
        p = doc[n - 1]
        pix = p.get_pixmap(matrix=fitz.Matrix(DPI / 72.0, DPI / 72.0))
        pagina = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        t = tavola(pagina, rp, r3)
        print(f"  {slug}  da p{n}")
        for w in LARGHEZZE:
            h = round(t.height * w / t.width)
            r = t.resize((w, h), Image.LANCZOS)
            # niente maschera di contrasto: su un tratto gia' netto creerebbe
            # un alone attorno alle linee invece di aggiungere dettaglio
            r.save(OUT / f"{slug}-{w}.avif", quality=82)
            r.save(OUT / f"{slug}-{w}.webp", quality=90, method=6)
            r.save(OUT / f"{slug}-{w}.jpg", quality=92, optimize=True, progressive=True)
            print(f"    {slug}-{w}: {w}x{h}")


if __name__ == "__main__":
    main()
