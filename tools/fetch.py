"""Download the old Wix site's HTML and page JSON into tools/raw/.

Usage: python tools/fetch.py
"""
import re
import urllib.request
from pathlib import Path

BASE = "https://napattavatnantacha.wixsite.com/portfolio-3d-artis-1"
RAW = Path(__file__).resolve().parent / "raw"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read()


def main():
    (RAW / "pagejson").mkdir(parents=True, exist_ok=True)
    home = get(BASE).decode("utf8")
    (RAW / "home.html").write_text(home, encoding="utf8")
    pages = re.findall(r'"pageUriSEO":"([^"]*)","pageJsonFileName":"([^"]*)"', home)
    for uri, json_name in pages:
        print("page", uri)
        (RAW / "pagejson" / f"{uri}.json").write_bytes(get(f"https://static.wixstatic.com/sites/{json_name}.json.z?v=3"))
        if uri != "home":
            try:
                (RAW / f"{uri}.html").write_bytes(get(f"{BASE}/{uri}"))
            except Exception as e:  # popups/hidden pages have no URL
                print("  no html:", e)


if __name__ == "__main__":
    main()
