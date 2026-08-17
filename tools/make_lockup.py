"""Prepara per il web il lockup completo Fly System + sponsor Modena FC 1912.

Sorgente: _sorgenti/newlogoflysystem.jpeg (marchio, filetto, canarino dorato e
la riga "SPONSOR UFFICIALE | MODENA CALCIO 1912").

Stesso scontorno usato per lo stemma in tools/make_modena.py: l'arte e su carta
bianca, quindi l'opacita e quanto il pixel si allontana dal bianco e il colore
va de-premoltiplicato. Una soglia secca lascerebbe un alone chiaro, ben visibile
quando la testata scorre sopra una fotografia.

    python tools/make_lockup.py
"""

from PIL import Image
import os

SRC = "_sorgenti/newlogoflysystem.jpeg"
OUT = "assets/img"

# bbox dell'intero lockup nel sorgente 1536x639, verificata a mano
LOCKUP = (282, 108, 1324, 572)

# altezza di riferimento in testata: 48 px logici, piu i multipli per gli schermi densi
TARGETS = {
    "logo-sponsor.png": 48,
    "logo-sponsor@2x.png": 96,
    "logo-sponsor@3x.png": 144,
}


def to_alpha(im):
    """Scontorna dal bianco senza aloni (vedi tools/make_modena.py)."""
    im = im.convert("RGB")
    px = im.load()
    out = Image.new("RGBA", im.size)
    op = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            a = 255 - min(r, g, b)
            if a <= 6:
                op[x, y] = (0, 0, 0, 0)
                continue
            f = a / 255.0
            cr = min(255, max(0, int(round((r - 255 * (1 - f)) / f))))
            cg = min(255, max(0, int(round((g - 255 * (1 - f)) / f))))
            cb = min(255, max(0, int(round((b - 255 * (1 - f)) / f))))
            op[x, y] = (cr, cg, cb, a)
    return out


def main():
    if not os.path.exists(SRC):
        raise SystemExit("sorgente mancante: " + SRC)

    im = to_alpha(Image.open(SRC).convert("RGB").crop(LOCKUP))
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)

    os.makedirs(OUT, exist_ok=True)
    for name, height in TARGETS.items():
        w = max(1, round(im.width * height / im.height))
        out = im.resize((w, height), Image.LANCZOS)
        path = os.path.join(OUT, name)
        out.save(path, optimize=True)
        print("  %-22s %dx%d  %d B" % (name, out.width, out.height, os.path.getsize(path)))

    print("  rapporto: %.3f (larghezza = altezza x %.2f)" % (im.width / im.height, im.width / im.height))


if __name__ == "__main__":
    main()
