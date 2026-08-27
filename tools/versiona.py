# -*- coding: utf-8 -*-
"""Attacca l'impronta del contenuto a style.css e main.js nelle pagine.

Nasce dal 27 agosto 2026. Il foglio di stile era stato pubblicato correttamente
e nessun visitatore lo vedeva: `style.css` viaggia con
`Cache-Control: max-age=14400`, cioe 4 ore, e Cloudflare teneva la copia
precedente. Peggio, il controllo che avevo fatto diceva che era tutto a posto,
perche interrogava `style.css?x=1`: la stringa di query e una chiave di cache
diversa, quindi quella richiesta andava all'origine mentre il browser, che
chiede l'indirizzo nudo, continuava a ricevere la copia vecchia.

Il rimedio non e accorciare la cache, che vorrebbe dire rinunciare a una cosa
buona per paura di un effetto collaterale. E cambiare indirizzo quando cambia
il contenuto:

    assets/css/style.css?v=6f3a1c22

Contenuto nuovo, impronta nuova, indirizzo nuovo, quindi la cache lunga smette
di essere una trappola e torna a essere un vantaggio. L'impronta sono le prime
8 cifre dello sha1 del file: cambia se e solo se cambia il contenuto, per cui
ripubblicare senza modifiche non invalida niente.

I FONT NON SI VERSIONANO, di proposito. Sono citati due volte, dal
`<link rel="preload">` nelle pagine e da `@font-face` dentro la CSS, e mettere
l'impronta solo sul primo dei due farebbe scaricare a ogni visitatore lo stesso
font due volte, una per indirizzo. Sono anche gli unici file qui che non
cambiano mai.

Nemmeno le immagini, per ora: le srcset sono lunghissime e le fotografie qui si
sostituiscono cambiando nome. Se un giorno si rimpiazza una foto tenendo lo
stesso nome, quella restera vecchia in cache per 4 ore, e allora questo script
va esteso.

    python tools/versiona.py            riscrive le pagine
    python tools/versiona.py --check    esce con 1 se un'impronta e vecchia
    python tools/versiona.py --hook     installa il pre-commit che fa il check
"""
import glob
import hashlib
import io
import os
import re
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Solo i file che cambiano spesso e che esistono in copia unica. Aggiungerne
# uno qui basta: la riscrittura e generica sull'attributo che lo cita.
ASSETS = ("assets/css/style.css", "assets/js/main.js")


def impronta(percorso):
    """Le prime 8 cifre dello sha1 del contenuto."""
    with io.open(os.path.join(RADICE, percorso), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def pagine():
    return sorted(glob.glob(os.path.join(RADICE, "*.html")))


def riscrivi(testo, asset, imp):
    r"""Sostituisce l'indirizzo dell'asset, con o senza impronta precedente.

    Il gruppo `(?:\?v=[0-9a-f]{8})?` e quello che rende lo script ripetibile:
    senza, la seconda esecuzione appenderebbe una seconda impronta alla prima.
    """
    schema = re.compile(r'(href|src)="' + re.escape(asset) + r'(?:\?v=[0-9a-f]{8})?"')
    return schema.subn(lambda m: '%s="%s?v=%s"' % (m.group(1), asset, imp), testo)


def main(argv):
    check = "--check" in argv
    if "--hook" in argv:
        return installa_hook()

    imps = {a: impronta(a) for a in ASSETS}
    vecchie, toccate = [], 0
    for p in pagine():
        testo = io.open(p, encoding="utf-8").read()
        nuovo = testo
        for a in ASSETS:
            nuovo, n = riscrivi(nuovo, a, imps[a])
            if not n:
                print("  %-16s non cita %s" % (os.path.basename(p), a))
        if nuovo != testo:
            vecchie.append(os.path.basename(p))
            if not check:
                io.open(p, "w", encoding="utf-8", newline="\n").write(nuovo)
                toccate += 1

    for a in ASSETS:
        print("  %-22s %s" % (a, imps[a]))
    if check:
        if vecchie:
            print("\n  IMPRONTA VECCHIA in: %s" % ", ".join(vecchie))
            print("  I visitatori riceverebbero la versione in cache. "
                  "Esegui: python tools/versiona.py")
            return 1
        print("\n  tutte le pagine sono aggiornate")
        return 0
    print("\n  %d pagina/e riscritta/e" % toccate)
    return 0


def installa_hook():
    """Un pre-commit che rifiuta un commit con le impronte vecchie.

    Blocca invece di correggere da solo: un hook che modifica i file sotto le
    mani di chi committa e peggio del problema che risolve.
    """
    d = os.path.join(RADICE, ".git", "hooks")
    if not os.path.isdir(d):
        print("  niente .git/hooks qui")
        return 1
    p = os.path.join(d, "pre-commit")
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        "#!/bin/sh\n"
        "# installato da tools/versiona.py\n"
        "python tools/versiona.py --check || exit 1\n")
    os.chmod(p, 0o755)
    print("  installato %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
