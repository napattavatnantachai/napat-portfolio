"""Check that every local href/src in the built pages points to an existing file.

Usage: python tools/check_links.py
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent


def main():
    pages = [ROOT / "index.html", ROOT / "about.html", *sorted((ROOT / "projects").glob("*.html"))]
    missing, checked = [], 0
    for page in pages:
        for ref in re.findall(r'(?:href|src|poster)="([^"#]+)', page.read_text(encoding="utf8")):
            if re.match(r"(https?:|mailto:)", ref):
                continue
            checked += 1
            if not (page.parent / unquote(ref)).resolve().exists():
                missing.append(f"{page.relative_to(ROOT)} -> {ref}")
    print(f"{len(pages)} pages, {checked} local links checked, {len(missing)} missing")
    for m in missing:
        print("  MISSING", m)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
