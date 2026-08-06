"""Varianti del logo per l'inserimento nei PDF rebrandizzati.

logo-navy.png  = logo-600.png cosi' com'e' (fondi chiari)
logo-white.png = pixel opachi forzati a bianco, alpha conservato (fondi scuri/colorati)
"""
from pathlib import Path

from PIL import Image

tools = Path(__file__).parent
out = tools / "out"
out.mkdir(exist_ok=True)

src = Image.open(tools.parent / "assets" / "img" / "logo-600.png").convert("RGBA")
src.save(out / "logo-navy.png", optimize=True)

white = src.copy()
px = white.load()
for y in range(white.height):
    for x in range(white.width):
        r, g, b, a = px[x, y]
        px[x, y] = (255, 255, 255, a)
white.save(out / "logo-white.png", optimize=True)
print("ok:", [p.name for p in out.glob("logo-*.png")])
