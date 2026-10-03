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


def layout(title, body, root, active="", description="", noindex=False, hero3d=False):
    meta_robots = '<meta name="robots" content="noindex">' if noindex else ""
    full_title = f"{title} | {SITE['name']}" if title else f"{SITE['name']} | {SITE['role']}"
    nav = "".join(
        f'<a class="pill" href="{root}{href}"{" aria-current=page" if key == active else ""}>{label}</a>'
        for key, href, label in (("work", "index.html#work", "Work"), ("about", "about.html", "About")))
    three = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js" defer></script>\n'
             f'<script src="{root}js/hero3d.js" defer></script>') if hero3d else ""
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
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}css/style.css">
<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">
<script>
  // motion is opt-in: without JS or with reduced motion, everything stays visible
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) document.documentElement.classList.add("motion");
</script>
</head>
<body>
<div class="veil" aria-hidden="true"></div>
<div class="cursor" aria-hidden="true"><span class="cursor-dot"></span><span class="cursor-label"></span></div>
<header class="site-header">
  <a class="logo" href="{root}index.html">{esc(SITE['logo'])}</a>
  <nav>{nav}<a class="pill pill-dark" href="mailto:{esc(SITE['email'])}">Let's talk <i class="dot" aria-hidden="true"></i></a></nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <div class="footer-card">
    <p class="footer-kicker">Have a project in mind?</p>
    <a class="footer-cta" href="mailto:{esc(SITE['email'])}" data-cursor="Email">Let's talk</a>
    <div class="footer-row">
      <a class="footer-mail" href="mailto:{esc(SITE['email'])}">{esc(SITE['email'])}</a>
      <div class="social">{social_links()}</div>
    </div>
    <small>© {SITE['year']} {esc(SITE['fullName'])}</small>
  </div>
</footer>
<div class="lightbox" hidden><button class="lb-close" aria-label="Close">×</button><button class="lb-prev" aria-label="Previous">‹</button><img alt=""><button class="lb-next" aria-label="Next">›</button></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js" defer></script>
{three}
<script src="{root}js/main.js" defer></script>
</body>
</html>
"""


def tag_line(tags):
    return "".join(f"<li>{esc(t)}</li>" for t in tags)


def build_home():
    root = ""
    cards = []
    for c in SITE["home"]:
        page = PAGES.get(c.get("wix"))
        if "video" in c:
            media = (f'<video muted loop playsinline preload="none" data-autoplay poster="{poster_src(c["video"], root)}">'
                     f'<source src="{video_src(c["video"], root)}" type="video/mp4"></video>')
        else:
            media = f'<img src="{img_src(c["image"], root)}" alt="" loading="lazy" decoding="async">'
        info = (f'<div class="card-info"><h2>{esc(c["title"])}</h2>'
                f'<p>{esc(c.get("subtitle", ""))}</p><ul class="tags">{tag_line(c.get("tags", []))}</ul></div>')
        if page:
            href, extra = f"projects/{page['slug']}.html", 'data-cursor="View"'
        else:  # no project page: play the clip in the lightbox
            href, extra = video_src(c["video"], root), 'data-lightbox-video data-cursor="Play"'
        cards.append(f'<a class="card" href="{href}" {extra}><div class="card-media">{media}</div>{info}</a>')
    hero = SITE["hero"]
    statement = SITE.get("statement", SITE["tagline"])
    words = " ".join(f"<span>{esc(w)}</span>" for w in statement.split())
    body = f"""
<section class="hero">
  <canvas class="hero-canvas" aria-hidden="true"></canvas>
  <div class="hero-text">
    <p class="eyebrow"><i class="dot" aria-hidden="true"></i>{esc(SITE['fullName'])} — {esc(SITE['role'])}</p>
    <h1 data-split-words>{esc(SITE['headline'])}</h1>
    <div class="hero-actions">
      <a class="pill pill-dark pill-lg" href="#work">See projects <span aria-hidden="true">↓</span></a>
      <a class="pill pill-lg" href="{video_src(hero['video'], root)}" data-lightbox-video data-cursor="Play">Play reel <span aria-hidden="true">▶</span></a>
    </div>
  </div>
  <p class="scroll-hint" aria-hidden="true">Continue to scroll</p>
</section>
<section class="reel">
  <a class="reel-frame" href="{video_src(hero['video'], root)}" data-lightbox-video data-cursor="Play">
    <video muted loop playsinline preload="none" data-autoplay poster="{poster_src(hero['video'], root)}"><source src="{video_src(hero['video'], root)}" type="video/mp4"></video>
    <span class="reel-label pill">Play reel ▶</span>
  </a>
</section>
<section class="statement"><p data-words>{words}</p></section>
<section id="work" class="work">
  <header class="section-head"><h2 data-split-words>Selected work</h2><span class="count">{len(cards):02d}</span></header>
  <div class="cards">{"".join(cards)}</div>
</section>"""
    (ROOT / "index.html").write_text(layout("", body, root, "work", hero3d=True), encoding="utf8")


def split_hero(blocks):
    """Take the first full-width video/image off the top of the page to use as a full-bleed hero."""
    for i, b in enumerate(blocks):
        if b["type"] in ("text", "button"):
            continue
        if b["type"] in ("video", "image") and (b.get("dispW") or 0) >= FULL_WIDTH and not b.get("link"):
            if b["type"] == "image" and b["uri"].startswith("http"):
                continue
            key = b.get("id") or b.get("uri")
            # drop the hero and later full-width repeats of the same clip
            rest = [o for o in blocks if o is not b and not
                    ((o.get("id") or o.get("uri")) == key and (o.get("dispW") or 0) >= FULL_WIDTH)]
            return b, rest
        return None, blocks
    return None, blocks


def build_project(page):
    root = "../"
    wix = WIX[page["wix"]]
    crumbs = f'<a href="{root}index.html#work">Work</a>'
    if page.get("parent"):
        parent = PAGES[page["parent"]]
        crumbs += f' <span>/</span> <a href="{root}projects/{parent["slug"]}.html">{esc(parent["title"])}</a>'
    hero, blocks = split_hero(wix["blocks"])
    body = render_body(blocks, root, page)
    nav = ""
    order = [p for p in SITE["pages"] if not p.get("parent")]
    if not page.get("parent"):
        k = order.index(page)
        prev_p, next_p = order[k - 1], order[(k + 1) % len(order)]
        nav = (f'<nav class="pager"><a href="{prev_p["slug"]}.html" data-cursor="Prev"><small>Previous</small>{esc(prev_p["title"])}</a>'
               f'<a href="{next_p["slug"]}.html" data-cursor="Next"><small>Next project</small>{esc(next_p["title"])}</a></nav>')
    subs = [p for p in SITE["pages"] if p.get("parent") == page["wix"]]
    head = f'<div class="crumbs">{crumbs}</div><h1 class="project-title" data-split>{esc(page["title"])}</h1>'
    if hero:
        if hero["type"] == "video":
            media = render_video(hero, root, ambient=True)
            watch = (f'<a class="btn btn-ghost" href="{video_src(hero["id"], root)}" data-lightbox-video data-cursor="Play">'
                     f'Watch with sound <span aria-hidden="true">▶</span></a>')
        else:
            media = render_image(hero, root, lightbox=False)
            watch = ""
        top = f'<section class="page-hero"><div class="page-hero-media">{media}</div><div class="page-hero-text">{head}{watch}</div></section>'
    else:
        top = f'<div class="project-head">{head}</div>'
    html_out = f"""
{top}
<article class="project">
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
<div class="project-head"><h1 class="project-title" data-split>About / CV</h1></div>
<article class="project about">
  {body}
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
