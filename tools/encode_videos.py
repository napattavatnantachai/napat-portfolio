"""Compress media_src/*.mp4 into web-sized assets/video/*.mp4 with ffmpeg.

Clips that only ever play as silent backgrounds lose their audio track and
get stronger compression; clips with player controls keep audio.

Usage: python tools/encode_videos.py
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media_src"
OUT = ROOT / "assets" / "video"
LONG_CLIP = 180  # seconds


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip() or 0)


def videos_with_controls():
    pages = json.loads((ROOT / "data" / "wix_pages.json").read_text(encoding="utf8"))
    return {b["id"] for p in pages.values() for b in p["blocks"] if b["type"] == "video" and not b.get("bg")}


def encode(src, dest, keep_audio):
    if dest.exists():
        return f"skip {dest.name}"
    tmp = dest.with_name(dest.stem + ".tmp.mp4")
    if duration(src) > LONG_CLIP:
        # long clips must stay under GitHub's 100MB file limit
        video = ["-vf", "scale='min(1280,iw)':-2,fps=30", "-crf", "28", "-maxrate", "1500k", "-bufsize", "3M"]
    else:
        video = ["-vf", "scale='min(1920,iw)':-2", "-crf", "24" if keep_audio else "26",
                 "-maxrate", "6M", "-bufsize", "12M"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264", "-preset", "slow",
           *video, "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    cmd += ["-c:a", "aac", "-b:a", "128k"] if keep_audio else ["-an"]
    subprocess.run(cmd + [str(tmp)], check=True)
    tmp.replace(dest)
    return f"{dest.name}: {src.stat().st_size // 1_000_000}MB -> {dest.stat().st_size // 1_000_000}MB"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    controls = videos_with_controls()
    jobs = [(s, OUT / s.name, s.stem in controls) for s in sorted(SRC.glob("*.mp4"))]
    with ThreadPoolExecutor(3) as ex:
        for line in ex.map(lambda j: encode(*j), jobs):
            print(line, flush=True)
    total = sum(f.stat().st_size for f in OUT.glob("*.mp4"))
    print(f"total {total // 1_000_000}MB")


if __name__ == "__main__":
    main()
