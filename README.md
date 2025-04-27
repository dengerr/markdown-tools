# markdown-tools

## скачать несколько html статей

1. записать урлы в `urls.txt`
2. `wget -i urls.txt`

## скачать несколько html статей в md

1. записать урлы в `urls.txt`
2. запустить `uv run bulk_get_articles_to_md.py`
3. посмотреть в каталог `md`

## создать epub из md

`uv run md_to_epub.py md/*.md`

