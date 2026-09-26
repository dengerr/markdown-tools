#!/usr/bin/python3

# Разбор входа: url / .txt / .html / .md --urls-list / .md (контент) -> Job

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from article_to_md import sanitize_filename

LINK = re.compile(r'\((.*?)\)')
DEFAULT_AUTHOR = 'unknown'
CONTENT_SUFFIXES = ('.md', '.markdown')


@dataclass
class Source:
    kind: str            # 'url' | 'html' | 'md'
    url: str | None = None
    html: str | None = None      # kind='html' — уже с диска
    md_path: Path | None = None  # kind='md'
    title: str = ''


@dataclass
class Job:
    sources: list[Source] = field(default_factory=list)
    author: str = DEFAULT_AUTHOR
    name: str = ''
    split: bool = False    # каждый источник — своя книга
    dynamic_name: bool = False  # имя книги узнаём после парсинга (один url)

    @property
    def is_md_content(self) -> bool:
        return bool(self.sources) and self.sources[0].kind == 'md'


def book_from_stem(stem: str) -> tuple[str, str]:
    """`Oleg - 2025-05-25` -> ('Oleg', '2025-05-25'). Без разделителя автор неизвестен
    на этом шаге: его возьмёт домен первого источника."""
    if ' - ' in stem:
        author, name = stem.split(' - ', maxsplit=1)
        return author.strip(), name.strip()
    return '', stem.strip()


def domain(url: str | None) -> str:
    return urlparse(url).netloc if url else ''


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding='utf8').splitlines() if line.strip()]


def urls_from_txt(path: Path) -> list[str]:
    """Строки вида `url` либо `stem=url` (как в rss_subs.txt). Разделитель — первый `=`,
    но только если справа действительно url: иначе `?a=b` в адресе съел бы адрес."""
    urls = []
    for line in read_lines(path):
        stem, _, rest = line.partition('=')
        url = rest.strip() if rest.strip().startswith('http') else line
        if url.startswith('http') and url not in urls:
            urls.append(url)
    return urls


def urls_from_md(path: Path) -> list[str]:
    """Ссылки из md-файла. Порядок сохраняется, дубли отбрасываются."""
    urls = []
    for match in LINK.findall(path.read_text(encoding='utf8')):
        url = match.strip()
        if url.startswith('http') and url not in urls:
            urls.append(url)
    return urls


def find_in_html(html: str, *selectors) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'lxml')
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag is None:
            continue
        # canonical — это link[href], og:url — это meta[content]
        for attr in ('href', 'content'):
            value = tag.get(attr)
            if value and value.strip():
                return value.strip()
    return ''


def first_url_in_md(path: Path) -> str:
    urls = urls_from_md(path)
    return urls[0] if urls else ''


def md_title(path: Path) -> str:
    for line in read_lines(path):
        if line.startswith('# '):
            return line[2:].strip()
    return path.stem


def source_from_html_file(path: Path) -> Source:
    html = path.read_text(encoding='utf8', errors='replace')
    url = find_in_html(html, 'link[rel=canonical]', 'meta[property="og:url"]')
    return Source(kind='html', url=url or None, html=html)


def source_from_md_file(path: Path) -> Source:
    return Source(kind='md', url=first_url_in_md(path) or None, md_path=path, title=md_title(path))


def job_from_path(path: Path, *, urls_list: bool, split: bool) -> Job:
    stem = path.stem
    author, name = book_from_stem(stem)
    suffix = path.suffix.lower()

    if suffix == '.txt':
        sources = [Source(kind='url', url=url) for url in urls_from_txt(path)]
    elif suffix in CONTENT_SUFFIXES and not urls_list:
        sources = [source_from_md_file(path)]
    elif suffix in CONTENT_SUFFIXES:
        sources = [Source(kind='url', url=url) for url in urls_from_md(path)]
    elif suffix in ('.html', '.htm'):
        sources = [source_from_html_file(path)]
    else:
        raise ValueError(f'неизвестный формат: {path}')

    if not author:
        author = next((domain(s.url) for s in sources if s.url), '') or DEFAULT_AUTHOR
    return Job(sources=sources, author=author, name=name, split=split)


def job_from_url(url: str) -> Job:
    # имя книги узнаем только после парсинга статьи, поэтому dynamic_name
    return Job(sources=[Source(kind='url', url=url)], author=domain(url), dynamic_name=True)


def job_for_arg(arg: str, *, urls_list: bool, split: bool) -> Job:
    if arg.startswith('http'):
        return job_from_url(arg)
    path = Path(arg)
    if not path.exists():
        raise FileNotFoundError(f'нет такого файла: {path}')
    return job_from_path(path, urls_list=urls_list, split=split)


def parse_args(args, *, urls_list: bool = False, split: bool = False) -> list[Job]:
    """Каждый url/.txt/.html — своя книга. Все .md-контент — одна книга
    (иначе `make epub` собрал бы 974 книги); --split отменяет."""
    jobs: list[Job] = []
    for arg in args:
        job = job_for_arg(arg, urls_list=urls_list, split=split)
        if job.is_md_content and not split and jobs and jobs[-1].is_md_content:
            jobs[-1].sources.extend(job.sources)
        else:
            jobs.append(job)
    return jobs


def book_name(job: Job, first_article) -> tuple[str, str]:
    """Для одиночного урла имя книги — заголовок первой статьи."""
    if job.dynamic_name and first_article is not None:
        return job.author, sanitize_filename(first_article.title)
    return job.author, job.name
