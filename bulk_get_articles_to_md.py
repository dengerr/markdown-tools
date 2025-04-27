#!/usr/bin/python3
import time

from article_to_md import get_article

OUTPUT_DIR = 'md'


if __name__ == '__main__':
    for url in open('urls.txt', 'r').readlines():
        article = get_article(url)
        open(f'{OUTPUT_DIR}/{article.filename}.md', 'w').write(article.md_content)
        print('success', url)
        time.sleep(5)

