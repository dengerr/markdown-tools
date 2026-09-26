#!/usr/bin/python3

# Скачивание статей и приведение их к md / читаемому html.
#
# usage: article_to_md.py https://url/
# Под каждый сайт подбираются селекторы title, content, date в своём Config.
# Если селектор не нашёлся (сайт поменял вёрстку) — ищем семантически
# (h1/main/article/og:title/time) и эвристически по объёму текста.
# Неизвестные сайты разбирает UniversalConfig — это AbstractConfig без селекторов.
# Нужно было скачать софтину (уже не надо)
# https://github.com/suntong/html2md

import copy
import re
import sys
from dataclasses import dataclass

import pyhtml2md
import requests
from bs4 import BeautifulSoup, Tag, Comment, Doctype, ProcessingInstruction

TAG_TIMEOUT = 30

# На linux опасны только разделители; `:` и `?` оставляем — они есть
# в именах уже скачанных статей (например `Собирали франкенштейна…: ZFS.md`)
UNSAFE_FILENAME_CHARS = re.compile(r'[/\\\x00-\x1f]')
ISO_DATETIME = re.compile(r'^\d{4}-\d{2}-\d{2}T')

DROP_TAGS = (
    'script', 'style', 'noscript', 'form', 'button', 'input', 'select', 'textarea',
    'iframe', 'ins', 'svg', 'canvas',
)
# bs4 4.13 не умеет find_all(Comment): класс уходит в TagNameMatchRule и падает,
# поэтому ищем через isinstance
DROP_NODES = (Comment, Doctype, ProcessingInstruction)
IS_DROP_NODE = lambda node: isinstance(node, DROP_NODES)
# В локальном файле class/style/srcset/data-* ничего не дают, но тащат мусор
KEEP_ATTRS = frozenset((
    'src', 'alt', 'href', 'title', 'id', 'width', 'height', 'colspan', 'rowspan',
    'datetime', 'lang', 'dir', 'start', 'type', 'rel', 'target',
))
# Эти теги имеют смысл и без содержимого
MEANINGFUL_TAGS = ('img', 'br', 'hr', 'table', 'figure', 'video', 'audio', 'source')
UNWRAP_TAGS = ('div', 'span')

POSITIVE_CLASS_TOKENS = (
    'article', 'content', 'post', 'entry', 'text',
    'body', 'main', 'story', 'blog', 'editorial', 'wrapper',
)
NEGATIVE_CLASS_TOKEN_PATTERNS = re.compile(
    r'(sidebar|nav|footer|comment|widget|menu|header|aside|advert|promo|related|share|social|meta|tags|categories|breadcrumb|author|reply|search|subscri|newsletter|rating|vote|wpdiscuz|navigation|pagination|breadcrumbs)',
    re.I,
)


@dataclass
class Article:
    raw_html: str
    success: bool
    error_code: str
    title: str
    md_content: str
    html_content: str
    filename: str


def sanitize_filename(name: str, max_len: int = 100) -> str:
    clean = re.sub(r'\s+', ' ', name).strip()
    clean = UNSAFE_FILENAME_CHARS.sub('-', clean).strip().strip('.')
    if len(clean) > max_len:
        cut = clean[:max_len]
        clean = cut.rsplit(' ', 1)[0] if ' ' in cut else cut
    return clean.strip() or 'article'


def unwrap_empty(clean: Tag) -> Tag:
    changed = True
    while changed:
        changed = False
        for tag in clean.find_all(UNWRAP_TAGS):
            if tag.get_text(strip=True) or tag.find(MEANINGFUL_TAGS):
                continue
            tag.unwrap()
            changed = True
    return clean


def strip_attributes(clean: Tag) -> Tag:
    # find_all не отдаёт сам корень, а у него атрибутов не меньше
    for node in [clean, *clean.find_all(True)]:
        for attr in list(node.attrs):
            if attr not in KEEP_ATTRS:
                del node.attrs[attr]
    return clean


def unwrap_structure(clean: Tag) -> Tag:
    """Фрагмент вставляется в div главы epub, поэтому `<body>`/`<html>` внутри него
    невалидны для XHTML. Содержимое сохраняем: корень переименовываем в div,
    вложенные теги разворачиваем."""
    if clean.name in ('body', 'html'):
        clean.name = 'div'
    for tag in clean.find_all(('body', 'html')):
        tag.unwrap()
    return clean


def clean_for_reading(tag: Tag) -> Tag:
    clean = copy.deepcopy(tag)
    remove = [
        node for node in clean.find_all(True)
        if NEGATIVE_CLASS_TOKEN_PATTERNS.search(
            ' '.join(node.get('class', [])) + ' ' + (node.get('id') or ''))
    ]
    for node in remove:
        node.decompose()
    for node in clean.find_all(string=IS_DROP_NODE):
        node.extract()
    for node in clean.find_all(DROP_TAGS):
        node.decompose()
    return unwrap_empty(unwrap_structure(strip_attributes(clean)))


def build_full_md_content(title, date, url, md_content):
    content_parts = [
        f"# {title}" if title else '',
        str(date),
        f'[{url}]({url})' if url else '',
        str(md_content),
    ]

    return '\n\n'.join(
        part_str for part in content_parts
        if (part_str := part.strip())) + '\n'

def build_full_html_content(title, date, url, html_content):
    html_content_parts = [
        f"<h1>{title}</h1>" if title else '',
        f"<p>{date}</p>" if str(date).strip() else '',
        f"<p><a href='{url}'>{url}</a></p>" if url else '',
        f"<div>{html_content}</div>",
    ]

    return '\n\n'.join(
        part_str for part in html_content_parts
        if (part_str := part.strip())) + '\n'


def get_md(html):
    md = pyhtml2md.convert(str(html))
    return md.strip()


def tag_to_str(tag) -> str:
    """Заголовок и дата — всегда чистый текст: они идут в имя файла, в
    `# ...` и в `<h1>`, где markdown-разметка не нужна."""
    if tag is None:
        return ''
    if tag.name == 'meta':
        val = (tag.get('content') or '').strip()
        return val.split('T')[0] if ISO_DATETIME.match(val) else val
    return re.sub(r'\s+', ' ', tag.get_text(' ', strip=True)).strip()


def find_semantic_title(soup) -> Tag | None:
    return (
        soup.select_one('h1')
        or soup.select_one('meta[property="og:title"]')
        or soup.select_one('title')
    )


def find_semantic_date(soup) -> Tag | None:
    return (
        soup.select_one('time')
        or soup.select_one('meta[property="article:published_time"]')
        or soup.select_one('meta[name="date"]')
    )


def find_semantic_content(soup) -> Tag | None:
    candidates = soup.select('article, main, [role="main"], [role="article"]')
    if candidates:
        return max(candidates, key=lambda el: len(el.get_text(strip=True)))
    return None


def score_element(el: Tag) -> float:
    text = el.get_text(strip=True)
    text_len = len(text)
    if text_len < 100:
        return 0

    p_count = len(el.find_all('p'))
    li_count = len(el.find_all('li'))
    heading_count = len(el.find_all(['h1', 'h2', 'h3', 'h4']))
    img_count = len(el.find_all('img'))
    pre_count = len(el.find_all(['pre', 'code', 'blockquote']))

    links = el.find_all('a')
    link_text_len = sum(len(a.get_text(strip=True)) for a in links)
    link_density = link_text_len / text_len if text_len > 0 else 1
    comma_count = text.count(',') + text.count('.')

    score = text_len * 0.05
    score += p_count * 30
    score += li_count * 15
    score += heading_count * 20
    score += img_count * 10
    score += pre_count * 15
    score += comma_count * 2
    score *= max(0, 1 - link_density * 1.5)

    classes = ' '.join(el.get('class', [])) + ' ' + (el.get('id') or '')
    positive_tokens = [t for t in classes.split() if t in POSITIVE_CLASS_TOKENS]
    score *= 1.2 ** len(positive_tokens)
    negative_tokens = NEGATIVE_CLASS_TOKEN_PATTERNS.findall(classes)
    score *= 0.3 ** len(negative_tokens)

    return score


def find_heuristic_content(soup) -> Tag | None:
    scored = []
    for el in soup.find_all(['div', 'section', 'article', 'main']):
        score = score_element(el)
        if score > 0:
            scored.append((score, el))
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return soup.body

    best_el = scored[0][1]

    for _, el in scored[1:3]:
        try:
            if best_el in el.find_all():
                return el
        except (AttributeError, TypeError):
            pass

    return best_el


def find_content(soup) -> Tag | None:
    semantic = find_semantic_content(soup)
    if semantic is None:
        return find_heuristic_content(soup)
    heuristic = find_heuristic_content(soup)
    if heuristic is None:
        return semantic
    semantic_len = len(semantic.get_text(strip=True))
    heuristic_len = len(heuristic.get_text(strip=True))
    if heuristic_len > semantic_len * 1.5:
        return heuristic
    return semantic


class AbstractConfig:
    title_tag = 'h1'
    content_tag = 'article'
    date_tag = '.dt-published'
    drop_selectors = ()

    @staticmethod
    def fetch_url_for(url: str) -> str:
        """Урл для скачивания, известный до создания конфига. Сеть не трогает,
        поэтому вызывается слоем загрузки до fetch."""
        return url

    def __init__(self, url, html=None):
        self.url = url
        self.raw_html = html
        self.soup = BeautifulSoup(self.html, 'lxml')
        self._content = None

    @property
    def html(self):
        if self.raw_html is None:
            self.raw_html = get_raw_html(self.get_fetch_url())
        return self.raw_html

    def get_fetch_url(self) -> str:
        """Урл, по которому реально качать. Telegram отдаёт текст только в embed-режиме."""
        return self.fetch_url_for(self.url)

    def get_title(self) -> str:
        return tag_to_str(self._find(self.title_tag, find_semantic_title))

    def get_filename(self) -> str:
        return sanitize_filename(self.get_title())

    def get_date(self) -> str:
        return tag_to_str(self._find(self.date_tag, find_semantic_date))

    def get_content(self) -> Tag | None:
        if self._content is None:
            self._content = self._get_content()
        return self._content

    def get_md_content(self) -> str:
        return get_md(self.get_content())

    def get_html_content(self) -> str:
        tag = self.get_content()
        if tag is None:
            print('not content for tag', self.content_tag)
            return ''
        return tag.prettify()

    def _find(self, selector, fallback):
        tag = self.soup.select_one(selector) if selector else None
        return tag if tag is not None else fallback(self.soup)

    def _get_content(self) -> Tag | None:
        tag = self._find(self.content_tag, find_content)
        if tag is None:
            return None
        for selector in self.drop_selectors:
            for node in tag.select(selector):
                node.decompose()
        return clean_for_reading(tag)

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
    content_tag = None
    date_tag = 'time'

    def get_date(self) -> str:
        time = BeautifulSoup(self.html, 'lxml').time
        return tag_to_str(time) if time else super().get_date()


class TelegramConfig(AbstractConfig):
    content_tag = '.tgme_widget_message_text'
    date_tag = 'time'

    @staticmethod
    def fetch_url_for(url: str) -> str:
        return f'{url}{"&" if "?" in url else "?"}embed=1&mode=tme'

    def get_title(self) -> str:
        return ''

    def get_filename(self) -> str:
        url_parts = self.url.split('/')
        *_, name, n = url_parts
        return sanitize_filename(f'{name} {n}')


class Vas3kConfig(AbstractConfig):
    # Заголовок и дата на странице есть только в og:title/метаданных —
    # их находит семантический поиск, объявленный ниже как None.
    title_tag = None
    content_tag = '.post'
    date_tag = None


class HabrConfig(AbstractConfig):
    title_tag = 'h1 > span'
    content_tag = '.article-body'
    date_tag = '.tm-article-datetime-published'

    def get_html_content(self) -> str:
        tag = self.get_content()
        if tag is None:
            print('not content for tag', self.content_tag)
            return ''
        for li in tag.find_all('li'):
            if len(li.contents) == 1 and li.contents[0].name == 'p':
                li.contents[0].name = 'span'
        return tag.prettify()


class UniversalConfig(AbstractConfig):
    """Ничего не настроено: всё через семантический и эвристический поиск."""

    title_tag = None
    content_tag = None
    date_tag = None


configs = {
    'olegmakarenko.ru': OlegConfig,
    't.me': TelegramConfig,
    'vas3k.blog': Vas3kConfig,
    'habr.com': HabrConfig,
}


def get_raw_html(url) -> str:
    response = requests.get(url, timeout=TAG_TIMEOUT)
    return response.text


def get_config(url, html=None) -> AbstractConfig:
    if not url:   # локальный .html без canonical/og:url
        return UniversalConfig('', html)
    for k, v in configs.items():
        if k in url:
            return v(url, html)
    return UniversalConfig(url, html)


def get_fetch_url_for(url) -> str:
    """Урл для скачивания без создания конфига: конфиг в __init__ тянет страницу,
    а слой загрузки решает, когда и как качать."""
    if not url:
        return ''
    for k, v in configs.items():
        if k in url:
            return v.fetch_url_for(url)
    return url


def get_article(url, html=None):
    config = get_config(url, html)
    return config.get_obj()


if __name__ == '__main__':
    from pipeline import main

    main(sys.argv[1:], outputs=['md'], md_dir='.')
