#!/usr/bin/python3
import re
import sys
import time
from pathlib import Path

from article_to_md import get_article
from md_to_epub import save_imgs, html_md_to_epub

OUTPUT_DIR = 'md'
HTML_DIR = 'html'
INTERVAL = 4


def urls_to_epub(urls, stem):
    html_filenames = []
    md_filenames = []
    for url in urls:
        print(url, end=' ... ')
        article = get_article(url)
        md_path = f'{OUTPUT_DIR}/{article.filename}.md'
        open(md_path, 'w').write(article.md_content)
        md_filenames.append(md_path)
        html_path = f'{HTML_DIR}/{article.filename}.html'
        open(html_path, 'w').write(article.html_content)
        html_filenames.append(html_path)
        print('success')
        time.sleep(INTERVAL)

    save_imgs(md_filenames)
    if ' - ' in stem:
        author, name = stem.split(' - ')
    else:
        author, name = 'unknown', stem
    html_md_to_epub(html_filenames, author, name)


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

