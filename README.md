# NAPAT.T Portfolio

Static portfolio site (HTML/CSS/JS, no framework), rebuilt from the old Wix site
and hosted on GitHub Pages.

## Folders

| Path | What |
|---|---|
| `index.html`, `about.html`, `projects/*.html` | Generated pages. Don't edit by hand; edit the data and rebuild. |
| `css/style.css`, `js/main.js` | Design and behavior (lightbox, video autoplay) |
| `assets/img/` | Images (WebP, max 2400px) |
| `assets/video/` | Web-compressed videos |
| `data/site.json` | Name, contact, social links, home card order/titles/tags, page slugs/titles |
| `data/wix_pages.json` | Content of each page (text + media in order), extracted from Wix |
| `media_src/` | Original full-quality videos from Wix. Local only, not uploaded (gitignored). |
| `tools/` | Scripts (below) |

## Common edits

- **Change a card title/tags, reorder projects, change contact links**: edit `data/site.json`, then run `python tools/build.py`
- **Change project text**: edit the `html` of the text block in `data/wix_pages.json`, then rebuild
- **Preview locally**: `python -m http.server 8000`, then open http://localhost:8000
- **Check for broken links**: `python tools/check_links.py`

## Re-importing from Wix (only needed if the Wix site changes)

```
python tools/fetch.py            # download Wix page HTML + JSON into tools/raw/
python tools/scrape.py           # -> data/wix_pages.json
python tools/download_media.py   # -> assets/img/, media_src/
python tools/encode_videos.py    # media_src/ -> assets/video/ (needs ffmpeg)
python tools/build.py            # -> HTML pages
```
