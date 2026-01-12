# markdown-tools

## скачать несколько html статей

1. записать урлы в `urls.txt`
2. `wget -i urls.txt`

## скачать несколько html статей в md

1. записать урлы в `urls.txt`
2. запустить `uv run bulk_get_articles_to_md.py urls.txt`
3. посмотреть в каталог `md`

Если файл будет не .txt, а .md, то берется из каждой строки значение в круглых скобках.
Подготовить такой файл можно из .md через grep.

## создать epub из md

`uv run md_to_epub.py md/*.md`

## полный цикл

`uv run urls_to_epub.py makarenko-2025-05-25.md`

Создаст файл makarenko-2025-05-25.epub с урлами из txt или md файла, по порядку.

## TODO

- кеш для статей. Чтобы при повторном запуске не скачивать заново
- асинхронное скачивание картинок

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

