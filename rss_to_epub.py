#!/usr/bin/python3
import re
import sys
import time
import requests
import shelve
from subprocess import run, PIPE
from pathlib import Path

from article_to_md import get_article, Article
from md_to_epub import save_imgs, html_md_to_epub
from parsing_rss import parse_rss

OUTPUT_DIR = 'md'
HTML_DIR = 'html'
GUIDS_FILE = 'guids.shelve'
INTERVAL = 4


def rss_to_epub(rss_url, stem):
    content = requests.get(rss_url)
    channel, items = parse_rss(content.content)
    items.sort(key=lambda x: x['pubDate'])
    with shelve.open(GUIDS_FILE) as guids_db:
        items = [item for item in items if item['guid'] not in guids_db]
        guids_db.update({item['guid']: True for item in items})
    if not items:
        return

    articles = []
    for item in items:
        html_content = '\n'.join([
            f'<h1>{item["title"]}</h1>',
            f'<p><a href="{item["link"]}">{item["link"]}</p>',
            item['description'],
        ])
        article = Article(
            raw_html=item['description'],
            success=True,
            error_code='',
            title=item['title'],
            md_content=get_md(item['description']),
            html_content=html_content,
            filename=item['title'],
        )
        articles.append(article)

    save_imgs(articles)
    if ' - ' in stem:
        author, name = stem.split(' - ')
    else:
        author, name = 'unknown', stem
    html_md_to_epub(articles, author, name)


def get_md(html):
    p = run(['html2md', '--in'], stdout=PIPE,
            input=html, encoding='utf8')
    return p.stdout.strip()


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        stem, url = arg.split('=', maxsplit=1)
        rss_to_epub(url, stem)

