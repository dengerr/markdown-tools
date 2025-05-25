#!/usr/bin/python3
import re
import sys
import time
from pathlib import Path

from article_to_md import get_article
from md_to_epub import save_imgs, md_to_epub

OUTPUT_DIR = 'md'
INTERVAL = 4


def urls_to_epub(urls, stem):
    html_filenames = []
    for url in urls:
        print(url, end=' ... ')
        article = get_article(url)
        path = f'{OUTPUT_DIR}/{article.filename}.md'
        open(path, 'w').write(article.md_content)
        html_filenames.append(path)
        print('success')
        time.sleep(INTERVAL)

    save_imgs(html_filenames)
    if ' - ' in stem:
        author, name = stem.split(' - ')
    else:
        author, name = 'unknown', stem
    md_to_epub(html_filenames, author, name)


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

