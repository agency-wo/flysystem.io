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
  python tools/enhance.py <cartella/nome> pagina:<catalogo>:<n>:<l,t,r,b> [larghezze] [modello]

  modello: realesrgan-x4plus (generativo, default) | realesrnet-x4plus (fedele)

Le tre sorgenti, e quando si usa quale:

  pdf:     il raster nativo per xref. Va bene finche una fotografia sta in UNA
           sola immagine dentro il PDF.
  pagina:  rende la pagina al suo dpi nativo e ne ritaglia un riquadro
           frazionario. Serve quando la fotografia e spezzata in strisce
           affiancate, come nel catalogo bolla e capsula (2.215 raster), dove
           extract_image restituisce frammenti e mai l'immagine intera.
  file:    un originale fotografico mandato dal cliente.

Solo `pagina:` puo generare uno slug NUOVO, perche porta gia il riquadro con
se. Le altre due si riagganciano all'inquadratura di cio che il sito serve
adesso, quindi pretendono che quello slug esista gia.
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
NESSUNO = None              # nessun modello: la sorgente ha gia i pixel che servono

# I due cataloghi Bolla, per NOME DEL FILE ORIGINALE e non per il nome con cui
# vengono pubblicati.
#
# Perche conta. Queste voci dicevano "pdf:fly-system-bolla:<xref>", cioe il
# nome del file in assets/pdf. Il 2026-11 quel nome ha cambiato contenuto: da
# 16 pagine a 124, perche il cliente ha mandato l'edizione nuova e si e tenuto
# lo stesso indirizzo per non rompere i link. Gli xref pero non sono stati
# scritti per quel file. Verificato: l'xref 4 e il 57 non risolvono piu, e il
# 52 risolve a un'ALTRA immagine, una striscia 1055x166. Cioe un
# `enhance.py --tutto bolla` avrebbe riscritto in silenzio le schede modello
# con dei frammenti di pagina, senza un errore.
#
# Puntando all'originale in _sorgenti il problema non si ripresenta: quel file
# non viene mai ripubblicato, quindi il suo nome non cambia contenuto.
BOLLA16 = "pdf:flysystem catalogo bolla ristorazione e glamping"
BOLLA26 = "pagina:Fly_System_Bolla_Capsula_Catalogue_261112_135714"

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
    # --- Bolla, fotografie nuove dal catalogo bolla e capsula (124 pagine) ---
    # Si rende la PAGINA, non il raster: quel catalogo e composto da 2.215
    # immagini affiancate, quindi extract_image restituisce strisce. Vedi
    # originale().
    #
    # Modello FEDELE e non generativo: sono installazioni reali di clienti, e
    # un generativo inventerebbe dettaglio che nella fotografia non c'e.
    #
    # I riquadri tengono fuori DUE cose che non devono finire sul sito:
    #   - il numero di pagina stampato in basso (sta sopra lo 0,94 dell'altezza);
    #   - i cartellini "Credit:" col nome del locale, l'indirizzo per esteso e
    #     il profilo social, che sono scritti DENTRO la fotografia. Pubblicarne
    #     uno metterebbe sul sito del nostro cliente il nome e l'indirizzo di
    #     un'attivita terza, come se fosse una referenza raccolta da noi.
    # ATTENZIONE AL CAPITOLO, non solo all'inquadratura. Il catalogo ha un
    # capitolo ESTATE (p54-59) e p6 lo spiega: "Stessa struttura, copertura
    # diversa". Stesso telaio, rivestimento in telo al posto della cupola
    # trasparente. Il 2026-11-13 la foto della home era p57, cioe' dentro quel
    # capitolo: in home c'era il telo e non il prodotto di cui parla la pagina.
    # Se ne e' accorto il cliente, non noi. Le pagine buone per la cupola
    # trasparente sono Ho.Re.Ca p26-33, Glamping p34-45, Contesti p64-83.
    ("bolla/cena-giardino",   BOLLA26 + ":30:0.163,0.225,0.837,0.940", (480, 960, 996), NET, None),
    ("bolla/terrazza-lago",   BOLLA26 + ":76:0.010,0.330,0.990,0.842", (480, 960, 1451), NET, None),
    ("bolla/mare-tramonto",   BOLLA26 + ":31:0.135,0.140,0.865,0.935", (480, 960, 1376), NET, None),
    ("bolla/collina-sera",    BOLLA26 + ":40:0.158,0.170,0.842,0.935", (480, 960, 1373), NET, None),

    # La fascia di apertura, cioe la PRIMA fotografia della pagina Bolla.
    # Sostituisce cupola-luci su richiesta del cliente, che di quella scena non
    # era convinto ("Ket e zevendeson dot"), mentre il resto gli andava bene.
    # p78 e dal capitolo Contesti: due cupole accese all'ora blu su un dehors,
    # che e esattamente cio che dice la didascalia. Nessun cartellino "Credit:"
    # e nessuna faccia riconoscibile, che e il motivo per cui p67 e p70, pure
    # belle, sono rimaste fuori.
    ("bolla/dehors-sera", BOLLA26 + ":78:0.005,0.280,0.995,0.797", (480, 960, 1440, 2160), NET, None),

    # camera-sera e neve-tavola NON hanno una voce qui: tengono la fotografia
    # della passata precedente e hanno solo cambiato nome, perche il contenuto
    # era gia cambiato e l'indirizzo no. Rigenerarle le cambierebbe una seconda
    # volta senza motivo.

    # --- schede modello della gamma 2026: fotografie, non disegni ---
    #
    # QUALE MISURA C'E' IN QUALE FOTO. Il catalogo lo dice UNA volta sola, a
    # p13: "Nella sua configurazione 600UP, la struttura ospita fino a 30
    # persone circa". Le altre 41 pagine fotografiche dei capitoli Ho.Re.Ca e
    # Contesti non nominano nessuna misura. Quindi la 600 UP e dichiarata dal
    # catalogo, le altre tre sono ABBINATE DA NOI, su decisione del cliente.
    # Sta scritto qui perche fra sei mesi non sembri un dato di catalogo.
    #
    # L'abbinamento non e a caso: si guarda quanti tavoli e quanta gente si
    # vedono dentro la cupola e lo si tiene coerente con la capienza stampata
    # sulla scheda. Una sala da trenta coperti sotto la "300 UP" si vedrebbe.
    #
    # I riquadri tengono fuori il numero di pagina e il cartellino "Credit:"
    # col nome e l'indirizzo del locale: su p43 sta in alto, sulle altre tre in
    # basso, e i tagli sono diversi per questo.
    # p42 e non p43: stessa scena (camera con letto, due persone) ma posata a
    # 125 dpi invece che a 74, i piu' poveri del catalogo. Trecento pixel in
    # piu' nell'originale valgono piu' di qualunque ingrandimento, e p42 non
    # porta nemmeno il cartellino "Credit:".
    ("bolla/modelli/300up", BOLLA26 + ":42:0.108,0.180,0.892,0.920", (240, 480, 800, 1030), NET, None),
    ("bolla/modelli/400up", BOLLA26 + ":15:0.150,0.220,0.850,0.880", (240, 480, 800, 1030), NET, None),
    ("bolla/modelli/500up", BOLLA26 + ":81:0.190,0.200,0.879,0.850", (240, 480, 800, 1030), NET, None),
    # il bordo alto parte da 0,340 e non da 0,320: sopra la fotografia p13 ha
    # un blocco di testo su fondo bianco, e a 0,320 ne entrava una striscia che
    # sulla scheda si vedeva come una banda chiara in cima all'immagine
    ("bolla/modelli/600up", BOLLA26 + ":13:0.095,0.340,0.667,0.880", (240, 480, 800, 1030), NET, None),

    # --- schede modello Bolla ---
    ("bolla/modelli/r400",  BOLLA16 + ":52", (240, 480, 800, 1030), GAN, None),
    # V18: stessa scena della fascia di punta, quindi stesso originale vero
    ("bolla/modelli/r500",  "file:_sorgenti/bollafly.jpeg", (240, 480, 800, 1030), NESSUNO, None),
    # la 650 e ripresa con LED verdi: la dominante va neutralizzata come in V14,
    # altrimenti l'ingrandimento restituisce una sala verde molto piu nitida
    ("bolla/modelli/r650",  BOLLA16 + ":26", (240, 480, 800, 1030), GAN, 0.55),
    ("bolla/modelli/r800",  BOLLA16 + ":22", (240, 480, 800, 1030), GAN, None),
    # V18: la scheda 1000 parla di grandi eventi e adesso ne mostra uno. Ritaglio
    # fermato sopra la fascia dove gli ospiti diventano riconoscibili, e modello
    # FEDELE perche qui ci sono persone: un generativo ricostruirebbe i volti.
    # 1040 e non 1030: la vecchia 1030 e rimasta nella cache di Cloudflare per
    # trenta giorni con lo stesso indirizzo e contenuto diverso. Cambiare misura
    # cambia l'indirizzo, che e l'unico modo di farla arrivare senza una purga.
    ("bolla/modelli/r1000", "file:_sorgenti/bobo-evento.jpeg", (240, 480, 800, 1040), NET, None),
    ("bolla/modelli/g400",  BOLLA16 + ":56", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/g500",  BOLLA16 + ":51", (240, 480, 800, 1030), GAN, None),
    ("bolla/modelli/suite", BOLLA16 + ":61", (240, 480, 800, 1030), GAN, None),

    # --- fotografie del cliente: il .jpeg E gia l'originale ---
    # bolla/glamping-inverno stava qui, con sorgente _sorgenti/fly1.jpeg. Tolta:
    # quella fascia non mostra piu quella fotografia (sostituita nella passata
    # precedente, adesso si chiama neve-tavola), quindi la voce avrebbe
    # rimesso la fotografia VECCHIA al posto di quella che il sito serve.
    ("home/selezione",         "file:_sorgenti/fly8.jpeg", (480, 960, 1440, 2880), GAN, None),
    ("outdoor/montaggio",      "file:_sorgenti/perg2.jpeg", (480, 960, 1280, 2592), GAN, None),
    ("outdoor/tramonto",       "file:_sorgenti/fly2.jpeg", (480, 960, 1600, 2160), GAN, None),
    # outdoor/rooftop: tolta dal sito su richiesta del titolare.
    # Il sorgente resta in _sorgenti/fly4.jpeg; per rimetterla servono
    # anche il <figure> in index.html e una griglia che la ospiti.
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


def catalogo_pdf(nome):
    """Il catalogo per nome, preferendo l'originale del cliente al pubblicato.

    Conta quale dei due si apre: quello in assets/pdf e gia passato da
    opt-pdf, cioe da una ricompressione delle immagini, e renderlo di nuovo
    impilerebbe due perdite sulla stessa fotografia. In _sorgenti c'e il file
    come lo ha mandato il cliente.
    """
    for p in (ROOT / "_sorgenti" / f"{nome}.pdf", ROOT / "assets" / "pdf" / f"{nome}.pdf"):
        if p.exists():
            return p
    raise SystemExit(f"catalogo {nome}.pdf non trovato ne in _sorgenti ne in assets/pdf")


def dpi_nativo(p, minimo=72.0, massimo=300.0):
    """I dpi a cui le immagini di questa pagina sono POSATE davvero.

    Si prende il MASSIMO fra i raster della pagina, non la media: rendere piu
    piano del piu fitto butterebbe via dettaglio che nel file c'e.
    """
    misure = []
    for im in p.get_images(full=True):
        xref, larghezza = im[0], im[2]
        for r in p.get_image_rects(xref):
            if r.width >= 20 and r.height >= 20:
                misure.append(larghezza / (r.width / 72.0))
    if not misure:
        return massimo
    return max(minimo, min(massimo, max(misure)))


def originale(spec):
    """Restituisce il raster nativo, senza margini di carta ne testo di pagina."""
    tipo, resto = spec.split(":", 1)
    if tipo == "pdf":
        catalogo, xref = resto.rsplit(":", 1)
        doc = fitz.open(catalogo_pdf(catalogo))
        info = doc.extract_image(int(xref))
        return Image.open(io.BytesIO(info["image"])).convert("RGB")
    if tipo == "pagina":
        # Perche non si usa "pdf:" qui. Il catalogo bolla e capsula e composto
        # da 2.215 raster affiancati: una fotografia a tutta pagina e spezzata
        # in strisce, quindi extract_image restituisce frammenti e mai
        # l'immagine intera. L'unico modo di riaverla e rendere la PAGINA e
        # ritagliare il soggetto.
        catalogo, n, riquadro = resto.split(":", 2)
        doc = fitz.open(catalogo_pdf(catalogo))
        p = doc[int(n) - 1]
        # Si rende al dpi NATIVO della pagina, non a 300. Le fotografie sono
        # posate fra i 111 e i 155 dpi: renderle a 300 non aggiunge un pixel,
        # interpola, e il modello finirebbe a ricostruire sopra
        # l'interpolazione invece che sui pixel veri. Al nativo il modello
        # riceve esattamente cio che c'e nel file, e l'ingrandimento lo fa lui.
        d = dpi_nativo(p)
        pix = p.get_pixmap(matrix=fitz.Matrix(d / 72, d / 72))
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        print(f"  pagina {n} resa a {d:.0f} dpi nativi: {im.width}x{im.height}")
        l, t, r, b = [float(x) for x in riquadro.split(",")]
        return im.crop((round(l * im.width), round(t * im.height),
                        round(r * im.width), round(b * im.height)))
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
    out.mkdir(parents=True, exist_ok=True)
    slug = Path(nome).name
    attuali = sorted(out.glob(f"{slug}-*.jpg"), key=lambda p: Image.open(p).width)
    # "pagina:" porta gia il riquadro dentro la sorgente, quindi l'inquadratura
    # e decisa e non va cercata. E l'unico caso in cui uno slug NUOVO si puo
    # generare: per tutti gli altri serve una misura gia sul sito da cui
    # ricavare il taglio.
    esplicito = spec.startswith("pagina:")
    if not attuali and not esplicito:
        raise SystemExit(f"nessuna immagine attuale per {nome}: non so quale ritaglio tenere")
    riferimento = Image.open(attuali[-1]).convert("RGB") if attuali else None

    orig = originale(spec)
    serviamo = (f"(serviamo {riferimento.width}x{riferimento.height})" if riferimento
                else "(slug nuovo)")
    print(f"  originale {orig.width}x{orig.height}  {serviamo}")

    if modello is None:
        # Su una fotografia con pixel veri il modello non serve e non aiuta: in
        # V16 abbiamo misurato che il generativo LEVIGA il dettaglio fine. Si
        # ingrandisce solo se il gate lo chiede, e in quel caso col fedele.
        grande = orig
        print("  nessun ingrandimento: la sorgente ha gia i pixel che servono")
    else:
        grande = ingrandisci(orig, modello)
        print(f"  ingrandita {grande.width}x{grande.height} con {modello}")

    if corr:
        grande = neutralizza(grande, corr)
    if esplicito:
        crop = grande
        print(f"  ritaglio {crop.width}x{crop.height}, dal riquadro della sorgente")
    else:
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
