"""Rigenera le fasce fotografiche a tutta larghezza.

Due problemi risolti qui:
- la fascia Chi siamo era un render con una cucitura verticale visibile, ed era
  il terzo tramonto della stessa pagina: nessuna immagine spiccava piu.
- la fascia Contatti era una foto stock (persona di spalle, cane, stufa) senza
  un solo prodotto Fly System dentro.
Entrambe passano a fotografie reali di installazioni, in piena luce diurna, cosi
sulla home resta un solo tramonto, nel punto in cui rende di piu (apertura Outdoor).

usage: python make_bands.py <sorgenti-dir>
"""
import sys
from pathlib import Path

import pillow_avif  # noqa: F401
from PIL import Image

ROOT = Path(__file__).parent.parent
IMG = ROOT / "assets" / "img"

# slug, sorgente, cartella, ritaglio frazionario (l, t, r, b), larghezze
JOBS = [
    ("selezione", "fly8.jpeg", "home", (0.0, 0.10, 1.0, 0.74), (480, 960, 1040)),
    ("lead", "fly9.jpeg", "contatti", (0.0, 0.16, 1.0, 0.80), (480, 960, 1210)),
]


def main(src: Path):
    for slug, fname, folder, box, widths in JOBS:
        out = IMG / folder
        out.mkdir(parents=True, exist_ok=True)
        im = Image.open(src / fname).convert("RGB")
        l, t, r, b = box
        im = im.crop((round(l * im.width), round(t * im.height),
                      round(r * im.width), round(b * im.height)))
        for w in sorted({min(w, im.width) for w in widths}):
            h = round(im.height * w / im.width)
            rs = im.resize((w, h), Image.LANCZOS)
            rs.save(out / f"{slug}-{w}.avif", quality=62)
            rs.save(out / f"{slug}-{w}.webp", quality=80, method=6)
            rs.save(out / f"{slug}-{w}.jpg", quality=82, optimize=True, progressive=True)
        print(f"  {folder}/{slug}: {im.width}x{im.height}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
