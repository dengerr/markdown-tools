# markdown-tools

Главная точка входа — `pipeline.py`. На любой вход она отдаёт три файла: `md/`, `html/`
(очищенный, для чтения) и `output/*.epub`.

```bash
uv run pipeline.py https://example.com/article   # одна статья
uv run pipeline.py urls.txt                      # список URL, каждый — отдельная книга
uv run pipeline.py --urls-list digest.md         # .md как список URL
uv run pipeline.py article.md                    # .md как готовый контент, без сети
uv run pipeline.py saved.html                    # локально сохранённая страница, офлайн
```

Что умеет список URL: одна ссылка на строку, скобочный формат из старых файлов
(`[title](url)`) и `имя = url`, чтобы задать своё имя книги. Порядок сохраняется,
дубликаты отбрасываются.

Флаги:

| Флаг | Что делает |
|---|---|
| `--no-md`, `--no-html`, `--no-epub` | не создавать этот файл |
| `--sync` | последовательная загрузка вместо асинхронной (5 запросов сразу) |
| `--interval N` | пауза между запросами, секунды |
| `--author`, `--name` | автор и название книги, если нужно переопределить |
| `--split` | каждый `.md` — отдельная книга (по умолчанию все `.md` в одну) |
| `--urls-list` | трактовать `.md` как список URL, а не как готовый контент |

`urls_to_epub.py` читает список URL, как и раньше, `.md` тоже:

```bash
uv run urls_to_epub.py makarenko-2025-05-25.md
```

Создаст `output/<автор> - makarenko-2025-05-25.epub` с главами по урлам из файла, по порядку.

Старые скрипты на месте и работают: `bulk_get_articles_to_md.py` (только `md/`),
`md_to_epub.py` (только epub), `article_to_md.py` (одна статья в текущий каталог),
`urls_to_epub.py` (только epub).

## TODO

- кеш для статей. Чтобы при повторном запуске не скачивать заново
- асинхронное скачивание картинок
- `vas3k.blog` отдаёт `article:published_time` = дата сборки блога (2018-05-16) для всех
  постов; если это мешает, в `Vas3kConfig` достаточно `def get_date(self): return ''`


## sqlite

При ошибках можно стереть в БД инфу о прочтении и создать epub заново.

```sql
sqlite3 rss.sqlite
SQLite version 3.45.1 2024-01-30 16:01:20
Enter ".help" for usage hints.
sqlite> .tables
articles
sqlite> select count(*) from articles;
519
sqlite> select channel, dt, title from articles;
https://olegmakarenko.ru/data/rss|2025-06-21 08:00:15+00:00|Чернокожий Карлсон
https://olegmakarenko.ru/data/rss|2025-06-21 11:00:15+00:00|Кто виноват в потере данных за 30 лет
...
https://olegmakarenko.ru/data/rss/|2026-01-08 12:00:36+00:00|Где учат на писателей?
https://olegmakarenko.ru/data/rss/|2026-01-09 08:00:43+00:00|Российская Империя — страна возможностей для крестьян
https://olegmakarenko.ru/data/rss/|2026-01-09 12:00:38+00:00|Про семьи и бункеры
https://olegmakarenko.ru/data/rss/|2026-01-10 08:00:06+00:00|Инволюция в Китае, или почему конкуренцию надо ограничивать
https://olegmakarenko.ru/data/rss/|2026-01-10 12:00:25+00:00|Про раздачу бесплатных квартир в России
https://olegmakarenko.ru/data/rss/|2026-01-11 08:00:18+00:00|В традиционном Иране рождаемость ниже, чем в порочной Исландии
sqlite> select channel, dt, title from articles where dt > '2026-01-08 12:00:36+00:00';
https://olegmakarenko.ru/data/rss/|2026-01-09 08:00:43+00:00|Российская Империя — страна возможностей для крестьян
https://olegmakarenko.ru/data/rss/|2026-01-09 12:00:38+00:00|Про семьи и бункеры
https://olegmakarenko.ru/data/rss/|2026-01-10 08:00:06+00:00|Инволюция в Китае, или почему конкуренцию надо ограничивать
https://olegmakarenko.ru/data/rss/|2026-01-10 12:00:25+00:00|Про раздачу бесплатных квартир в России
https://olegmakarenko.ru/data/rss/|2026-01-11 08:00:18+00:00|В традиционном Иране рождаемость ниже, чем в порочной Исландии
sqlite> delete from articles where dt > '2026-01-08 12:00:36+00:00';
```

