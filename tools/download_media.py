"""Download every image and video referenced in data/wix_pages.json.

Images  -> assets/img/<id>.webp   (Wix-resized to max 2400px; originals are not served)
Videos  -> media_src/<id>.mp4     (highest quality; compressed later by encode_videos.py)

Usage: python tools/download_media.py
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "assets" / "img"
SRC_DIR = ROOT / "media_src"
MAX_PX = 2400


def media_id(uri):
    return uri.split("~")[0].split(".")[0]


def collect():
    pages = json.loads((ROOT / "data" / "wix_pages.json").read_text(encoding="utf8"))
    images, videos = {}, {}
    for p in pages.values():
        for b in p["blocks"]:
            if b["type"] == "image" and b["uri"] and not b["uri"].startswith("http"):
                images[media_id(b["uri"])] = b["uri"]
            elif b["type"] == "gallery":
                for it in b["items"]:
                    if it.get("uri"):
                        images[media_id(it["uri"])] = it["uri"]
            elif b["type"] == "video":
                best = next((q for q in ("1080p", "720p", "480p", "360p") if q in b["qualities"]), None)
                if best:
                    videos[b["id"]] = best
    return images, videos


def download(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return "skip"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=300).read()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return "ok"


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    images, videos = collect()
    jobs = []
    for mid, uri in images.items():
        url = f"https://static.wixstatic.com/media/{uri}/v1/fit/w_{MAX_PX},h_{MAX_PX},q_90/file.webp"
        jobs.append((url, IMG_DIR / f"{mid}.webp"))
    for vid, q in videos.items():
        jobs.append((f"https://video.wixstatic.com/video/{vid}/{q}/mp4/file.mp4", SRC_DIR / f"{vid}.mp4"))
        # first frame poster, used until the video loads
        jobs.append((f"https://static.wixstatic.com/media/{vid}f000.jpg/v1/fit/w_1920,h_1920,q_85/file.webp",
                     IMG_DIR / f"{vid}_poster.webp"))
    print(f"{len(images)} images, {len(videos)} videos")
    failed = []

    def run(job):
        try:
            return download(*job)
        except Exception as e:
            failed.append((job[0], str(e)))
            return "fail"

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(run, jobs))
    print({r: results.count(r) for r in set(results)})
    for url, err in failed:
        print("FAILED", url, err)


if __name__ == "__main__":
    main()
