import re
from pathlib import Path

root = Path(r"C:\Users\aceto\OneDrive\Desktop\web and apps\flysystem.io")
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
        if not (root / u).exists():
            missing.append(f"{f}: {u}")
print("\n".join(missing) if missing else "ALL ASSET REFS OK")
