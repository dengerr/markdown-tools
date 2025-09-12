#!/usr/bin/python3
import aiohttp
import asyncio
import re
import sys
import time
from pathlib import Path

from article_to_md import get_article, get_raw_html
from md_to_epub import save_imgs, html_md_to_epub

OUTPUT_DIR = 'md'
HTML_DIR = 'html'
INTERVAL = 2
SYNC = False


async def async_get_raw_html(session, url) -> str:
    async with session.get(url) as resp:
        return await resp.read()


async def async_get_htmls(urls):
    async with aiohttp.ClientSession() as session:
        htmls = await asyncio.gather(*(async_get_raw_html(session, url) for url in urls))
    return htmls


def urls_to_epub(urls, stem):
    articles = []
    htmls = []
    if SYNC:
        for url in urls:
            print(url, end=' ... ')
            html = get_raw_html(url)
            htmls.append(html)
            print('success')
            time.sleep(INTERVAL)
    else:
        htmls = asyncio.run(async_get_htmls(urls))

    for url, html in zip(urls, htmls):
        article = get_article(url, html)
        articles.append(article)

    save_imgs(articles)
    if ' - ' in stem:
        author, name = stem.split(' - ')
    else:
        author, name = 'unknown', stem
    html_md_to_epub(articles, author, name)


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        p = Path(filename)
        urls = []
        match p.suffix:
            case '.md':
                for line in open(p, 'r').readlines():
                    matches = re.findall(r'\((.*?)\)', line)
                    for url in matches:
                        if url and url.startswith('http'):
                            urls.append(url)
                urls_to_epub(urls, p.stem)
            case '.txt':
                for url in open(p, 'r').readlines():
                    urls.append(url)
                urls_to_epub(urls, p.stem)
            case _:
                urls.append(filename)
                urls_to_epub(urls, 'one_url')

