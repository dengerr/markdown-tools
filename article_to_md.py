#!/usr/bin/python3

# использование article_to_md.py https://url/
# Надо немного поднастроить под каждый сайт:
# jQuery селекторы для title, content, date.
# Нужно скачать софтину
# https://github.com/suntong/html2md

from dataclasses import dataclass
import sys
import requests
from subprocess import run, PIPE

from bs4 import BeautifulSoup


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

    def __init__(self, url):
        self.url = url
        self.raw_html = self.get_html(url)
        self.soup = BeautifulSoup(self.raw_html, 'lxml')

    def get_html(self, url):
        return get_raw_html(url)

    def get_title(self) -> str:
        return get_md(self.raw_html, self.title_tag)

    def get_filename(self) -> str:
        return self.get_title()

    def get_date(self) -> str:
        return get_md(self.raw_html, self.date_tag)

    def get_md_content(self) -> str:
        return get_md(self.raw_html, self.content_tag)

    def get_html_content(self) -> str:
        return self.soup.select_one(self.content_tag).prettify()

    def get_obj(self) -> str:
        title = self.get_title()
        date = self.get_date()

        content_parts = [
            f"# {title}" if title else '',
            date,
            f'[{self.url}]({self.url})',
            self.get_md_content(),
        ]

        md_content = '\n\n'.join(
            part_str for part in content_parts if (part_str := part.strip()))

        html_content_parts = [
            f"<h1>{title}</h1>" if title else '',
            f"<p>{date}</p>",
            f"<p><a href='{self.url}'>{self.url}</a></p>",
            f"<div>{self.get_html_content()}</div>",
        ]

        html_content = '\n\n'.join(
            part_str for part in html_content_parts if (part_str := part.strip()))

        return Article(
            raw_html=self.raw_html,
            success=True,
            error_code='',
            title=title,
            md_content=md_content,
            html_content=html_content,
            filename=self.get_filename(),
        )


class OlegConfig(AbstractConfig):
    content_tag = '.b-singlepost-bodywrapper'

    def get_date(self) -> str:
        return BeautifulSoup(self.raw_html, 'lxml').time.text


class TelegramConfig(AbstractConfig):
    content_tag = '.tgme_widget_message_text'
    date_tag = 'time'

    def get_html(self, url):
        url = f'{url}?embed=1&mode=tme'
        return get_raw_html(url)

    def get_title(self) -> str:
        return ''
        content = get_md(self.raw_html, self.content_tag)
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
    title_tag = 'h1'
    content_tag = '.tm-article-body'
    date_tag = '.tm-article-datetime-published'


configs = {
    'olegmakarenko.ru': OlegConfig,
    't.me': TelegramConfig,
    'vas3k.blog': Vas3kConfig,
    'habr.com': HabrConfig,
}


def get_raw_html(url) -> str:
    response = requests.get(url)
    return response.content.decode('utf8')


def get_md(html, tag):
    p = run(['html2md', '--in', '-s', tag], stdout=PIPE,
            input=html, encoding='utf8')
    return p.stdout.strip()


def get_config(url) -> AbstractConfig:
    for k, v in configs.items():
        if k in url:
            return v(url)
    raise RuntimeError('config not found')


def get_article(url):
    config = get_config(url)
    return config.get_obj()

    title = config.get_title()
    content = config.get_content()
    date = config.get_date()

    content_parts = [
        f"# {title}" if title else '',
        date,
        url,
        content,
    ]

    md_content = '\n\n'.join(
        part_str for part in content_parts if (part_str := part.strip()))

    return Article(
        raw_html=raw_html,
        success=True,
        error_code='',
        title=title,
        md_content=md_content,
        filename=config.get_filename(),
    )


if __name__ == '__main__':
    article = get_article(sys.argv[1])
    open(f'{article.filename}.md', 'w').write(article.md_content)
