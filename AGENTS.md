# markdown-tools

Python 3.12 project for scraping articles and converting them to Markdown/EPUB.

## Commands

All scripts run via `uv run <script>.py` (uv is the package manager).

Главная точка входа — `pipeline.py`: любой вход даёт три файла (`md/`, `html/`, `output/*.epub`).

| Command | What it does |
|---|---|
| `uv run pipeline.py <url>` | One URL → `md/`, `html/`, `output/<домен> - <заголовок>.epub` |
| `uv run pipeline.py list.txt` | `.txt` with one URL per line (`stem = url` also works) |
| `uv run pipeline.py --urls-list digest.md` | `.md` treated as a list of URLs |
| `uv run pipeline.py article.md` | `.md` treated as ready content → html + epub, no network |
| `uv run pipeline.py saved.html` | Locally saved page, parsed offline |
| `uv run pipeline.py --no-epub <url>` | Skip any of the three outputs (`--no-md`, `--no-html`) |
| `uv run pipeline.py --sync --interval 4 <url>` | Sequential fetch with a pause (default: aiohttp, 5 at a time) |
| `uv run pipeline.py --split a.md b.md` | Each `.md` is its own book (default: all `.md` → one book) |
| `uv run bulk_get_articles_to_md.py urls.txt` | Legacy: only `md/`, sequential, 4s pause |
| `uv run md_to_epub.py md/*.md` | Legacy: one book from all `md/*.md` |
| `uv run urls_to_epub.py <file>.md` | Legacy: only epub |
| `uv run article_to_md.py <url>` | Legacy: only md, into the current directory |
| `uv run rss_to_epub.py rss_subs.txt` | RSS feed → SQLite dedup → EPUB |
| `uv run pytest` | Tests (no network) |
| `make epub` | `pipeline.py urls/*.txt` |
| `make rss` | `rss_to_epub rss_subs.txt` |

## Architecture

Pipeline is three stages; each module knows only its own.

- **`sources.py`** — input parsing: argv → `Job` of `Source`s. No network, no writing.
  Book rules: every url/`.txt`/`.html` argument is its own book, all `.md` content arguments
  form one book (`--split` breaks it), a single URL is named after the article title with the
  site domain as author.
- **`fetch.py`** — downloading. Async (aiohttp + semaphore + rate limit) or `--sync`
  (requests). `RETRIES = 2` on 429/5xx only; 403/404 skip immediately. One bad URL never
  kills the run. Configs stay out of it: the caller passes the URL to download, which may
  differ from the article URL (`t.me` embed).
- **`pipeline.py`** — glues stages: sources → fetch → `Article`/`Chapter` → the three
  outputs. `run()` takes options, `main()` is the argparse wrapper.
- **`article_to_md.py`** — scraping engine. Per-site configs, `clean_for_reading()`,
  `sanitize_filename()`.
- **`md_to_epub.py`** — `Chapter` (title + ready html) → image cache (shelve) → EPUB.
  Takes `list[Chapter]` only; callers convert articles and md files themselves.
- **`rss_to_epub.py`** — RSS → SQLite dedup (`rss.sqlite`) → EPUB. Uses `sqlean`.
  Not part of the URL pipeline, but writes through the same `Chapter` writer.

## Site configs

Site detection is by substring match in URL (`get_config` in `article_to_md.py`). Each config
defines CSS selectors for `title_tag`, `content_tag`, `date_tag`, plus optional
`drop_selectors` (site-specific junk to remove) and `get_fetch_url()` (URL to actually
download).

If a selector matches nothing, it falls back to semantic search (`h1`, `main`, `article`,
`og:title`, `time`) and then to a text-volume heuristic. So a site that changed its markup
yields a worse article, not a crash. Adding a new site = subclass `AbstractConfig`, register
in `configs`; only override selectors if the generic search picks the wrong element.

## Gotchas

- `.gitignore` ignores all `*.html`, `*.epub`, `*.md`, `*.db`, `*.sqlite`, `*.xml`, `*.shelve`
  — generated artifacts won't show in git status. To diff a change in parsing, snapshot files
  outside the repo: artifacts in `md/`/`html/` can't be reviewed with `git diff`.
- Image cache is a Python `shelve` file (`cache.shelve`). `make clean` deletes it.
- bs4 4.13 misroutes `find_all(Comment)` into a tag-name rule and crashes on it — search
  nodes with `find_all(string=lambda n: isinstance(n, ...))`, see `IS_DROP_NODE`.
- `clean_for_reading()` applies a negative-class filter, so anything with `comment`, `meta`,
  `author`, `share`, `tags` in its class/id is removed along with comments and sidebars. A
  site that needs such a block back must survive with `drop_selectors`-inverse handling.
- Filenames keep `:` and `?` (they exist in already-downloaded articles); only `/` and `\`
  are replaced.
- RSS-фиды обходятся подряд, без паузы (раньше был `INTERVAL = 4`, но он не
  использовался). Если фидов много — добавь `time.sleep` в цикл в `__main__`.
- `rss_to_epub.py` не имеет argparse: аргументы вида `stem=url` или файл `.txt` с
  такими строками. `--help` не работает, это не баг.
- Images are still downloaded synchronously inside `save_imgs`.
