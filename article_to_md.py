#!/usr/bin/python3

# использование article_to_md.py https://url/
# Надо немного поднастроить под каждый сайт:
# jQuery селекторы для title, content, date.
# Нужно скачать софтину (уже не надо)
# https://github.com/suntong/html2md

import sys
from dataclasses import dataclass
from subprocess import run, PIPE

import pyhtml2md
import requests
from bs4 import BeautifulSoup


def build_full_md_content(title, date, url, md_content):
    content_parts = [
        f"# {title}" if title else '',
        str(date),
        f'[{url}]({url})',
        str(md_content),
    ]

    return '\n\n'.join(
        part_str for part in content_parts
        if (part_str := part.strip())) + '\n'

def build_full_html_content(title, date, url, html_content):
    html_content_parts = [
        f"<h1>{title}</h1>" if title else '',
        f"<p>{date}</p>",
        f"<p><a href='{url}'>{url}</a></p>",
        f"<div>{html_content}</div>",
    ]

    return '\n\n'.join(
        part_str for part in html_content_parts
        if (part_str := part.strip())) + '\n'


@dataclass
class Article:
    raw_html: str
    success: bool
    error_code: str
    title: str
    md_content: str
    html_content: str
    filename: str


class AbstractConfig:
    title_tag = 'h1'
    content_tag = 'article'
    date_tag = '.dt-published'

    def __init__(self, url, html=None):
        self.url = url
        self.raw_html = html
        self.soup = BeautifulSoup(self.html, 'lxml')

    @property
    def html(self):
        if self.raw_html is None:
            self.raw_html = get_raw_html(self.url)
        return self.raw_html

    def get_html(self, url):
        return get_raw_html(url)

    def get_title(self) -> str:
        html = self.soup.select_one(self.title_tag)
        return get_md(html)

    def get_filename(self) -> str:
        return self.get_title()

    def get_date(self) -> str:
        html = self.soup.select_one(self.date_tag)
        return get_md(html)

    def get_md_content(self) -> str:
        html = self.soup.select_one(self.content_tag)
        return get_md(html)

    def get_html_content(self) -> str:
        html = self.soup.select_one(self.content_tag).prettify()
        if not html:
            print('not content for tag', self.content_tag)
        return html

    def get_obj(self) -> Article:
        title = self.get_title()
        date = self.get_date()

        full_md_content = build_full_md_content(title, date, self.url, self.get_md_content())
        full_html_content = build_full_html_content(title, date, self.url, self.get_html_content())

        return Article(
            raw_html=self.html,
            success=True,
            error_code='',
            title=title,
            md_content=full_md_content,
            html_content=full_html_content,
            filename=self.get_filename(),
        )


class OlegConfig(AbstractConfig):
    content_tag = '.b-singlepost-bodywrapper'

    def get_date(self) -> str:
        return BeautifulSoup(self.html, 'lxml').time.text


class TelegramConfig(AbstractConfig):
    content_tag = '.tgme_widget_message_text'
    date_tag = 'time'

    def get_html(self, url):
        url = f'{url}?embed=1&mode=tme'
        return get_raw_html(url)

    def get_title(self) -> str:
        return ''
        content = get_md(self.html, self.content_tag)
        return content[:50]

    def get_filename(self) -> str:
        url_parts = self.url.split('/')
        *_, name, n = url_parts
        return f'{name} {n}'


class Vas3kConfig(AbstractConfig):
    title_tag = '.simple-headline-title'
    content_tag = '.post'
    date_tag = '.simple-headline-date'


class HabrConfig(AbstractConfig):
    title_tag = 'h1 > span'
    content_tag = '.article-body'
    date_tag = '.tm-article-datetime-published'

    def get_html_content(self) -> str:
        html = self.soup.select_one(self.content_tag)
        if not html:
            print('not content for tag', self.content_tag)
        for li in html.find_all('li'):
            if len(li.contents) == 1 and li.contents[0].name == 'p':
                li.contents[0].name = 'span'
        return html.prettify()


configs = {
    'olegmakarenko.ru': OlegConfig,
    't.me': TelegramConfig,
    'vas3k.blog': Vas3kConfig,
    'habr.com': HabrConfig,
}


def get_raw_html(url) -> str:
    response = requests.get(url)
    return response.content.decode('utf8')


def get_md(html):
    md = pyhtml2md.convert(str(html))
    return md.strip()
    p = run(['html2md'], stdout=PIPE,
            input=html, encoding='utf8')
    return p.stdout.strip()


def get_config(url, html=None) -> AbstractConfig:
    for k, v in configs.items():
        if k in url:
            return v(url, html)
    raise RuntimeError('config not found')


def get_article(url, html=None):
    config = get_config(url, html)
    return config.get_obj()

    title = config.get_title()
    content = config.get_content()
    date = config.get_date()

    full_md_content = build_full_md_content(title, date, url, content)

    return Article(
        raw_html=content,
        success=True,
        error_code='',
        title=title,
        md_content=full_md_content,
        filename=config.get_filename(),
    )


if __name__ == '__main__':
    article = get_article(sys.argv[1])
    open(f'{article.filename}.md', 'w').write(article.md_content)
