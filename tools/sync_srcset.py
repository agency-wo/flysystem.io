"""Allinea le srcset dell'HTML alle misure che esistono davvero su disco.

Nasce da un errore fatto in V15: avevo esteso le srcset "a tutte le varianti
piu grandi presenti su disco" e mi sono portato dentro tre file rimasti da
luglio che avevano lo stesso nome ma **un'altra fotografia** (contatti/lead-1440
era 1440x2021 contro i 1210x1024 dell'immagine corrente). Da qui la regola:

    una variante entra nella srcset solo se il suo RAPPORTO D'ASPETTO
    coincide con quello dell'immagine di riferimento.

Segnala anche i file orfani, cioe le misure su disco che nessuna pagina cita:
li elenca e, con --pulisci, li elimina.

    python tools/sync_srcset.py [--pulisci]
"""
import glob
import os
import re
import sys

import pillow_avif  # noqa: F401
from PIL import Image

TOLLERANZA = 0.012  # 1,2% sul rapporto: copre l'arrotondamento delle misure


def larghezza_altezza(p):
    try:
        im = Image.open(p)
        return im.width, im.height
    except Exception:
        return None


def varianti_valide(stem, ext):
    """Tutte le misure di <stem> in <ext> che sono la STESSA fotografia."""
    trovate = []
    for p in glob.glob(f"{stem}-*.{ext}"):
        m = re.search(r"-(\d+)\." + ext + r"$", p)
        if not m:
            continue
        wh = larghezza_altezza(p)
        if not wh:
            continue
        trovate.append((int(m.group(1)), wh[0] / wh[1], p))
    if not trovate:
        return []
    # il riferimento e la misura piu grande: e quella appena rigenerata
    trovate.sort()
    rif = trovate[-1][1]
    buone, scartate = [], []
    for w, r, p in trovate:
        (buone if abs(r - rif) / rif <= TOLLERANZA else scartate).append((w, r, p))
    for w, r, p in scartate:
        print(f"    ESCLUSA {os.path.basename(p)}: rapporto {r:.3f} contro {rif:.3f}, e un'altra foto")
    return buone


def main(pulisci):
    citati = set()
    cambiati = 0

    for f in sorted(glob.glob("*.html")):
        s = open(f, encoding="utf-8").read()
        originale = s

        def rifai(m):
            nonlocal cambiati
            ss = m.group(1)
            cand = re.findall(r"(\S+?)-(\d+)\.(avif|webp|jpg)\s+\d+w", ss)
            if not cand:
                return m.group(0)
            stem, _, ext = cand[0]
            buone = varianti_valide(stem, ext)
            if not buone:
                return m.group(0)
            nuovo = ", ".join(f"{stem}-{w}.{ext} {w}w" for w, _, _ in buone)
            for w, _, p in buone:
                citati.add(os.path.normpath(p))
            if nuovo != ss.strip():
                cambiati += 1
            return f'srcset="{nuovo}"'

        s = re.sub(r'srcset="([^"]+)"', rifai, s)

        # il src di ripiego deve puntare a una misura che esiste
        def ripiego(m):
            p = m.group(1)
            if os.path.exists(p):
                citati.add(os.path.normpath(p))
                return m.group(0)
            stem = re.sub(r"-\d+\.jpg$", "", p)
            buone = varianti_valide(stem, "jpg")
            if not buone:
                return m.group(0)
            scelto = buone[len(buone) // 2][2]
            citati.add(os.path.normpath(scelto))
            print(f"    ripiego aggiornato: {os.path.basename(p)} -> {os.path.basename(scelto)}")
            return f'src="{scelto.replace(os.sep, "/")}"'

        s = re.sub(r'src="(assets/img/[^"]+\.jpg)"', ripiego, s)

        if s != originale:
            open(f, "w", encoding="utf-8").write(s)
            print(f"  {f}: srcset allineate")

    # orfani: misure su disco che nessuna pagina cita
    orfani = []
    for p in glob.glob("assets/img/**/*.*", recursive=True):
        if not os.path.isfile(p) or not re.search(r"-\d+\.(avif|webp|jpg)$", p):
            continue
        gemelli = [re.sub(r"\.(avif|webp|jpg)$", "." + e, p) for e in ("avif", "webp", "jpg")]
        if not any(os.path.normpath(g) in citati for g in gemelli):
            orfani.append(p)

    if orfani:
        print(f"\n  file orfani (nessuna pagina li cita): {len(orfani)}")
        for p in sorted(orfani)[:40]:
            print(f"    {p}  {os.path.getsize(p)//1024} KB")
        if pulisci:
            for p in orfani:
                os.remove(p)
            print(f"  eliminati {len(orfani)} file")
        else:
            print("  (usa --pulisci per eliminarli)")
    print(f"\n  srcset modificate: {cambiati}")


if __name__ == "__main__":
    main("--pulisci" in sys.argv)
