#!/usr/bin/python3
import re
import sys
import time
from pathlib import Path

from article_to_md import get_article

OUTPUT_DIR = 'md'
INTERVAL = 4


if __name__ == '__main__':
    urls = set()
    for filename in sys.argv[1:]:
        p = Path(filename)
        match p.suffix:
            case '.md':
                for line in open(p, 'r').readlines():
                    matches = re.findall(r'\((.*?)\)', line)
                    for url in matches:
                        urls.add(url)
            case '.txt':
                for url in open(p, 'r').readlines():
                    urls.add(url)
    for url in urls:
        print('begin', url, end=' ... ')
        article = get_article(url)
        open(f'{OUTPUT_DIR}/{article.filename}.md', 'w').write(article.md_content)
        print('success')
        time.sleep(INTERVAL)
