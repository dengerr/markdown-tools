#!/bin/python

import markdown
from pathlib import Path
import sys

import requests
from ebooklib import epub
from bs4 import BeautifulSoup


def md_to_epub(filenames):

    book = epub.EpubBook()
    book.set_title("Название книги")
    book.add_author("Автор")
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
            url = img['src']
            img_name = url.rsplit('/', 1)[-1]
            response = requests.get(url)
            media_type = response.headers['Content-Type']
            img_file_path = f'static/{img_name}'
            img['src'] = img_file_path
            eimg = epub.EpubImage(uid=f'image_{i}_{j}', file_name=img_file_path, media_type=media_type, content=response.content)
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

    epub.write_epub("output.epub", book)


if __name__ == "__main__":
    md_to_epub(sys.argv[1:])

