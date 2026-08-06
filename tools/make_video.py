"""Codifica i video del sito (H.264 self-hosted) + frame candidati per i poster.

- bolla-drone.mp4: drone notturno delle bolle, ruotato (transpose=2), muto, loop
- pergole-promo.mp4: promo pergole verticale con audio (full->limited range)

usage: python make_video.py <sorgenti-dir> <poster-frames-dir>
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).parent.parent
VID = ROOT / "assets" / "video"


def run(args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def main(src: Path, frames: Path):
    VID.mkdir(exist_ok=True)
    frames.mkdir(parents=True, exist_ok=True)

    drone = VID / "bolla-drone.mp4"
    run(["-i", str(src / "flyvid1.mp4"), "-vf", "transpose=2", "-an",
         "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-crf", "23", "-preset", "veryslow", "-movflags", "+faststart",
         str(drone)])
    print(f"bolla-drone.mp4: {drone.stat().st_size / 1024 / 1024:.1f} MB")

    promo = VID / "pergole-promo.mp4"
    run(["-i", str(src / "flyvid.mp4"),
         "-vf", "scale=in_range=full:out_range=limited",
         "-pix_fmt", "yuv420p", "-color_range", "tv",
         "-c:v", "libx264", "-profile:v", "high", "-crf", "24",
         "-preset", "veryslow", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(promo)])
    print(f"pergole-promo.mp4: {promo.stat().st_size / 1024 / 1024:.1f} MB")

    # frame candidati per i poster
    run(["-ss", "2", "-i", str(drone), "-frames:v", "1", str(frames / "drone-poster.png")])
    for t in ("5", "15", "28", "42", "58"):
        run(["-ss", t, "-i", str(promo), "-frames:v", "1", str(frames / f"promo-{t}s.png")])
    print("poster frames ->", frames)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
