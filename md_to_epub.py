#!/bin/python

import markdown
from pathlib import Path
import sys
import shelve
import hashlib

import requests
from ebooklib import epub
from bs4 import BeautifulSoup

CACHE_DIR = './cache'
CACHE_FILE = './cache.shelve'


def save_imgs(filenames):
    with shelve.open(CACHE_FILE) as cache_db:
        for filename in filenames:
            with open(filename, 'r') as f:
                body = markdown.markdown(f.read())
            soup = BeautifulSoup(body, "html.parser")
            img_tags = soup.find_all('img')
            for img in img_tags:
                url = img['src']
                if url in cache_db:
                    continue
                response = requests.get(url)
                hash = str(hashlib.sha1(response.content))
                with open(Path(CACHE_DIR) / hash, 'wb') as fp:
                    fp.write(response.content)
                cache_db[url] = dict(
                    img_name=str(url).rsplit('/', 1)[-1],
                    media_type=response.headers['Content-Type'],
                    hash=hash,
                )
                print('.', end='')
    print('all imgs saved')


def md_to_epub(filenames, name):
    author = "habr"

    book = epub.EpubBook()
    book.set_title(name)
    book.add_author(author)
    book.set_language("ru")
    chapters = ['nav']
    toc = []

    for i, filename in enumerate(filenames):
        with open(filename, 'r') as f:
            body = markdown.markdown(f.read())
        title = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        print(title)

        soup = BeautifulSoup(body, "html.parser")
        img_tags = soup.find_all('img')
        for j, img in enumerate(img_tags):
            with shelve.open(CACHE_FILE) as cache_db:
                if cached_img := cache_db.get(img['src']):
                    img_name = cached_img['img_name']
                    media_type = cached_img['media_type']
                    img_file_path = f'static/{img_name}'
                    img['src'] = img_file_path
                    with open(Path(CACHE_DIR) / cached_img['hash'], 'rb') as img_file:
                        content = img_file.read()
                    eimg = epub.EpubImage(uid=f'image_{i}_{j}', file_name=img_file_path, media_type=media_type, content=content)
                    book.add_item(eimg)

        chapter = epub.EpubHtml(title=title, file_name=f"chap{i}.xhtml", lang="ru")
        chapter.content = str(soup)

        book.add_item(chapter)
        chapters.append(chapter)
        toc.append(chapter)
    book.spine = chapters
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(f"{author} - {name}.epub", book)


if __name__ == "__main__":
    filenames = sys.argv[1:]
    save_imgs(filenames)
    base_name = "2025-04-25"
    md_to_epub(filenames, base_name)

