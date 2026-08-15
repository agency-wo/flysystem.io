"""Estrae lo stemma del Modena FC 1912 dal lockup sponsor e lo prepara per il web.

Sorgente: _sorgenti/newlogoflysystem.jpeg (lockup Fly System + sponsor ufficiale).
Lo stemma e' il canarino dorato con "1912"; qui viene ritagliato, il bianco della
pagina diventa trasparente e il risultato viene salvato a 1x e 2x cosi' che possa
stare sia sulla carta chiara sia sulla fascia scura del footer.

    python tools/make_modena.py
"""

from PIL import Image
import os

SRC = "_sorgenti/newlogoflysystem.jpeg"
OUT = "assets/img"

# bbox dello stemma nel sorgente, verificato a mano sul file 1536x639
CREST = (738, 434, 812, 530)

# altezza logica di riferimento: lo stemma viene mostrato a ~40px
TARGETS = {"modena-crest.png": 96, "modena-crest@2x.png": 192}


def to_alpha(im):
    """Scontorna l'oro dal bianco senza lasciare aloni.

    L'arte e' su carta bianca, quindi ogni pixel vale colore*a + bianco*(1-a):
    l'alopacita' e' semplicemente quanto il pixel si allontana dal bianco, e il
    colore va poi de-premoltiplicato. Una soglia secca lascerebbe invece un
    contorno chiaro, ben visibile sulla fascia scura del footer.
    """
    im = im.convert("RGB")
    px = im.load()
    out = Image.new("RGBA", im.size)
    op = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            lo = min(r, g, b)
            a = 255 - lo
            if a <= 6:
                op[x, y] = (0, 0, 0, 0)
                continue
            f = a / 255.0
            # de-premoltiplicazione rispetto al bianco
            cr = min(255, max(0, int(round((r - 255 * (1 - f)) / f))))
            cg = min(255, max(0, int(round((g - 255 * (1 - f)) / f))))
            cb = min(255, max(0, int(round((b - 255 * (1 - f)) / f))))
            op[x, y] = (cr, cg, cb, a)
    return out


def main():
    if not os.path.exists(SRC):
        raise SystemExit("sorgente mancante: " + SRC)
    im = Image.open(SRC).convert("RGB").crop(CREST)
    im = to_alpha(im)

    # ritaglio esatto sul contenuto rimasto
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


if __name__ == "__main__":
    main()
