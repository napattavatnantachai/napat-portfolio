"""Generate the static site from data/wix_pages.json + data/site.json.

Writes index.html, about.html and projects/*.html at the project root.
Usage: python tools/build.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SITE = json.loads((DATA / "site.json").read_text(encoding="utf8"))
WIX = json.loads((DATA / "wix_pages.json").read_text(encoding="utf8"))

# wix uri -> new page info
PAGES = {p["wix"]: p for p in SITE["pages"]}
ROW_TOLERANCE = 30      # px: blocks starting this close vertically sit in one row
FULL_WIDTH = 900        # px: wix width at which a block counts as full-bleed
ICON_MAX = 70           # px: images this short are software/tool icons


def esc(s):
    return html.escape(s or "", quote=True)


def media_id(uri):
    return uri.split("~")[0].split(".")[0]


def img_src(uri, root):
    return f"{root}assets/img/{media_id(uri)}.webp"


def video_src(vid, root):
    return f"{root}assets/video/{vid}.mp4"


def poster_src(vid, root):
    return f"{root}assets/img/{vid}_poster.webp"


def page_href(wix_uri, root):
    if wix_uri in ("home", ""):
        return f"{root}index.html"
    if wix_uri == "my-cv":
        return f"{root}about.html"
    p = PAGES.get(wix_uri)
    return f"{root}projects/{p['slug']}.html" if p else None


# ---------------------------------------------------------------- rich text

URL_RE = re.compile(r'(?<!href=")(https?://[^\s<|"]+)')


def clean_text(raw):
    """Wix rich text -> minimal semantic HTML (headings, paragraphs, lists, bold, links)."""
    s = raw
    s = re.sub(r'<span style="[^"]*font-weight:bold[^"]*">(.*?)</span>', r"<strong>\1</strong>", s, flags=re.S)
    # heading levels in wix are styling, not structure: map by theme font
    def heading(m):
        tag, cls, inner = m.group(1), m.group(2), m.group(3)
        if cls in ("font_0", "font_2") or (tag == "h1" and cls != "font_8"):
            return f"<h3>{inner}</h3>"
        if cls == "font_5":
            return f"<h4>{inner}</h4>"
        return f"<p>{inner}</p>"
    s = re.sub(r'<(h[1-6]) class="(font_\d+)"[^>]*>(.*?)</\1>', heading, s, flags=re.S)
    s = re.sub(r"<(p|ul|ol|li)\b[^>]*>", r"<\1>", s)
    s = re.sub(r'<a\b[^>]*?href="([^"]*)"[^>]*>', r'<a href="\1" target="_blank" rel="noopener">', s)
    s = re.sub(r"</?(span|div|wix-[\w-]+)\b[^>]*>", "", s)
    s = s.replace("​", "")
    s = re.sub(r"<p>\s*(<br\s*/?>)?\s*</p>", "", s)
    s = re.sub(r"<li>\s*(<p>)?\s*(<br\s*/?>)?\s*(</p>)?\s*</li>", "", s)
    s = re.sub(r"(<br\s*/?>\s*){2,}", "<br>", s)
    s = URL_RE.sub(r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    return s.strip()


# ---------------------------------------------------------------- blocks

def is_icon(b):
    return b["type"] == "image" and (b.get("dispH") or 999) <= ICON_MAX and (b.get("dispW") or 999) <= ICON_MAX * 2


def render_image(b, root, cls="", lightbox=True):
    w, h = b.get("w") or 1, b.get("h") or 1
    alt = esc(b.get("alt") or "")
    full = img_src(b["uri"], root)
    tag = f'<img src="{full}" alt="{alt}" width="{w}" height="{h}" loading="lazy" decoding="async">'
    if b.get("link"):
        lk = b["link"]
        href = lk.get("url") or page_href(lk.get("page", ""), root) or "#"
        return f'<a class="media {cls}" href="{esc(href)}">{tag}</a>'
    if lightbox:
        return f'<a class="media {cls}" href="{full}" data-lightbox>{tag}</a>'
    return f'<span class="media {cls}">{tag}</span>'


def render_video(b, root, ambient=None):
    vid = b["id"]
    w, h = b.get("w") or b.get("dispW") or 16, b.get("h") or b.get("dispH") or 9
    ambient = b.get("bg") if ambient is None else ambient
    attrs = ('muted loop playsinline preload="none" data-autoplay' if ambient
             else 'controls playsinline preload="none"')
    return (f'<video class="media" {attrs} poster="{poster_src(vid, root)}" width="{w}" height="{h}">'
            f'<source src="{video_src(vid, root)}" type="video/mp4"></video>')


def render_gallery(b, root):
    items = [i for i in b["items"] if i.get("uri")]
    if b["kind"] in ("SlideShowGallery", "TPA3DCarousel"):
        cells = "".join(render_image(i, root) for i in items)
        return f'<div class="carousel">{cells}</div>'
    cols = 4 if len(items) >= 7 else 3 if len(items) >= 3 else len(items)
    cells = "".join(render_image(i, root) for i in items)
    return f'<div class="gallery" style="--cols:{cols}">{cells}</div>'


def render_button(b, root, page):
    lk = b["link"]
    href = lk.get("url") or page_href(lk.get("page", ""), root)
    if not href:
        return ""
    label = b["label"]
    target = PAGES.get(lk.get("page"))
    if label == "Up":
        return ""  # replaced by the breadcrumb at the top of the page
    if target and label.lower() == "view more":
        label = f"View {target['title']}"
    return f'<a class="btn" href="{esc(href)}">{esc(label)} <span aria-hidden="true">→</span></a>'


def render_block(b, root, page):
    t = b["type"]
    if t == "text":
        txt = clean_text(b["html"])
        return f'<div class="text">{txt}</div>' if txt else ""
    if t == "image":
        if b["uri"].startswith("http"):
            return ""  # wix loader placeholder
        if is_icon(b):
            return render_image(b, root, "icon", lightbox=False)
        return render_image(b, root)
    if t == "video":
        return render_video(b, root)
    if t == "gallery":
        return render_gallery(b, root)
    if t == "button":
        return render_button(b, root, page)
    return ""


def side_by_side(row, b):
    """True if b overlaps the row vertically and no row member horizontally."""
    for o in row:
        oh = o.get("dispH") or 0
        if b["_y"] > o["_y"] + max(ROW_TOLERANCE, oh - 10):
            return False
        if b["_x"] < o["_x"] + (o.get("dispW") or 0) - 10 and o["_x"] < b["_x"] + (b.get("dispW") or 0) - 10:
            return False
    return True


def group_rows(blocks):
    """Group blocks that sit side by side into rows."""
    rows = []
    for b in blocks:
        if rows and side_by_side(rows[-1], b):
            rows[-1].append(b)
        else:
            rows.append([b])
    merged = []
    for r in rows:  # icon strips that wix stacked with small overlaps -> one strip
        if merged and all(map(is_icon, r)) and all(map(is_icon, merged[-1])):
            merged[-1].extend(r)
        else:
            merged.append(r)
    for r in merged:
        r.sort(key=lambda b: (b["_y"] // 40, b["_x"]))
    return merged


def render_row(row, root, page):
    icons = [b for b in row if is_icon(b)]
    if icons and len(icons) == len(row):
        return '<div class="icons">' + "".join(render_block(b, root, page) for b in row) + "</div>"
    parts = []
    for b in row:
        inner = render_block(b, root, page)
        if inner:
            grow = max(1, round(b.get("dispW") or 300))
            parts.append(f'<div class="cell" style="--grow:{grow}">{inner}</div>')
    if not parts:
        return ""
    if len(parts) == 1:
        b = row[0]
        cap = ""
        if b["type"] in ("image", "video") and (b.get("dispW") or FULL_WIDTH) < FULL_WIDTH * 0.8:
            cap = f' style="max-width:{round(b["dispW"] * 1.2)}px"'
        return f'<div class="row single"{cap}>{parts[0]}</div>'
    return f'<div class="row">{"".join(parts)}</div>'


def render_banner(bg, overlay, root, page):
    """Full-width background media with whatever sits on top of it."""
    media = render_video(bg, root, ambient=True) if bg["type"] == "video" else render_image(bg, root, lightbox=False)
    ratio = f'{bg.get("dispW") or 980} / {bg.get("dispH") or 413}'
    inner = "".join(render_row(r, root, page) for r in group_rows(overlay))
    over = f'<div class="banner-over">{inner}</div>' if inner.strip() else ""
    return f'<section class="banner" style="aspect-ratio:{ratio}">{media}{over}</section>'


def plain(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip().lower()


def render_body(page_blocks, root, page):
    blocks, seen = [], set()
    title = (page.get("title") or "").lower()
    for b in page_blocks:
        if b["type"] == "text" and plain(b["html"]) == title:
            continue  # already shown as the page heading
        key = (b["type"], b.get("id") or b.get("uri"))
        if b["type"] in ("video", "image") and key in seen and (b.get("dispW") or 0) >= FULL_WIDTH:
            continue  # wix pages repeat the hero clip as a section background
        seen.add(key)
        blocks.append(b)
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        if b.get("bg") and (b.get("dispW") or 0) >= FULL_WIDTH:
            end = b["_y"] + (b.get("dispH") or 0)
            j, overlay = i + 1, []
            while j < len(blocks) and blocks[j]["_y"] < end - 10 and not blocks[j].get("bg"):
                overlay.append(blocks[j])
                j += 1
            out.append(render_banner(b, overlay, root, page))
            i = j
            continue
        j = i + 1
        while j < len(blocks) and not (blocks[j].get("bg") and (blocks[j].get("dispW") or 0) >= FULL_WIDTH):
            j += 1
        out.extend(render_row(r, root, page) for r in group_rows(blocks[i:j]))
        i = j
    return "\n".join(o for o in out if o)


# ---------------------------------------------------------------- layout

def social_links():
    return "".join(
        f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["label"])}</a>' for s in SITE["social"])


def asset_version():
    """Short content hash for css/js so browsers fetch new files after each deploy."""
    import hashlib
    h = hashlib.sha1()
    for f in ("css/style.css", "js/main.js"):
        h.update((ROOT / f).read_bytes())
    return h.hexdigest()[:8]


ASSET_V = asset_version()


def layout(title, body, root, active="", description="", noindex=False):
    meta_robots = '<meta name="robots" content="noindex">' if noindex else ""
    full_title = f"{title} | {SITE['name']}" if title else f"{SITE['name']} | {SITE['role']}"
    nav = "".join(
        f'<a href="{root}{href}"{" aria-current=page" if key == active else ""}>{label}</a>'
        for key, href, label in (("work", "index.html#work", "Work"), ("about", "about.html", "About / CV")))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description or SITE['tagline'])}">
{meta_robots}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}css/style.css?v={ASSET_V}">
<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">
<script>
  // motion is opt-in: without JS or with reduced motion, everything stays visible
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) document.documentElement.classList.add("motion");
</script>
</head>
<body>
<div class="veil" aria-hidden="true"></div>
<header class="site-header">
  <a class="logo" href="{root}index.html">{esc(SITE['logo'])}</a>
  <nav>{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <div>
    <strong>{esc(SITE['fullName'])}</strong>
    <a href="mailto:{esc(SITE['email'])}">{esc(SITE['email'])}</a>
  </div>
  <div class="social">{social_links()}</div>
  <small>© {SITE['year']} {esc(SITE['fullName'])}. All rights reserved.</small>
</footer>
<div class="lightbox" hidden><button class="lb-close" aria-label="Close">×</button><button class="lb-prev" aria-label="Previous">‹</button><img alt=""><button class="lb-next" aria-label="Next">›</button></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js" defer></script>
<script src="{root}js/main.js?v={ASSET_V}" defer></script>
</body>
</html>
"""


def back_bar(up_href, up_label):
    """Back (previous page) + up (parent page) buttons, plus a floating back button."""
    return (f'<nav class="backbar" aria-label="Back navigation">'
            f'<a class="pill-btn" href="{up_href}" data-back>← Back</a>'
            f'<a class="pill-btn ghost" href="{up_href}">↑ {esc(up_label)}</a></nav>'
            f'<a class="float-back" href="{up_href}" data-back aria-label="Back to previous page">← Back</a>')


def build_home():
    root = ""
    cards = []
    for c in SITE["home"]:
        page = PAGES.get(c.get("wix"))
        href = f"projects/{page['slug']}.html" if page else None
        if "video" in c:
            media = (f'<video muted loop playsinline preload="none" data-autoplay poster="{poster_src(c["video"], root)}">'
                     f'<source src="{video_src(c["video"], root)}" type="video/mp4"></video>')
        else:
            media = f'<img src="{img_src(c["image"], root)}" alt="" loading="lazy" decoding="async">'
        tags = "".join(f"<li>{esc(t)}</li>" for t in c.get("tags", []))
        info = (f'<div class="card-info"><h2>{esc(c["title"])}</h2><p>{esc(c.get("subtitle", ""))}</p>'
                f'<ul class="tags">{tags}</ul></div>')
        if href:
            cards.append(f'<a class="card{" portrait" if c.get("portrait") else ""}" href="{href}"><div class="card-media">{media}</div>{info}</a>')
        else:  # no project page: play the clip in the lightbox
            cards.append(f'<a class="card" href="{video_src(c["video"], root)}" data-lightbox-video>'
                         f'<div class="card-media">{media}</div>{info}</a>')
    hero = SITE["hero"]
    # hero cycles through every landscape project video on the home page
    reel = [c for c in SITE["home"] if "video" in c and not c.get("portrait") and PAGES.get(c.get("wix"))]
    hero_reel = "".join(
        f'<video muted playsinline preload="{"auto" if i == 0 else "none"}"{" autoplay" if i == 0 else ""}'
        f'{" class=is-active" if i == 0 else ""} poster="{poster_src(c["video"], root)}"'
        f'>'
        f'<source src="{video_src(c["video"], root)}" type="video/mp4"></video>'
        for i, c in enumerate(reel))
    body = f"""
<section class="hero">
  <div class="hero-reel">{hero_reel}</div>
  <div class="hero-text">
    <p class="eyebrow">{esc(SITE['role'])}</p>
    <h1>{esc(SITE['fullName'])}</h1>
    <p>{esc(SITE['tagline'])}</p>
    <a class="btn" href="#work">View work <span aria-hidden="true">↓</span></a>
  </div>
</section>
<section id="work" class="cards">
{"".join(cards)}
</section>"""
    (ROOT / "index.html").write_text(layout("", body, root, "work"), encoding="utf8")


def build_project(page):
    root = "../"
    wix = WIX[page["wix"]]
    crumbs = f'<a href="{root}index.html#work">Work</a>'
    up_href, up_label = f"{root}index.html#work", "All projects"
    if page.get("parent"):
        parent = PAGES[page["parent"]]
        crumbs += f' <span>/</span> <a href="{root}projects/{parent["slug"]}.html">{esc(parent["title"])}</a>'
        up_href, up_label = f"{root}projects/{parent['slug']}.html", parent["title"]
    body = render_body(wix["blocks"], root, page)
    nav = ""
    order = [p for p in SITE["pages"] if not p.get("parent")]
    if not page.get("parent"):
        k = order.index(page)
        prev_p, next_p = order[k - 1], order[(k + 1) % len(order)]
        nav = (f'<nav class="pager"><a href="{prev_p["slug"]}.html">← {esc(prev_p["title"])}</a>'
               f'<a href="{next_p["slug"]}.html">{esc(next_p["title"])} →</a></nav>')
    subs = [p for p in SITE["pages"] if p.get("parent") == page["wix"]]
    html_out = f"""
<article class="project">
  {back_bar(up_href, up_label)}
  <div class="crumbs">{crumbs}</div>
  <h1 class="project-title">{esc(page['title'])}</h1>
  {body}
  {nav}
</article>"""
    noindex = page.get("noindex") or (page.get("parent") and PAGES[page["parent"]].get("noindex"))
    (ROOT / "projects").mkdir(exist_ok=True)
    (ROOT / "projects" / f"{page['slug']}.html").write_text(
        layout(page["title"], html_out, root, "work", page.get("description", ""), noindex), encoding="utf8")
    return len(subs)


def build_about():
    root = ""
    blocks = WIX["my-cv"]["blocks"]
    body = render_body(blocks, root, {"wix": "my-cv"})
    html_out = f"""
<article class="project about">
  {back_bar(f"{root}index.html", "Home")}
  <h1 class="project-title">About / CV</h1>
  <div class="about-grid">
    <figure class="about-photo"><img src="{root}assets/img/profile.webp" alt="{esc(SITE['fullName'])}" width="737" height="824"></figure>
    <div class="about-body">{body}</div>
  </div>
</article>"""
    (ROOT / "about.html").write_text(layout("About / CV", html_out, root, "about"), encoding="utf8")


def main():
    build_home()
    build_about()
    for p in SITE["pages"]:
        build_project(p)
    print(f"built index.html, about.html and {len(SITE['pages'])} project pages")


if __name__ == "__main__":
    main()
