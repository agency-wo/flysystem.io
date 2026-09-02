# -*- coding: utf-8 -*-
"""Alleggerisce i cataloghi PDF ricomprimendo le immagini.

Nasce da un limite vero: Cloudflare Pages rifiuta i file oltre i 25 MiB, e tre
cataloghi stavano fra i 34,8 e i 36 MB. Il deploy si fermava li'.

Perche' le immagini e non altro: misurato, sono fra il 48% e il 100% del peso di
questi file. Su `fly-system-porte-tagliafuoco.pdf` sono il 100%, perche' il PDF
non ha alcuno strato di testo - e' una scansione. Comprimere altro non avrebbe
spostato niente.

DUE COSE CHE QUESTO SCRIPT NON FA, E IL PERCHE'.

`subset_fonts()` non viene chiamata. Su un altro progetto ha corrotto la
spaziatura fra le parole in grassetto ("design essenziale" -> "designessenziale")
e il controllo automatico sulla lunghezza del testo **non se n'era accorto**:
la lunghezza era identica, mancavano solo gli spazi. Se ne e' accorto solo un
occhio che guardava la pagina resa. Da allora: niente subset, e verifica visiva.

Non ottimizza in blocco tutti i PDF della cartella. Tocca solo quelli che
superano il limite, perche' ricomprimere un catalogo che gia' passa e' rischio
senza guadagno.

    python tools/opt-pdf.py                 # elenca cosa supera il limite
    python tools/opt-pdf.py --applica       # riscrive quelli che lo superano
"""
import os
import shutil
import sys
from pathlib import Path

import fitz

RADICE = Path(__file__).resolve().parent.parent
CARTELLA = RADICE / "assets" / "pdf"

# Cloudflare Pages rifiuta oltre i 25 MiB. Si punta piu' in basso perche' un file
# che passa per un pelo tornerebbe a bloccare il deploy al primo aggiornamento.
LIMITE = 25 * 1024 * 1024
OBIETTIVO = 23 * 1024 * 1024   # un margine sotto il limite, non il limite stesso

# Una scala, non un valore solo: quanto si guadagna dipende da quanta parte del
# peso sono immagini, e varia molto. Su porte-tagliafuoco sono il 100% e il primo
# gradino basta (35,2 -> 9,4 MB); su vetrate-panoramiche sono il 48% e il primo
# gradino si fermava a 28,6 MB, ancora sopra il limite. Si scende di un gradino
# solo se serve, cosi' nessun file viene compresso piu' del necessario.
#
# Tarati confrontando le pagine rese a 110 dpi. Primo gradino: differenza media
# 2,94 su 255. Terzo gradino, sul file che ne aveva bisogno: 0,25 su una pagina
# tecnica e 2,89 su una fotografica. Le tabelle di quote e i codici RAL restano
# leggibili, ed e' li' che una compressione troppo forte si vedrebbe per prima.
SCALA = [(200, 150, 80), (170, 120, 75), (130, 100, 70)]


def mb(n):
    return n / 1048576


def candidati():
    return sorted((p for p in CARTELLA.glob("*.pdf") if p.stat().st_size > LIMITE),
                  key=lambda p: -p.stat().st_size)


def ottimizza(percorso):
    prima = percorso.stat().st_size
    d = fitz.open(percorso)
    pagine_prima, testo_prima = d.page_count, sum(len(p.get_text()) for p in d)

    d.close()

    tmp = percorso.with_suffix(".pdf.tmp")
    for soglia, target, q in SCALA:
        d = fitz.open(percorso)
        d.rewrite_images(dpi_threshold=soglia, dpi_target=target, quality=q)
        d.save(tmp, garbage=4, deflate=True, clean=True)
        d.close()
        if tmp.stat().st_size <= OBIETTIVO:
            break
    usato = (soglia, target, q)

    v = fitz.open(tmp)
    pagine_dopo, testo_dopo = v.page_count, sum(len(p.get_text()) for p in v)
    v.close()
    dopo = tmp.stat().st_size

    # Le pagine non si perdono, e il testo non si accorcia. Non basta a dire che
    # il PDF e' intatto - vedi il commento in cima - ma un fallimento qui e'
    # certo, e conviene fermarsi prima di sovrascrivere l'originale.
    if pagine_dopo != pagine_prima:
        tmp.unlink()
        raise SystemExit("  %s: pagine %d -> %d, annullato" % (percorso.name, pagine_prima, pagine_dopo))
    if testo_dopo < testo_prima:
        tmp.unlink()
        raise SystemExit("  %s: testo %d -> %d caratteri, annullato" % (percorso.name, testo_prima, testo_dopo))
    if dopo > LIMITE:
        tmp.unlink()
        raise SystemExit("  %s: %.1f MB, ancora sopra il limite" % (percorso.name, mb(dopo)))

    shutil.move(str(tmp), str(percorso))
    return prima, dopo, pagine_dopo, testo_dopo, usato


def main(applica):
    da_fare = candidati()
    if not da_fare:
        print("  nessun PDF sopra i %.0f MiB: niente da fare" % mb(LIMITE))
        return 0

    print("  sopra il limite di %.0f MiB (Cloudflare Pages):" % mb(LIMITE))
    for p in da_fare:
        print("    %6.1f MB  %s" % (mb(p.stat().st_size), p.name))

    if not applica:
        print("\n  esegui con --applica per riscriverli")
        return 0

    print()
    for p in da_fare:
        prima, dopo, pag, testo, usato = ottimizza(p)
        print("  %-44s %5.1f -> %5.1f MB  (%2.0f%% in meno)  pag=%d testo=%d  gradino %d/%d"
              % (p.name, mb(prima), mb(dopo), 100 - 100 * dopo / prima, pag, testo,
                 SCALA.index(usato) + 1, len(SCALA)))

    resta = candidati()
    print("\n  ancora sopra il limite: %s" % ([p.name for p in resta] if resta else "nessuno"))
    print("  GUARDA UNA PAGINA DI CIASCUNO prima di pubblicare: i controlli qui")
    print("  sopra non vedono una compressione che rovina le tabelle di quote.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--applica" in sys.argv))
