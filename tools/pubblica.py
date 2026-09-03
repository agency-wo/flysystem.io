"""Costruisce la cartella da pubblicare con una LISTA DI COSE AMMESSE.

Perche non basta `.assetsignore`. Su Cloudflare **Pages** quel file non viene
mai letto: e una funzione dei Workers static assets. Il percorso di upload di
Pages filtra contro una lista fissa dentro wrangler,

    ["_worker.js", "_redirects", "_headers", "_routes.json", "functions",
     "**/.DS_Store", "**/node_modules", "**/.git", ".wrangler"]

e nient'altro. Quindi `wrangler pages deploy .` da questa cartella pubblicherebbe
`_sorgenti/` (le fotografie originali del cliente, e i PDF che portano nel nome
le due societa del gruppo che non vanno mai nominate), `tools/`, `README.md`.

Oggi sembra che vada bene solo per un incidente fortunato: il deploy si
fermerebbe sul limite di 25 MiB per file, superato da un PDF in `_sorgenti/` e
dai modelli in `tools/bin/`. Ma quei due percorsi sono in `.gitignore`: su un
clone pulito non esistono, nessun limite scatta, e il deploy riesce pubblicando
`tools/` e `README.md` senza un solo avviso.

Una lista di esclusioni sbaglia in modo silenzioso e pericoloso: dimentichi una
riga e pubblichi. Una lista di cose ammesse sbaglia in modo rumoroso e
innocuo: dimentichi una riga e manca una pagina, che si vede subito.

    python tools/pubblica.py           # costruisce _dist/ e dice cosa contiene
    python tools/pubblica.py --deploy  # costruisce e pubblica
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / "_dist"

# Tutto e solo cio che deve stare online. Niente jolly su cartelle di lavoro.
PAGINE = ["index.html", "bolla.html", "cataloghi.html", "contatti.html",
          "privacy.html", "404.html"]
FILE = ["robots.txt", "sitemap.xml", "_headers", "_redirects", ".nojekyll"]
CARTELLE = ["assets"]

# Se uno di questi finisse in _dist, la pubblicazione va fermata.
MAI = ["_sorgenti", "tools", "README.md", "package.json", "package-lock.json",
       ".git", ".gitignore", ".wrangler", ".assetsignore", "_dist"]

LIMITE = 25 * 1024 * 1024  # Cloudflare Pages rifiuta i file oltre i 25 MiB


def costruisci():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    mancanti = []
    for nome in PAGINE + FILE:
        src = ROOT / nome
        if not src.exists():
            mancanti.append(nome)
            continue
        shutil.copy2(src, DIST / nome)
    for nome in CARTELLE:
        src = ROOT / nome
        if not src.exists():
            mancanti.append(nome + "/")
            continue
        shutil.copytree(src, DIST / nome)
    return mancanti


def controlla():
    """Nessun file vietato, nessun file oltre il limite di Pages."""
    guai = []
    for vietato in MAI:
        p = DIST / vietato
        if p.exists():
            guai.append(f"in _dist c'e {vietato}, che non deve mai essere pubblicato")
    for p in DIST.rglob("*"):
        if p.is_file() and p.stat().st_size > LIMITE:
            mb = p.stat().st_size / 1024 / 1024
            guai.append(f"{p.relative_to(DIST)} pesa {mb:.1f} MB, oltre il limite di 25 MiB di Pages")
    return guai


def main():
    mancanti = costruisci()
    guai = controlla()

    file = [p for p in DIST.rglob("*") if p.is_file()]
    peso = sum(p.stat().st_size for p in file)
    print(f"  _dist: {len(file)} file, {peso / 1048576:.0f} MB")
    for nome in sorted(os.listdir(DIST)):
        print(f"    {nome}")

    if mancanti:
        print("\n  MANCANO, e la lista di cose ammesse se ne accorge subito:")
        for m in mancanti:
            print(f"    {m}")
    if guai:
        print("\n  PUBBLICAZIONE FERMATA:")
        for g in guai:
            print(f"    {g}")
        sys.exit(1)
    if mancanti:
        sys.exit(1)

    print("\n  nessun file vietato, nessun file oltre i 25 MiB")

    if "--deploy" in sys.argv:
        print("\n  pubblico...")
        subprocess.run(["npx", "wrangler", "pages", "deploy", str(DIST),
                        "--project-name", "flysystem", "--branch", "main"],
                       check=True, shell=True)
        print("\n  Verificare adesso che questi rispondano 404 sul sito:")
        for p in ("_sorgenti/bobo.jpeg", "tools/enhance.py", "README.md"):
            print(f"    https://flysystem.io/{p}")


if __name__ == "__main__":
    main()
