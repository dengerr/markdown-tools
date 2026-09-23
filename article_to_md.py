#!/usr/bin/python3

# использование article_to_md.py https://url/
# Надо немного поднастроить под каждый сайт:
# jQuery селекторы для title, content, date.
# Нужно скачать софтину (уже не надо)
# https://github.com/suntong/html2md

import copy
import re
import sys
from dataclasses import dataclass
from subprocess import run, PIPE

import pyhtml2md
import requests
from bs4 import BeautifulSoup, Tag


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


POSITIVE_CLASS_TOKENS = (
    'article', 'content', 'post', 'entry', 'text',
    'body', 'main', 'story', 'blog', 'editorial', 'wrapper',
)
NEGATIVE_CLASS_TOKEN_PATTERNS = re.compile(
    r'(sidebar|nav|footer|comment|widget|menu|header|aside|advert|promo|related|share|social|meta|tags|categories|breadcrumb|author|reply|search|subscri|newsletter|rating|vote|wpdiscuz|navigation|pagination|breadcrumbs)',
    re.I,
)


class UniversalConfig(AbstractConfig):
    title_tag = None
    content_tag = None
    date_tag = None

    def _find_semantic_content(self):
        candidates = self.soup.select('article, main, [role="main"], [role="article"]')
        if candidates:
            return max(candidates, key=lambda el: len(el.get_text(strip=True)))
        return None

    def _find_semantic_title(self):
        h1 = self.soup.select_one('h1')
        if h1:
            return h1
        og = self.soup.select_one('meta[property="og:title"]')
        if og and og.get('content'):
            return og
        title_tag = self.soup.select_one('title')
        return title_tag

    def _find_semantic_date(self):
        time_tag = self.soup.select_one('time')
        if time_tag:
            return time_tag
        meta_date = self.soup.select_one('meta[property="article:published_time"]')
        if meta_date:
            return meta_date
        return self.soup.select_one('meta[name="date"]')

    def _score_element(self, el: Tag) -> float:
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

        classes = ' '.join(el.get('class', [])) + ' ' + el.get('id', '')
        positive_tokens = [t for t in classes.split() if t in POSITIVE_CLASS_TOKENS]
        score *= 1.2 ** len(positive_tokens)
        negative_tokens = NEGATIVE_CLASS_TOKEN_PATTERNS.findall(classes)
        score *= 0.3 ** len(negative_tokens)

        return score

    def _find_heuristic_content(self):
        scored = []
        for el in self.soup.find_all(['div', 'section', 'article', 'main']):
            score = self._score_element(el)
            if score > 0:
                scored.append((score, el))
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return self.soup.body

        best_el = scored[0][1]

        for _, el in scored[1:3]:
            try:
                if best_el in el.find_all():
                    return el
            except (AttributeError, TypeError):
                pass

        return best_el

    def _clean_content(self, el: Tag) -> Tag:
        clean = copy.deepcopy(el)
        for tag in clean.find_all(
            ['nav', 'footer', 'aside', 'script', 'style', 'noscript', 'iframe', 'form']
        ):
            tag.decompose()
        remove = []
        for tag in clean.find_all(True):
            classes = tag.get('class') or []
            if any(NEGATIVE_CLASS_TOKEN_PATTERNS.search(c) for c in classes):
                remove.append(tag)
        for tag in remove:
            tag.decompose()
        return clean

    def get_title(self) -> str:
        el = self._find_semantic_title()
        if el is None:
            return ''
        if el.name == 'meta':
            return el.get('content', '')
        if el.name == 'h1' or el.name == 'title':
            return el.get_text(strip=True)
        return get_md(el)

    def get_date(self) -> str:
        el = self._find_semantic_date()
        if el is None:
            return ''
        if el.name == 'meta':
            val = el.get('content', '')
            if val:
                return val.split('T')[0]
            return ''
        return get_md(el)

    def get_filename(self) -> str:
        title = self.get_title()
        if not title:
            return 'article'
        clean = re.sub(r'[^\w\s-]', '', title)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:100]

    def get_md_content(self) -> str:
        el = self._find_semantic_content()
        if el is None:
            el = self._find_heuristic_content()
        else:
            heuristic = self._find_heuristic_content()
            semantic_text = len(el.get_text(strip=True))
            heuristic_text = len(heuristic.get_text(strip=True))
            if heuristic_text > semantic_text * 1.5:
                el = heuristic
        el = self._clean_content(el)
        return get_md(el)

    def get_html_content(self) -> str:
        el = self._find_semantic_content()
        if el is None:
            el = self._find_heuristic_content()
        el = self._clean_content(el)
        html = el.prettify()
        if not html:
            print('universal config: no content found')
        return html


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
    return UniversalConfig(url, html)


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
