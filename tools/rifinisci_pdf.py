"""Rifiniture su un PDF gia' rimarchiato: metadati e verso di lettura.

DUE COSE CHE rebrand_pdf.py NON FA, e che nessun altro script qui fa.

METADATI. Il nome del fornitore non sta solo sulle pagine: sta nel campo title
del file. Si legge nelle proprieta' del documento e nella scheda del browser
quando il PDF si apre in linea. I due cataloghi arrivati il 3 settembre 2026
portavano "Catalogo Vertaglia Porte (1).pdf" e "FLY-FINALE-SENZA-COPPIA.pdf".
L'audit di rebrand_pdf.py non guarda i metadati, quindi rispondeva zero.

VERSO DI LETTURA. Il catalogo del fornitore ha le pagine coricate: il testo si
legge dal basso verso l'alto. Non e' il flag /Rotate, che vale 0 su tutte: la
rotazione e' dentro le immagini. Impostare /Rotate non tocca un pixel e dice al
lettore come mostrare la pagina, quindi si sistema senza ricomprimere niente.
Gli altri cataloghi pubblicati si leggono dritti: questo si allinea a loro.

    python tools/rifinisci_pdf.py <in.pdf> <out.pdf> --titolo="..." [--ruota=90]
"""
import sys
from pathlib import Path

import fitz


def rifinisci(sorgente, destinazione, titolo, ruota=None, autore="Fly System Srls"):
    doc = fitz.open(sorgente)

    prima = dict(doc.metadata or {})
    doc.set_metadata({
        "title": titolo,
        "author": autore,
        "subject": titolo,
        "keywords": "",
        "creator": autore,
        "producer": autore,
    })

    if ruota is not None:
        for page in doc:
            page.set_rotation(ruota)

    doc.save(str(destinazione), garbage=3, deflate=True)
    return prima, doc.metadata


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    titolo = next(a.split("=", 1)[1] for a in sys.argv if a.startswith("--titolo="))
    ruota = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--ruota=")), None)

    prima, dopo = rifinisci(src, dst, titolo, ruota)
    print("  %s -> %s" % (src.name, dst.name))
    print("     title prima: %r" % prima.get("title"))
    print("     title dopo:  %r" % dopo.get("title"))
    print("     producer prima: %r" % prima.get("producer"))
    if ruota is not None:
        print("     /Rotate impostato a %d su tutte le pagine" % ruota)


if __name__ == "__main__":
    main()
