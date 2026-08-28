import re
from pathlib import Path

# Ricavata dalla posizione dello script: un percorso assoluto scritto a mano
# smette di funzionare appena il repo cambia cartella o macchina.
root = Path(__file__).resolve().parent.parent
missing = []
for f in ["index.html", "bolla.html", "cataloghi.html", "contatti.html", "404.html"]:
    html = (root / f).read_text(encoding="utf-8")
    urls = set()
    for m in re.finditer(r'(?:src|href|poster)="(assets/[^"]+)"', html):
        urls.add(m.group(1))
    for m in re.finditer(r'(?:srcset|imagesrcset)="([^"]+)"', html):
        for cand in m.group(1).split(","):
            u = cand.strip().split(" ")[0]
            if u.startswith("assets/"):
                urls.add(u)
    for u in sorted(urls):
        # La stringa di query non fa parte del nome del file: da quando
        # versiona.py appende ?v=<impronta> a style.css e main.js, cercarli
        # con la query attaccata li dava per mancanti a ogni esecuzione.
        if not (root / u.split("?")[0]).exists():
            missing.append(f"{f}: {u}")
print("\n".join(missing) if missing else "ALL ASSET REFS OK")
