"""Misura, pagina per pagina, il rettangolo esatto di un marchio a pie' di pagina.

PERCHE NON BASTA trova_marchi.py. Quello trova un campione uguale a se stesso.
Nel catalogo tagliafuoco lo stesso slogan e' stampato in due misure diverse (203
px a pagina 2, 194 px a pagina 22 alla stessa risoluzione), quindi un campione
solo manca meta' documento e due campioni lasciano comunque fuori una pagina.

PERCHE NON BASTA UNA FASCIA FISSA. Sopra il marchio corre una barra verde piena
che non va toccata, e la barra scende a quote diverse: finisce a y=741 in pagina
7 e molto piu' in alto altrove. Un rettangolo che sta sotto la barra di pagina 7
taglia il marchio delle pagine dove sta piu' in alto; uno che li copre tutti
intacca la barra di pagina 7.

COME. Per ogni pagina, in autonomia:
  1. si cerca la barra: le righe coperte per oltre il 70 per cento da pixel
     saturi, dentro la finestra. La barra attraversa la pagina, il marchio no.
  2. la finestra utile parte sotto l'ultima riga di barra.
  3. il rettangolo e' il bounding box dei pixel saturi rimasti.
La didascalia verticale del margine destro e' grigia, quindi non e' satura e
resta fuori da sola; in piu' si puo' tagliare la finestra con --dx.

    python tools/misura_marchio.py <pdf> --finestra=x0,y0,x1,y1 [--dx=566]
    python tools/misura_marchio.py <pdf> --finestra=... --json > rects.json

Il rettangolo esce con un margine di sicurezza, e le pagine senza marchio sono
elencate a parte: una pagina saltata in silenzio e' il modo in cui questo lavoro
fallisce senza accorgersene.
"""
import json
import sys

import fitz
import numpy as np

Z = 4.0                     # risoluzione di misura, 4x = 288 dpi
SAT_MIN = 60                # sotto questa saturazione e' grigio o nero: non e' il marchio
COPERTURA_BARRA = 0.70


def misura(pdf, finestra, dx=None, margine=2.0, sat_min=SAT_MIN):
    doc = fitz.open(pdf)
    x0, y0, x1, y1 = finestra
    trovati, vuote = {}, []

    for pno, page in enumerate(doc, start=1):
        pix = page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1), matrix=fitz.Matrix(Z, Z))
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).astype(int)
        mx, mn = a.max(axis=2), a.min(axis=2)
        m = ((mx - mn) > sat_min) & (mx > 40)

        if dx is not None:
            m[:, int((dx - x0) * Z):] = False

        # 1-2. sotto l'ultima barra piena
        piene = np.where(m.sum(axis=1) > m.shape[1] * COPERTURA_BARRA)[0]
        inizio = int(piene.max()) + 1 if len(piene) else 0
        m[:inizio, :] = False

        ys, xs = np.where(m)
        if len(xs) == 0:
            vuote.append(pno)
            continue
        trovati[pno] = [round(x0 + xs.min() / Z - margine, 1),
                        round(y0 + ys.min() / Z - margine, 1),
                        round(x0 + xs.max() / Z + margine, 1),
                        round(y0 + ys.max() / Z + margine, 1)]
    return trovati, vuote


def per_colore(pdf, colori, tolleranza=26, margine=2.0, finestra=None, min_px=200):
    """Rettangolo dei pixel vicini a uno dei colori dati, pagina per pagina.

    Serve quando il marchio sta sopra una fotografia: li la correlazione col
    campione crolla, perche a cambiare non e il marchio ma tutto cio che gli sta
    dietro. I colori piatti di un logo invece non cambiano. Nel catalogo REI il
    marchio del fornitore e esattamente rosso (226,29,35) e verde (0,151,70),
    campionati dall unica occorrenza trovata a mano: cercarli e sufficiente.

    min_px evita di scambiare per marchio qualche pixel sparso della stessa
    tinta dentro una foto.
    """
    doc = fitz.open(pdf)
    trovati, vuote = {}, []
    col = np.array(colori, dtype=int)

    for pno, page in enumerate(doc, start=1):
        clip = fitz.Rect(*finestra) if finestra else page.rect
        pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(Z, Z))
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).astype(int)
        m = np.zeros(a.shape[:2], dtype=bool)
        for c in col:
            m |= (np.abs(a - c).max(axis=2) <= tolleranza)
        if m.sum() < min_px:
            vuote.append(pno)
            continue
        ys, xs = np.where(m)
        trovati[pno] = [round(clip.x0 + xs.min() / Z - margine, 1),
                        round(clip.y0 + ys.min() / Z - margine, 1),
                        round(clip.x0 + xs.max() / Z + margine, 1),
                        round(clip.y0 + ys.max() / Z + margine, 1)]
    return trovati, vuote


def per_logo(pdf, colori, larghezza, altezza, tolleranza=30, margine=3.0,
             min_px=(2000, 500), chiusura=(9, 61)):
    """Il metodo buono: colori del marchio, chiusura morfologica, filtro di taglia.

    per_colore() prende il bounding box di TUTTI i pixel di quel colore, quindi
    su una pagina dove lo stesso rosso compare in una fiamma fotografata
    restituisce mezza pagina. Qui invece:

      1. maschera dei pixel vicini ai colori del marchio;
      2. chiusura morfologica larga, che salda le lettere in un blocco unico
         (il primo tentativo usava un elemento 5x9 px, cioe 1,2 x 2,2 pt: non
         univa niente e trovava zero marchi su sei pagine);
      3. si tengono i blocchi della taglia giusta che contengono ABBASTANZA
         pixel di ogni colore del marchio. La fiamma ha il rosso ma non il
         verde, e cade da sola.

    larghezza e altezza sono intervalli (min, max) in punti, misurati su
    un'occorrenza certa.
    """
    from scipy import ndimage

    doc = fitz.open(pdf)
    cols = [np.array(c, dtype=int) for c in colori]
    trovati, vuote = {}, []

    for pno, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(Z, Z))
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).astype(int)
        maschere = [np.abs(a - c).max(axis=2) <= tolleranza for c in cols]
        unione = np.logical_or.reduce(maschere)
        lab, n = ndimage.label(ndimage.binary_closing(unione, np.ones(chiusura, bool)))

        colpi = []
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            w, h = (xs.max() - xs.min()) / Z, (ys.max() - ys.min()) / Z
            if not (larghezza[0] < w < larghezza[1] and altezza[0] < h < altezza[1]):
                continue
            sel = lab == i
            if any(m[sel].sum() < soglia for m, soglia in zip(maschere, min_px)):
                continue
            colpi.append([round(xs.min() / Z - margine, 1), round(ys.min() / Z - margine, 1),
                          round(xs.max() / Z + margine, 1), round(ys.max() / Z + margine, 1)])
        if colpi:
            trovati[pno] = colpi
        else:
            vuote.append(pno)
    return trovati, vuote


def main():
    pdf = sys.argv[1]
    fin = next((tuple(float(v) for v in a.split("=")[1].split(",")) for a in sys.argv
                if a.startswith("--finestra=")), None)
    dx = next((float(a.split("=")[1]) for a in sys.argv if a.startswith("--dx=")), None)
    marg = next((float(a.split("=")[1]) for a in sys.argv if a.startswith("--margine=")), 2.0)
    sat = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--sat=")), SAT_MIN)

    colori = next((a.split("=")[1] for a in sys.argv if a.startswith("--colori=")), None)
    if colori:
        terne = [tuple(int(v) for v in t.split(",")) for t in colori.split(";")]
        toll = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--toll=")), 26)
        minpx = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--minpx=")), 200)
        trovati, vuote = per_colore(pdf, terne, toll, marg, fin, minpx)
    else:
        trovati, vuote = misura(pdf, fin, dx, marg, sat)

    if "--json" in sys.argv:
        print(json.dumps({"patches": [{"page": p, "rect": r, "bg": [1, 1, 1], "logo": None}
                                      for p, r in sorted(trovati.items())]}, indent=2))
        return

    print("  %s: marchio misurato su %d pagine" % (pdf, len(trovati)))
    for p, r in sorted(trovati.items()):
        print("     p%-3d %-34s %3.0f x %2.0f pt" % (p, r, r[2] - r[0], r[3] - r[1]))
    if vuote:
        print("  nessun pixel saturo nella finestra: pagine %s" % vuote)


if __name__ == "__main__":
    main()
