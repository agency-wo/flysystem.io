"""Trova un marchio dentro un PDF senza testo, e ne stampa i rettangoli in punti.

PERCHE ESISTE. tools/rebrand_pdf.py sa coprire un marchio, ma per sapere DOVE si
affida a page.search_for, che legge il livello di testo. Meta dei cataloghi qui
non ha livello di testo: sono stampati con "Microsoft: Print To PDF" e ogni
pagina e una pila di strisce raster, zero caratteri. Su quei file l'audit
risponde TOTAL HITS: 0 e non significa niente. Guardare 167 pagine a occhio non
e un controllo, e un augurio: questo script le misura.

COME. Correlazione incrociata normalizzata (NCC) fra un ritaglio campione del
marchio e ogni pagina resa a bassa risoluzione. La NCC e insensibile a
luminosita e contrasto, quindi lo stesso marchio viene trovato sia sul fondo
chiaro sia dentro una fascia colorata. Per ogni pagina si tiene il picco, e si
riporta anche quando e sotto soglia, perche un marchio mancato in silenzio e
esattamente il modo in cui questo lavoro fallisce.

    python tools/trova_marchi.py <pdf> <campione.png> [--soglia 0.7] [--dpi 60]
    python tools/trova_marchi.py <pdf> <campione.png> --json > patch.json

L'uscita --json e gia nella forma dei "patches" di rebrand_pdf.py, con il rect
allargato di un margine e il logo lasciato a null: si sceglie a mano navy o
white e si aggiusta, non si applica alla cieca.
"""
import json
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def grigio(im):
    return np.asarray(im.convert("L"), dtype=np.float64)


def ncc(pagina, campione):
    """Mappa di correlazione normalizzata fra pagina e campione.

    Restituisce la matrice dei punteggi, non solo il picco: una pagina puo
    portare il marchio due volte, e tenere solo il massimo ne perderebbe uno.

    Il numeratore si calcola con una convoluzione FFT invece che con due cicli
    annidati sui pixel del campione. La versione a cicli era corretta e
    inutilizzabile: 3 minuti e 43 per un catalogo di 29 pagine, cioe mezz'ora
    per i sette documenti, ripetuta a ogni ritocco di soglia. Con la FFT lo
    stesso lavoro sta in pochi secondi e il risultato e identico.
    """
    from scipy.signal import fftconvolve

    ph, pw = pagina.shape
    th, tw = campione.shape
    if th > ph or tw > pw:
        return None

    c = campione - campione.mean()
    cn = np.sqrt((c * c).sum())
    if cn == 0:
        return None

    # numeratore: correlazione = convoluzione col campione ribaltato
    num = fftconvolve(pagina, c[::-1, ::-1], mode="valid")

    # denominatore: deviazione standard di ogni finestra, dalle somme cumulative
    integ = np.pad(np.cumsum(np.cumsum(pagina, 0), 1), ((1, 0), (1, 0)))
    integ2 = np.pad(np.cumsum(np.cumsum(pagina * pagina, 0), 1), ((1, 0), (1, 0)))

    def finestra(I):
        return I[th:, tw:] - I[:-th, tw:] - I[th:, :-tw] + I[:-th, :-tw]

    n = th * tw
    somma = finestra(integ)
    varianza = finestra(integ2) - somma * somma / n
    varianza[varianza < 1e-9] = 1e-9
    return num / (np.sqrt(varianza) * cn)


def picchi(mappa, soglia, th, tw):
    """Ogni massimo locale sopra soglia, con soppressione dei doppioni vicini."""
    fuori = []
    m = mappa.copy()
    for _ in range(6):
        idx = int(np.argmax(m))
        y, x = divmod(idx, m.shape[1])
        s = float(m[y, x])
        if s < soglia:
            break
        fuori.append((s, x, y))
        y0, y1 = max(0, y - th // 2), min(m.shape[0], y + th // 2)
        x0, x1 = max(0, x - tw // 2), min(m.shape[1], x + tw // 2)
        m[y0:y1, x0:x1] = -1e9
    return fuori


def cerca(pdf, campione_png, soglia, dpi, margine):
    doc = fitz.open(pdf)
    camp = grigio(Image.open(campione_png))
    th, tw = camp.shape
    scala = 72.0 / dpi
    trovati, mancati = [], []

    for pno, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        mappa = ncc(grigio(im), camp)
        if mappa is None:
            mancati.append({"page": pno, "punteggio": -1.0, "rect": None})
            continue
        colpi = picchi(mappa, soglia, th, tw)
        if colpi:
            for s, x, y in colpi:
                trovati.append({"page": pno, "punteggio": round(s, 3), "rect": [
                    round((x - margine) * scala, 1), round((y - margine) * scala, 1),
                    round((x + tw + margine) * scala, 1), round((y + th + margine) * scala, 1)]})
        else:
            mancati.append({"page": pno, "punteggio": round(float(mappa.max()), 3), "rect": None})

    return trovati, mancati, doc.page_count


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    pdf, campione = Path(sys.argv[1]), Path(sys.argv[2])
    soglia = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--soglia=")), 0.70))
    dpi = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--dpi=")), 60))
    margine = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--margine=")), 2))
    come_json = "--json" in sys.argv

    trovati, mancati, totale = cerca(pdf, campione, soglia, dpi, margine)

    if come_json:
        print(json.dumps({"patches": [{"page": t["page"], "rect": t["rect"],
                                       "bg": None, "logo": None}
                                      for t in trovati]}, indent=2))
        return

    print(f"  {pdf.name}  ({totale} pagine, campione {campione.name}, dpi {dpi})")
    print(f"  trovati sopra {soglia}: {len(trovati)}")
    for t in trovati:
        print("     p%-3d %.3f  rect %s" % (t["page"], t["punteggio"], t["rect"]))
    if mancati:
        print(f"  sotto soglia: {len(mancati)}  (da guardare a mano, non da ignorare)")
        for m in sorted(mancati, key=lambda r: -r["punteggio"])[:12]:
            print("     p%-3d %.3f" % (m["page"], m["punteggio"]))


if __name__ == "__main__":
    main()
