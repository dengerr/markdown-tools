#!/bin/python

import shelve
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from ebooklib import epub
from bs4 import BeautifulSoup

CACHE_DIR = './cache'
CACHE_FILE = './cache.shelve'
OUTPUT_DIR = './output'
MD_DIR = './md'
HTML_DIR = './html'


@dataclass
class Chapter:
    """Глава книги: готовый html. Статьи и md-файлы приводятся к нему
    в pipeline.py — здесь только сборка epub и кеш картинок."""
    title: str
    html: str


def save_imgs(chapters):
    with shelve.open(CACHE_FILE) as cache_db:
        for chapter in chapters:
            soup = BeautifulSoup(chapter.html, "html.parser")
            for img in soup.find_all('img'):
                url = img.get('src')
                if not url or url in cache_db:
                    continue
                response = requests.get(url)
                hash = hashlib.sha1(response.content).hexdigest()
                with open(Path(CACHE_DIR) / hash, 'wb') as fp:
                    fp.write(response.content)
                if 'Content-Type' not in response.headers:
                    print('error, not content type')
                    print(response.headers)
                else:
                    cache_db[url] = dict(
                        img_name=str(url).rsplit('/', 1)[-1],
                        media_type=response.headers['Content-Type'],
                        hash=hash,
                    )
                print('.', end='')
    print('all imgs saved')


def html_md_to_epub(chapters, author, name):
    book = epub.EpubBook()
    book.set_title(name)
    book.add_author(author)
    book.set_language("ru")
    spine = []
    toc = []
    img_in_epub = set()

    for i, chapter in enumerate(chapters):
        print(chapter.title)

        soup = BeautifulSoup(chapter.html, "html.parser")
        img_tags = soup.find_all('img')
        with shelve.open(CACHE_FILE) as cache_db:
            for j, img in enumerate(img_tags):
                url = img.get('src')
                if not url:
                    continue
                if cached_img := cache_db.get(url):
                    img_name = cached_img['img_name']
                    img['src'] = f'static/{img_name}'
                    if url in img_in_epub:
                        continue
                    img_in_epub.add(url)
                    media_type = cached_img['media_type']
                    with open(Path(CACHE_DIR) / cached_img['hash'], 'rb') as img_file:
                        content = img_file.read()
                    eimg = epub.EpubImage(uid=f'image_{i}_{j}', file_name=img['src'], media_type=media_type, content=content)
                    book.add_item(eimg)

        chap = epub.EpubHtml(title=chapter.title, file_name=f"chap{i}.xhtml", lang="ru")
        chap.content = str(soup)

        book.add_item(chap)
        spine.append(chap)
        toc.append(chap)
    book.spine = spine
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    epub.write_epub(f"{OUTPUT_DIR}/{author} - {name}.epub", book)


if __name__ == "__main__":
    from pipeline import main

    raise SystemExit(main(sys.argv[1:], outputs=['epub']))
