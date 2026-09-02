# -*- coding: utf-8 -*-
"""Sposta il sito da un indirizzo di base a un altro, in un colpo solo.

Il sito nasce servito da `minarankstudio.com/flysystem.io/`, che e' il dominio
di minarank soltanto perche' il repository sta nell'organizzazione GitHub
`agency-wo`, il cui sito Pages porta `CNAME = minarankstudio.com`: ogni repo di
quella organizzazione finisce sotto quel dominio in automatico. Il progetto pero'
e' di MarketingPro, e prima o poi va servito da li'; piu' avanti ancora dal
dominio del cliente.

L'indirizzo di base compare in canonical, og:url, og:image, in ogni URL assoluto
dei dati strutturati, nella sitemap e dentro robots.txt: oggi 70 volte su 6 file,
tutte identiche. Farlo a mano significa quasi certamente dimenticarne una, e una
canonical rimasta indietro e' peggio di nessuna canonical, perche' indica a
Google una pagina diversa da quella che sta leggendo.

Da qui la regola di questo script: **o cambia tutto, o non cambia niente**. Alla
fine ricontrolla, e se resta anche una sola occorrenza del vecchio indirizzo
esce con errore invece di lasciare il sito a meta'.

L'indirizzo di partenza non e' scritto qui dentro: viene letto dalla canonical
di `index.html`. Cosi' non puo' invecchiare, e dopo il primo spostamento lo
script continua a funzionare senza modifiche.

    python tools/rebase.py https://flysystem.marketingpro-agency.com/
    python tools/rebase.py --check      esce con 1 se i file non concordano

Dopo lo spostamento va rieseguito `python tools/verify.py`, che e' il controllo
che accorge se la sitemap e le canonical hanno smesso di raccontare la stessa
cosa.
"""
import io
import os
import re
import subprocess
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# I file che citano l'indirizzo assoluto. Le pagine lo fanno in canonical, og e
# JSON-LD; la sitemap in ogni <loc>; robots.txt nella riga Sitemap.
def bersagli():
    nomi = sorted(f for f in os.listdir(RADICE) if f.endswith(".html"))
    for extra in ("sitemap.xml", "robots.txt"):
        if os.path.exists(os.path.join(RADICE, extra)):
            nomi.append(extra)
    return nomi


def leggi(nome):
    with io.open(os.path.join(RADICE, nome), encoding="utf-8") as f:
        return f.read()


def scrivi(nome, testo):
    with io.open(os.path.join(RADICE, nome), "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)


CANONICAL = re.compile(r'<link rel="canonical" href="(https?://[^"]+?)/?"')


def base_corrente():
    """L'indirizzo di base secondo index.html, con lo slash finale.

    La canonical della home *e'* la base, quindi non c'e' niente da comporre e
    niente che possa divergere da cio' che il sito dichiara di essere.
    """
    m = CANONICAL.search(leggi("index.html"))
    if not m:
        raise SystemExit("  index.html non ha una canonical: non so da dove partire")
    return m.group(1) + "/"


def occorrenze(base):
    return {n: leggi(n).count(base) for n in bersagli()}


def basi_dichiarate():
    """Le basi ricavate dalle canonical di tutte le pagine.

    La canonical di una pagina e' l'indirizzo *della pagina*, non la base: solo
    per la home le due cose coincidono. Per le altre la base e' la canonical
    meno il proprio nome di file. Se ne esce piu' di una, qualcuno ha spostato
    una pagina sola, ed e' esattamente il guasto che --check deve vedere.

    404.html non ha canonical (e' noindex) e viene semplicemente saltata.
    """
    trovate = {}
    for n in bersagli():
        if not n.endswith(".html"):
            continue
        m = CANONICAL.search(leggi(n))
        if not m:
            continue
        url = m.group(1) + "/"
        # La canonical di una sottopagina non porta l'estensione (Cloudflare
        # Pages risponde 308 da /bolla.html a /bolla, quindi l'indirizzo che
        # vale e' il secondo). Si toglie quindi il nome SENZA .html; il ramo
        # con l'estensione resta per compatibilita' con com'era prima.
        if n != "index.html":
            senza = n[: -len(".html")]
            if url.endswith("/" + n + "/"):
                url = url[: -len(n + "/")]
            elif url.endswith("/" + senza + "/"):
                url = url[: -len(senza + "/")]
        trovate.setdefault(url, []).append(n)
    return trovate


def normalizza(url):
    if not re.match(r"^https?://", url):
        raise SystemExit("  l'indirizzo deve iniziare con http:// o https:// : " + url)
    return url if url.endswith("/") else url + "/"


def versiona():
    """Ristampa le impronte. Non cambiano (CSS e JS non sono toccati), ma cosi'
    il pre-commit resta verde anche se qualcuno lancia i due script al contrario."""
    s = os.path.join(RADICE, "tools", "versiona.py")
    if os.path.exists(s):
        subprocess.call([sys.executable, s], cwd=RADICE)


def controlla():
    basi = basi_dichiarate()
    for b, pagine in sorted(basi.items()):
        print("  %-45s %s" % (b, ", ".join(pagine)))
    if len(basi) > 1:
        print("\n  LE PAGINE NON CONCORDANO: %d basi diverse." % len(basi))
        print("  Una canonical rimasta indietro manda Google sulla pagina sbagliata.")
        return 1
    base = next(iter(basi))
    # Devono citare la base solo i file che hanno motivo di farlo: le pagine
    # indicizzabili (quelle con una canonical), la sitemap e robots.txt.
    # 404.html non ne ha: e' noindex e senza canonical, di proposito.
    dovuti = set(sum(basi.values(), [])) | {
        n for n in bersagli() if n in ("sitemap.xml", "robots.txt")}
    conteggi = occorrenze(base)
    manca = sorted(n for n in dovuti if not conteggi.get(n))
    if manca:
        print("\n  NON CITANO LA BASE: %s" % ", ".join(manca))
        return 1
    print("\n  una sola base, %d occorrenze, tutti i file concordano"
          % sum(occorrenze(base).values()))
    return 0


def sposta(nuova):
    vecchia = base_corrente()
    if vecchia == nuova:
        print("  la base e' gia' %s: niente da fare" % nuova)
        return 0

    prima = occorrenze(vecchia)
    totale = sum(prima.values())
    if not totale:
        raise SystemExit("  nessuna occorrenza di %s: mi fermo" % vecchia)

    print("  da  %s" % vecchia)
    print("  a   %s\n" % nuova)
    for nome, n in prima.items():
        if n:
            scrivi(nome, leggi(nome).replace(vecchia, nuova))
        print("  %-16s %d" % (nome, n))

    # Il controllo che rende lo script sicuro: se e' rimasto anche un solo
    # riferimento vecchio, il sito e' a meta' e va detto subito.
    rimasti = {n: c for n, c in occorrenze(vecchia).items() if c}
    if rimasti:
        raise SystemExit("\n  RIMASTI INDIETRO: %s" % rimasti)
    dopo = sum(occorrenze(nuova).values())
    if dopo != totale:
        raise SystemExit("\n  attese %d occorrenze, trovate %d" % (totale, dopo))

    print("\n  %d occorrenze spostate su %d file" % (totale, len([1 for v in prima.values() if v])))
    versiona()
    print("\n  Ora: python tools/verify.py")
    return 0


def main(argv):
    if "--check" in argv:
        return controlla()
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[0])
        print("\n  uso: python tools/rebase.py <nuovo-indirizzo-base>")
        print("       python tools/rebase.py --check")
        return 1
    return sposta(normalizza(argv[0]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
