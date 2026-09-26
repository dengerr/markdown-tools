# Унификация работы с URL — дизайн

Дата: 2026-09-25

## Проблема

Пять точек входа дублируют разбор входа и запись результата:

| Скрипт | Вход | Что пишет |
|---|---|---|
| `article_to_md.py` | url | `<title>.md` в корень |
| `bulk_get_articles_to_md.py` | `.txt` / `.md` | `md/<title>.md` |
| `urls_to_epub.py` | `.txt` / `.md` / url | `output/*.epub` |
| `rss_to_epub.py` | rss-подписка | `output/*.epub` + `md/<автор> - <title>.md` |
| `md_to_epub.py` | `md/*.md` | `output/*.epub` (имя захардкожено) |

Каталог `html/` наполнен фрагментами, но никто в него не пишет.

Найденные при разведке дефекты:

- `TelegramConfig.get_html` (`article_to_md.py:125`) мёртвый: свойство `html` зовёт модульную
  `get_raw_html(self.url)`, а не хук. `?embed=1&mode=tme` не применяется никогда.
- `select_one(...)` может вернуть `None` — `get_title`/`get_date`/`get_html_content` падают с
  `AttributeError`. Воспроизведено на живых страницах `olegmakarenko.ru` и `vas3k.blog`.
- `OlegConfig.content_tag = '.b-singlepost-bodywrapper'` и `Vas3kConfig.title_tag`/`.date_tag`
  протухли: на живых сайтах таких элементов нет.
- `html` и `md` строятся из разных деревьев: чистка есть только у `UniversalConfig`.
- `asyncio.gather` без `return_exceptions` — одно битое зерно роняет весь запуск.
- `bulk_get_articles_to_md.py:14` теряет порядок урлов (`set`).

## Решение

Один вход → три артефакта: `md/<title>.md`, `html/<title>.html` (очищенный), `output/<автор> - <книга>.epub`.
Старые скрипты остаются рабочими тонкими обёртками.

### Два конвейера

**Путь A — источник в сети**: URL / `.txt` / локальный `.html` / `--urls-list X.md`

```
args → Source[] → fetch → Article[] → md/, html/, output/*.epub
```

**Путь B — готовый контент**: `X.md` без флага

```
X.md → markdown → html/<stem>.html, output/<автор> - <stem>.epub   (сети нет, md уже на месте)
```

### Правила разбора входа

| Вход | Путь | URL | Книга (author, name) |
|---|---|---|---|
| `https://…` | A | сам | (домен, `article.title`) |
| `list.txt` | A | непустые строки; поддерживается `stem = url` как в `rss_subs.txt` | stem файла, split по `' - '`, иначе `unknown` |
| `page.html` | A | `<link rel=canonical>` / `og:url`, иначе пусто | stem файла |
| `--urls-list d.md` | A | http-ссылки в скобках, дедуп с сохранением порядка | stem файла |
| `a.md` | B | — | (домен из строки `[url](url)`, иначе `unknown`), name = stem |

### Группировка в книги

- URL / `.txt` / `.html`: **каждый аргумент — своя книга** (как сейчас в `urls_to_epub.py`)
- `.md`-контент: **все аргументы — одна книга** (как сейчас в `md_to_epub.py md/*.md`, иначе
  `make epub` собрал бы 974 книги). `--split` отменяет.

### Флаги

`--urls-list` · `--no-md` · `--no-html` · `--no-epub` · `--sync` · `--split` ·
`--concurrency N` (5) · `--interval N` · `--author` · `--name`

## Модули

### `article_to_md.py` (правки)

- `clean_for_reading(tag)` — общая чистка, применяется и к `md`, и к `html`:
  удаление `script, style, noscript, form, button, input, iframe, ins, svg, canvas`,
  узлов `Comment`/`Doctype`/`ProcessingInstruction` (убирает react-артефакты `<!--[-->`),
  негативный фильтр мусорных классов **до** срезания атрибутов, разворот опустевших
  `<div>`/`<span>`. Белый список атрибутов: `src, alt, href, title, id, width, height,
  colspan, rowspan, datetime, lang, dir, start, type, rel, target`. `srcset`/`sizes`/
  `data-*`/`class`/`style` отбрасываются — в локальном файле они бессмысленны.
- `AbstractConfig.drop_selectors = ()` — site-specific мусор, применяется в общей точке
  выборки контента.
- Семантический и эвристический поиск переезжает из `UniversalConfig` в модульные функции
  и становится **запасным путём** для любого конфига: битый селектор даёт пустую строку,
  а не падение. `UniversalConfig` остаётся как «ничего не настроено».
- `get_fetch_url()` — единственная точка расширения для сайта, которой пользуется слой
  загрузки; `TelegramConfig` переопределяет её. Старый `get_html(url)` удалён как дубль.
- `sanitize_filename()` — замена только разделителей пути (`/ \`) и управляющих символов на
  `-`. `:` и `?` **сохраняются**: в `md/` уже лежат файлы с ними, и менять имена
  существующих статей — регресс. Схлопывание пробелов и обрезка до 100 символов по границе
  слова остаются. Применяется в `get_filename`, так что `Article.filename` всегда безопасен
  для записи на диск.
- `build_full_md_content` / `build_full_html_content` не печатают `[](…)` при пустом url.

### `fetch.py`

`fetch_sources(sources, *, sync=False, concurrency=5, interval=0) -> list[Source | None]`

- async: одна `aiohttp.ClientSession`, `Semaphore`, общий rate-limit по `interval`;
  `resp.text()` вместо ручного `.decode('utf8')`
- sync: `requests` + `time.sleep(interval)`
- `TIMEOUT = 30`, `RETRIES = 2` с экспоненциальной паузой
- локальные `.html` / `.md` в сеть не идут
- ошибка на конкретный URL → `None` + `SKIP <url>: <причина>`, остальное продолжается
- получает готовые пары `(url_for_download, Source)` и о конфигах ничего не знает

### `md_to_epub.py` → `Chapter`

```python
@dataclass
class Chapter:
    title: str
    html: str
```

`save_imgs(chapters)` и `html_md_to_epub(chapters, author, name)` принимают только
`list[Chapter]`. Ветки `isinstance(filename, Article)` уходят, конвертация md→html делается
один раз в `pipeline.py`, импорт `Article` из `md_to_epub` исчезает.

### `pipeline.py`

```python
run(args, *, outputs=('md','html','epub'), urls_list=False, split=False,
    sync=False, concurrency=5, interval=0,
    md_dir='md', html_dir='html') -> int
main(argv=None)   # argparse поверх run()
```

`sanitize_filename`, `mkdir(parents=True, exist_ok=True)`, предупреждение `DUP` при
коллизии имён, сводка `готово: N статей, M пропущено`, код возврата 1 если не записан
ни один артефакт.

## Обёртки

| Скрипт | Новое тело |
|---|---|
| `article_to_md.py URL` | `run([url], outputs=['md'], md_dir='.')` |
| `bulk_get_articles_to_md.py f.{txt,md}` | `run(args, outputs=['md'], sync=True, interval=4, urls_list=True)` |
| `urls_to_epub.py f.{txt,md} \| URL` | `run(args, outputs=['epub'], urls_list=True)` — здесь `.md` всегда список URL, иначе старый контракт сломан |
| `md_to_epub.py md/*.md` | одна книга, имя из первого файла, `--author/--name` для переопределения |
| `rss_to_epub.py` | структурно не трогаем, переводим на `Chapter` |

## Тесты

`tests/test_clean.py`, `tests/test_sources.py`, `tests/test_emit.py` — только чистые функции,
без сети. `uv add --dev pytest`.

## Проверка

```
uv run pytest
uv run pipeline.py "https://habr.com/ru/articles/908278/"
uv run pipeline.py --urls-list "urls/habr - 2025-05-16.md"
uv run pipeline.py "urls/tarasenko.txt"
uv run pipeline.py "md/10 забытых гаджетов…md"
uv run bulk_get_articles_to_md.py urls/tarasenko.txt
uv run md_to_epub.py "md/10 забытых гаджетов…md"
```

Регрессия md: снапшоты 4 статей снимаются **до** правок и сравниваются `diff` после
(артефакты в `.gitignore`, в git их не видно).
