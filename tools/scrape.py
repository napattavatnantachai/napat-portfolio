"""Extract content from the old Wix site into data/wix_pages.json.

Reads the page JSON files (component tree + data) and the SSR HTML (for
gallery and background-video data), and emits each page's content blocks
in visual order (top-to-bottom, left-to-right).

Usage: python tools/scrape.py   (run tools/fetch.py first)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "tools" / "raw"


def load_page(uri):
    j = json.loads((RAW / "pagejson" / f"{uri}.json").read_text(encoding="utf8"))
    # design items and data items share one id namespace; merge for lookups
    return j, {**j["data"].get("design_data", {}), **j["data"]["document_data"]}


def ref(dd, q):
    return dd.get(q.lstrip("#")) if isinstance(q, str) else q


def background(dd, design_q):
    """Background image/video of a section, strip or column, if any."""
    design = ref(dd, design_q)
    bg = ref(dd, design.get("background")) if design else None
    media = ref(dd, bg.get("mediaRef")) if bg else None
    if not media:
        return None
    if media.get("type") == "WixVideo":
        b = video_from_item(media)
        if b:
            b["bg"] = True
        return b
    if media.get("type") == "Image" and media.get("uri"):
        return {"type": "image", "uri": media["uri"], "w": media.get("width"), "h": media.get("height"),
                "alt": "", "bg": True}
    return None


def resolve_link(dd, q, page_ids):
    link = ref(dd, q)
    if not link:
        return None
    t = link.get("type")
    if t == "PageLink":
        return {"page": page_ids.get(link.get("pageId", "").lstrip("#"), "home")}
    if t == "ExternalLink":
        return {"url": link.get("url")}
    if t == "EmailLink":
        return {"url": "mailto:" + link.get("recipient", "")}
    if t == "AnchorLink":
        return None
    return {"raw": t}


def video_from_item(v):
    if not v:
        return None
    vid = v.get("videoId") or v.get("uri")
    if not vid:
        return None
    qs = [q.get("quality") for q in v.get("qualities", [])]
    poster = None
    if v.get("posterImageRef"):
        poster = v["posterImageRef"]
    return {"type": "video", "id": vid, "w": v.get("width"), "h": v.get("height"),
            "qualities": qs, "poster": poster}


def galleries_from_html(page_html):
    m = re.search(r'id="wix-warmup-data"[^>]*>(.*?)</script>', page_html, re.S)
    out = {}
    if not m:
        return out
    w = json.loads(m.group(1))
    for app in w.get("appsWarmupData", {}).values():
        for k, v in app.items():
            if k.endswith("_galleryData") and isinstance(v, dict):
                items = sorted(v.get("items", []), key=lambda i: i.get("orderIndex", 0), reverse=True)
                out[k[: -len("_galleryData")]] = [
                    {"uri": i["mediaUrl"], "w": i["metaData"].get("width"), "h": i["metaData"].get("height"),
                     "title": i["metaData"].get("title", ""),
                     "video": i["metaData"].get("type") == "video"}
                    for i in items
                ]
    return out


def extract(uri, page_ids):
    j, dd = load_page(uri)
    page_html_path = RAW / f"{uri}.html"
    page_html = page_html_path.read_text(encoding="utf8") if page_html_path.exists() else ""
    galleries = galleries_from_html(page_html)
    blocks = []

    def emit(c, x, y, block):
        lay = c.get("layout", {})
        block.setdefault("dispW", lay.get("width"))
        block.setdefault("dispH", lay.get("height"))
        block["_y"], block["_x"], block["comp"] = y, x, c["id"]
        blocks.append(block)

    def walk(c, ox, oy):
        lay = c.get("layout", {})
        x, y = ox + lay.get("x", 0), oy + lay.get("y", 0)
        ctype = c.get("componentType", "").split(".")[-1]
        data = ref(dd, c.get("dataQuery"))
        if data and data.get("metaData", {}).get("isHidden"):
            return
        bg = background(dd, c.get("designQuery"))
        if bg:
            bg["dispW"], bg["dispH"] = lay.get("width"), lay.get("height")
            emit(c, x, y, bg)
        if ctype == "WRichText" and data:
            emit(c, x, y, {"type": "text", "html": data.get("text", "")})
        elif ctype == "WPhoto" and data:
            b = {"type": "image", "uri": data.get("uri"), "w": data.get("width"), "h": data.get("height"),
                 "alt": data.get("alt", ""), "dispW": lay.get("width"), "dispH": lay.get("height")}
            lk = resolve_link(dd, data.get("link"), page_ids)
            if lk:
                b["link"] = lk
            emit(c, x, y, b)
        elif ctype in ("SiteButton", "StylableButton") and data:
            lk = resolve_link(dd, data.get("link"), page_ids)
            if lk:
                emit(c, x, y, {"type": "button", "label": data.get("label", ""), "link": lk})
        elif ctype == "VideoPlayer" and data:
            v = video_from_item(ref(dd, data.get("videoRef")))
            if v:
                v["dispW"], v["dispH"] = lay.get("width"), lay.get("height")
                emit(c, x, y, v)
        elif ctype in ("SlideShowGallery", "TPA3DCarousel") and data:
            items = []
            for q in data.get("items", []):
                it = ref(dd, q)
                if it:
                    items.append({"uri": it.get("uri"), "w": it.get("width"), "h": it.get("height"),
                                  "title": it.get("title", "")})
            emit(c, x, y, {"type": "gallery", "kind": ctype, "items": items})
        elif ctype == "TPAWidget" and c["id"] in galleries:
            emit(c, x, y, {"type": "gallery", "kind": "pro", "items": galleries[c["id"]]})
        for ch in c.get("components", []):
            walk(ch, x, y)

    walk(j["structure"], 0, 0)
    blocks.sort(key=lambda b: (b["_y"], b["_x"]))
    return {"uri": uri, "title": j.get("title"), "blocks": blocks}


def main():
    home = (RAW / "home.html").read_text(encoding="utf8")
    pages = re.findall(r'"pageId":"(\w+)","title":"([^"]*)","pageUriSEO":"([^"]*)"', home)
    page_ids = {pid: uri for pid, _, uri in pages}
    out = {}
    for _, _, uri in pages:
        out[uri] = extract(uri, page_ids)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "wix_pages.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf8")
    for uri, p in out.items():
        kinds = {}
        for b in p["blocks"]:
            kinds[b["type"]] = kinds.get(b["type"], 0) + 1
        print(f"{uri:32} {kinds}")


if __name__ == "__main__":
    main()
