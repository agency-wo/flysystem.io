"""Controlla che ogni didascalia parli della fotografia che accompagna.

Nasce da un difetto trovato dal cliente: la fascia fotografica della home
mostrava una pergola vista dall'alto a bordo piscina, e sotto c'era scritto
"Vetrata panoramica, terrazza al tramonto". La didascalia era rimasta da
quando quella fascia conteneva un'altra immagine; sostituita la fotografia,
nessuno aveva aggiornato il testo.

Il controllo e volutamente grossolano: confronta le parole di contenuto della
didascalia con quelle dell'attributo alt della stessa figura e segnala solo
quando NON hanno nemmeno una parola in comune. Un testo puo legittimamente
essere piu sintetico dell'alt, ma se non condivide una sola parola quasi
sempre e rimasto indietro.

    python tools/didascalie.py
"""
import glob
import re
import sys
import unicodedata

VUOTE = {
    "con", "una", "uno", "un", "del", "della", "dei", "delle", "dal", "dalla",
    "in", "su", "sul", "sulla", "per", "che", "di", "da", "il", "lo", "la",
    "le", "gli", "gia", "al", "alla", "ai", "alle", "and", "the", "e", "a",
    "gres", "gia", "gliene",
}

RX_FIG = re.compile(r"<figure[^>]*>(.*?)</figure>", re.S)
RX_CAP = re.compile(r"<figcaption[^>]*>(.*?)</figcaption>", re.S)
RX_IMG = re.compile(r'<img[^>]*alt="([^"]*)"', re.S)
RX_SRC = re.compile(r'<img[^>]*src="([^"]+)"')


def parole(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return {w for w in re.findall(r"[a-zA-Z]{3,}", t.lower()) if w not in VUOTE}


def main():
    guai = 0
    controllate = 0
    for f in sorted(glob.glob("*.html")):
        for blocco in RX_FIG.findall(open(f, encoding="utf-8").read()):
            cap = RX_CAP.search(blocco)
            alt = RX_IMG.search(blocco)
            if not (cap and alt and alt.group(1).strip()):
                continue
            controllate += 1
            pc, pa = parole(cap.group(1)), parole(alt.group(1))
            if pc & pa:
                continue
            guai += 1
            src = RX_SRC.search(blocco)
            print(f"  SCOLLEGATA  {f}  {src.group(1).split('/')[-1] if src else '?'}")
            print(f"      alt: {re.sub(r'<[^>]+>', '', alt.group(1)).strip()[:90]}")
            print(f"      did: {re.sub(r'<[^>]+>', '', cap.group(1)).strip()[:90]}")
    print(f"\n  didascalie controllate: {controllate}")
    print(f"  senza una parola in comune con la foto: {guai}")
    sys.exit(1 if guai else 0)


if __name__ == "__main__":
    main()
