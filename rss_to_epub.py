#!/usr/bin/python3
import asyncio
import datetime
import sys
from subprocess import run, PIPE

import aiohttp
import pyhtml2md
import requests
import sqlean as sqlite3
from aiohttp import http

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


TIMEOUT = aiohttp.ClientTimeout(total=40, sock_connect=5)


async def bulk_rss_to_epub(params):
    coros = []
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for url, stem in params:
            coros.append(rss_to_epub(session, url.strip(), stem.strip()))
        await asyncio.gather(*coros)


async def rss_to_epub(session: aiohttp.ClientSession, rss_url: str, stem: str):
    if DEBUG:
        with open('oleg.rss.xml') as fp:
            content = fp.read()
    else:
        try:
            print('connect to', rss_url)
            async with session.get(rss_url, headers={'UserAgent': 'aiohttp'}) as resp:
                print('hey', rss_url)
                content = await resp.read()
        except aiohttp.client_exceptions.ClientError as exc:
            print(str(exc))
            return
        except asyncio.TimeoutError as exc:
            print(rss_url, 'timeout error', str(exc))
            return
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
    params = []
    for arg in sys.argv[1:]:
        if arg.endswith('.txt'):
            with open(arg, 'r') as fp:
                for line in fp.readlines():
                    if line:
                        stem1, url = line.split('=', maxsplit=1)
                        stem = f'{stem1} - {now.strftime("%Y-%m-%d-%H-%M")}'
                        params.append((url, stem))
        else:
            stem, url = arg.split('=', maxsplit=1)
            params.append((url, stem))
    asyncio.run(bulk_rss_to_epub(params))
