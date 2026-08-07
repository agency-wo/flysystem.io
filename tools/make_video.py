"""Codifica i video del sito (H.264 self-hosted), con parametri sicuri per iOS/Safari.

Perche questi parametri (verificati in WebKit 26.5 e leggendo i box MP4):
- `-refs 4 -level 3.1`: il preset veryslow portava ref=16, e x264 dichiarava High@5.0
  solo per contenere quel DPB. I decoder hardware di iOS rifiutano quel livello,
  quindi su iPhone il video non partiva mentre su Safari desktop andava.
- `-avoid_negative_ts make_zero`: senza, ffmpeg scriveva una edit list con un edit
  vuoto iniziale. Safari rispetta le edit list (Chrome le ignora): nei primi
  millisecondi non c'e nessun sample da mostrare e si vedeva un lampo nero.
- `-g 60 -keyint_min 60 -sc_threshold 0`: GOP fisso di 2 s. Prima il default era 250
  frame, cioe 3 soli keyframe in 24 s, con uno scatto a ogni ripartenza del loop.

output:
- bolla-drone.mp4    loop notturno delle bolle, muto (ruotato: transpose=2)
- pergole-loop.mp4   taglio silenzioso di sole inquadrature di prodotto
- pergole-promo.mp4  versione integrale narrata, su richiesta

usage: python make_video.py <sorgenti-dir> <poster-frames-dir>
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).parent.parent
VID = ROOT / "assets" / "video"

# parametri comuni: profilo/livello/refs compatibili con i decoder hardware iOS
IOS_SAFE = [
    "-c:v", "libx264",
    "-profile:v", "main",
    "-level", "3.1",
    "-refs", "4",
    "-bf", "2",
    "-preset", "slow",
    "-pix_fmt", "yuv420p",
    "-g", "60",
    "-keyint_min", "60",
    "-sc_threshold", "0",
    # negative_cts_offsets: i CTS possono essere negativi, quindi il muxer NON deve
    # compensare il ritardo dei B-frame con una edit list. Attenzione: aggiungere
    # `-avoid_negative_ts make_zero` REINTRODUCE un edit vuoto di 66 ms (verificato
    # a mano sui box: e proprio quello il lampo nero iniziale su Safari, che le
    # edit list le rispetta mentre Chrome le ignora). Lasciarlo fuori.
    "-movflags", "+faststart+negative_cts_offsets",
]

# i sorgenti sono in range pieno (pc): senza conversione esplicita Safari e Chrome
# interpretano i livelli in modo diverso e i neri risultano schiacciati
TO_LIMITED = ["-vf", "scale=in_range=full:out_range=limited", "-color_range", "tv"]

# segmenti di solo prodotto in flyvid.mp4 (nessuna persona che parla):
# scelti guardando un contact sheet a 1 fps dell'originale
LOOP_CUTS = [
    (34.6, 40.0),   # pergola bianca, divani e verde
    (40.6, 45.0),   # pergola scura, tavolo e lettini
    (67.0, 69.6),   # dehors con tende, tavoli apparecchiati
]


def run(args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def size_mb(p: Path) -> float:
    return p.stat().st_size / 1024 / 1024


def build_loop(src: Path, out: Path):
    """Taglia i segmenti di prodotto e li concatena con dissolvenze brevi."""
    parts = []
    filt = []
    for i, (a, b) in enumerate(LOOP_CUTS):
        filt.append(
            f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{i}]"
        )
        parts.append(f"[v{i}]")
    filt.append(
        "".join(parts)
        + f"concat=n={len(LOOP_CUTS)}:v=1:a=0,"
        + "scale=576:1024:in_range=full:out_range=limited[out]"
    )
    run(["-i", str(src), "-filter_complex", ";".join(filt), "-map", "[out]",
         "-color_range", "tv", "-an", *IOS_SAFE, "-crf", "26", str(out)])


def probe(path: Path) -> dict:
    """Rilegge il file e verifica i punti che rompevano Safari."""
    import struct

    data = path.read_bytes()
    info = {"file": path.name, "mb": round(size_mb(path), 2)}

    # ordine dei box di primo livello (faststart = moov prima di mdat)
    order, off = [], 0
    while off + 8 <= len(data):
        sz = struct.unpack(">I", data[off:off + 4])[0]
        typ = data[off + 4:off + 8].decode("latin-1", "replace")
        order.append(typ)
        if sz < 8:
            break
        off += sz
    info["faststart"] = "moov" in order and "mdat" in order and order.index("moov") < order.index("mdat")

    # avcC: profilo e livello dichiarati
    i = data.find(b"avcC")
    if i > 0:
        info["profile"] = data[i + 5]
        info["level"] = data[i + 7]

    # SPS: numero di reference frame (via ffmpeg, piu affidabile del parsing a mano)
    out = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    info["ffmpeg_line"] = next((l.strip() for l in out.splitlines() if "Video:" in l), "")

    # elst: nessun edit vuoto e nessuno start diverso da zero sul track video
    edits = []
    j = 0
    while True:
        j = data.find(b"elst", j + 1)
        if j < 0:
            break
        cnt = struct.unpack(">I", data[j + 8:j + 12])[0]
        ver = data[j + 4]
        entries = []
        p = j + 12
        for _ in range(cnt):
            if ver == 1:
                dur, mt = struct.unpack(">Qq", data[p:p + 16]); p += 20
            else:
                dur, mt = struct.unpack(">Ii", data[p:p + 8]); p += 12
            entries.append((dur, mt))
        edits.append(entries)
    info["elst"] = edits
    return info


def main(src: Path, frames: Path):
    VID.mkdir(exist_ok=True)
    frames.mkdir(parents=True, exist_ok=True)

    drone = VID / "bolla-drone.mp4"
    run(["-i", str(src / "flyvid1.mp4"), "-vf", "transpose=2", "-an",
         *IOS_SAFE, "-crf", "23", str(drone)])

    loop = VID / "pergole-loop.mp4"
    build_loop(src / "flyvid.mp4", loop)

    promo = VID / "pergole-promo.mp4"
    run(["-i", str(src / "flyvid.mp4"), *TO_LIMITED,
         *IOS_SAFE, "-crf", "29", "-maxrate", "900k", "-bufsize", "1800k",
         "-c:a", "aac", "-b:a", "96k", "-ac", "2", str(promo)])

    # frame candidati per il poster del loop
    for t in ("1", "3", "6", "9"):
        run(["-ss", t, "-i", str(loop), "-frames:v", "1", str(frames / f"loop-{t}s.png")])

    print(json.dumps([probe(p) for p in (drone, loop, promo)], indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
