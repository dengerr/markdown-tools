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

