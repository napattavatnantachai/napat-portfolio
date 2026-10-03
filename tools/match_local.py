"""Find higher-resolution local originals for low-res site images.

Compares a perceptual hash (dHash) of each site image against every image in
a local folder and writes the best matches to tools/raw/local_matches.json.

Usage: python tools/match_local.py "F:/Portfolio"
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent.parent
EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
MAX_FILE = 400_000_000
MAX_DIST = 8  # of 128 bits


def dhash(im):
    """128-bit difference hash: horizontal + vertical gradients on a 9x8 grayscale."""
    g = im.convert("L")
    h = g.resize((9, 8), Image.LANCZOS).tobytes()
    v = g.resize((8, 9), Image.LANCZOS).tobytes()
    bits = [h[r * 9 + c] > h[r * 9 + c + 1] for r in range(8) for c in range(8)]
    bits += [v[r * 8 + c] > v[(r + 1) * 8 + c] for r in range(8) for c in range(8)]
    return sum(1 << i for i, b in enumerate(bits) if b)


def index_file(path):
    try:
        with Image.open(path) as im:
            w, h = im.size
            im.draft("RGB", (256, 256))
            if im.mode in ("I;16", "I;16B", "I", "F"):
                im = im.point(lambda x: x / 256).convert("L")
            return str(path), w, h, dhash(im)
    except Exception:
        return None


def main():
    folder = Path(sys.argv[1])
    files = [p for p in folder.rglob("*") if p.suffix.lower() in EXTS and p.stat().st_size < MAX_FILE]
    print(f"indexing {len(files)} local images...", flush=True)
    with ProcessPoolExecutor() as ex:
        local = [r for r in ex.map(index_file, files, chunksize=8) if r]
    print(f"indexed {len(local)}", flush=True)

    targets = json.loads((ROOT / "tools" / "raw" / "lowres.json").read_text())
    matches = {}
    for name, w, h in targets:
        with Image.open(ROOT / "assets" / "img" / name) as im:
            hs = dhash(im)
        ratio = w / h
        best = None
        for path, lw, lh, lhash in local:
            if lw <= w * 1.2 or abs(lw / lh - ratio) > 0.04 * ratio:
                continue
            d = bin(hs ^ lhash).count("1")
            if d <= MAX_DIST and (best is None or (d, -lw) < (best[0], -best[2])):
                best = (d, path, lw, lh)
        if best:
            matches[name] = {"dist": best[0], "path": best[1], "w": best[2], "h": best[3], "was": [w, h]}
            print(f"{name}: {w}x{h} -> {best[2]}x{best[3]} d={best[0]} {best[1]}", flush=True)
    (ROOT / "tools" / "raw" / "local_matches.json").write_text(json.dumps(matches, indent=1, ensure_ascii=False),
                                                              encoding="utf8")
    print(f"{len(matches)}/{len(targets)} low-res images have a higher-res local original")


if __name__ == "__main__":
    main()
