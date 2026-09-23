# markdown-tools

Python 3.12 project for scraping articles and converting them to Markdown/EPUB.

## Commands

All scripts run via `uv run <script>.py` (uv is the package manager).

| Command | What it does |
|---|---|
| `uv run bulk_get_articles_to_md.py urls.txt` | Download articles from URLs → `md/` |
| `uv run md_to_epub.py md/*.md` | Convert `md/*.md` → `output/*.epub` |
| `uv run urls_to_epub.py <file>.md` | Full pipeline: URLs → fetch → images → EPUB |
| `uv run rss_to_epub.py rss_subs.txt` | RSS feed → SQLite dedup → EPUB |
| `make epub` | `bulk_get_articles_to_md` + `md_to_epub` |
| `make rss` | `rss_to_epub rss_subs.txt` |

## Architecture

- **`article_to_md.py`** — Core scraping engine. Has per-site configs (`OlegConfig`, `TelegramConfig`, `Vas3kConfig`, `HabrConfig`). Adding a new site = subclass `AbstractConfig` and register in `configs` dict.
- **`md_to_epub.py`** — Image caching (shelve) + EPUB generation (ebooklib).
- **`urls_to_epub.py`** — End-to-end: URLs → fetch (async via aiohttp) → images → EPUB.
- **`rss_to_epub.py`** — RSS → SQLite dedup (`rss.sqlite`) → EPUB. Uses `sqlean` (sqlite3 wrapper).

## Site configs

Site detection is by substring match in URL (`article_to_md.py:159`). Each config defines CSS selectors for `title_tag`, `content_tag`, `date_tag`. Custom `get_date()`/`get_html()` overrides available (see `TelegramConfig`).

## Gotchas

- `.gitignore` ignores all `*.html`, `*.epub`, `*.md`, `*.db`, `*.sqlite`, `*.xml`, `*.shelve` — generated artifacts won't show in git status.
- Image cache is a Python `shelve` file (`cache.shelve`). `make clean` deletes it.
- RSS has a 4s interval between fetches (`INTERVAL = 4`). Article bulk fetch also has a delay (`INTERVAL = 4`).
- No tests, no linting, no type checking configured.
