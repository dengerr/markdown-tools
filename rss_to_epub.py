#!/usr/bin/python3
import datetime
import sys
from subprocess import run, PIPE

import pyhtml2md
import requests
import sqlean as sqlite3

from article_to_md import Article, build_full_md_content, build_full_html_content
from md_to_epub import save_imgs, html_md_to_epub
from parsing_rss import parse_rss

OUTPUT_DIR = 'md'
HTML_DIR = 'html'
GUIDS_FILE = 'guids.shelve'
INTERVAL = 4
DEBUG = 0


def init_sqlite():
    conn = sqlite3.connect("rss.sqlite")
    conn.row_factory = sqlite3.Row
    conn.execute("create table if not exists articles (channel, guid, dt, title, raw_html)")
    return conn


def rss_to_epub(rss_url, stem):
    if DEBUG:
        with open('oleg.rss.xml') as fp:
            content = fp.read()
    else:
        content = requests.get(rss_url).content
    channel, items = parse_rss(content)
    items.sort(key=lambda x: x['pubDate'])
    if not items:
        return

    articles = []
    conn = init_sqlite()
    cursor = conn.cursor()

    for item in items:
        cursor.execute('select 1 from articles WHERE guid = ?;', (item['guid'],))
        exists = cursor.fetchone()
        if exists:
            continue

        insert_query = (
            "insert into articles "
            "(channel, guid, dt, title, raw_html) "
            "values (?, ?, ?, ?, ?)"
        )
        cur = conn.execute(insert_query, (
            rss_url, item['guid'], item['pubDate'], item['title'], item['description'],
        ))

        title = item['title']
        date = item["pubDate"].date()
        url = item["link"]
        full_html_content = build_full_html_content(title, date, url, item['description'])
        full_md_content = build_full_md_content(title, date, url, get_md(item['description']))
        article = Article(
            raw_html=item['description'],
            success=True,
            error_code='',
            title=item['title'],
            md_content=full_md_content,
            html_content=full_html_content,
            filename=item['title'],
        )
        articles.append(article)

    conn.commit()
    conn.close()

    if not articles:
        return

    save_imgs(articles)
    if ' - ' in stem:
        author, name = stem.split(' - ')
    else:
        author, name = 'unknown', stem
    html_md_to_epub(articles, author, name)

    # save to md file
    for article in articles:
        open(f'md/{author} - {article.filename}.md', 'w').write(article.md_content)


def get_md(html):
    md = pyhtml2md.convert(str(html))
    return md.strip()
    p = run(['html2md', '--in'], stdout=PIPE,
            input=html, encoding='utf8')
    return p.stdout.strip()


if __name__ == '__main__':
    now = datetime.datetime.now()
    for arg in sys.argv[1:]:
        if arg.endswith('.txt'):
            with open(arg, 'r') as fp:
                for line in fp.readlines():
                    if line:
                        stem1, url = line.split('=', maxsplit=1)
                        stem = f'{stem1} - {now.strftime("%Y-%m-%d-%H-%M")}'
                        rss_to_epub(url.strip(), stem.strip())
        else:
            stem, url = arg.split('=', maxsplit=1)
            rss_to_epub(url.strip(), stem.strip())
