#!/usr/bin/python3

# Единый вход: url / .txt / .html / --urls-list .md / .md
#   -> md/<title>.md + html/<title>.html + output/<автор> - <книга>.epub

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import markdown

from article_to_md import get_article, sanitize_filename
from fetch import fetch_sources
from md_to_epub import Chapter, html_md_to_epub, save_imgs
from sources import Job, book_name, parse_args

MD_DIR = 'md'
HTML_DIR = 'html'
ALL_OUTPUTS = ('md', 'html', 'epub')


def chapter_from_article(article) -> Chapter:
    return Chapter(title=article.title, html=article.html_content)


def chapter_from_md(source) -> Chapter:
    text = source.md_path.read_text(encoding='utf8')
    return Chapter(title=source.title, html=markdown.markdown(text))


def write_text(path: Path, text: str) -> None:
    if path.exists():
        print(f'DUP {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf8')


def write_md(article, md_dir: str) -> None:
    write_text(Path(md_dir) / f'{article.filename}.md', article.md_content)


def write_html(chapter: Chapter, name: str, html_dir: str) -> None:
    write_text(Path(html_dir) / f'{sanitize_filename(name)}.html', chapter.html)


def write_epub(chapters: list, job: Job, first_article) -> None:
    if not chapters:
        return
    save_imgs(chapters)
    author, name = book_name(job, first_article)
    html_md_to_epub(chapters, sanitize_filename(author), sanitize_filename(name or 'one_url'))


def html_name(source, article) -> str:
    return source.md_path.stem if source.kind == 'md' else article.filename


def sub_jobs(job: Job) -> list[Job]:
    """--split: каждый источник — своя книга."""
    if not job.split or len(job.sources) < 2:
        return [job]
    return [replace(job, sources=[s], dynamic_name=False) for s in job.sources]


def run_job(job: Job, *, outputs, md_dir, html_dir, sync, concurrency, interval):
    done = skipped = 0

    for sub in sub_jobs(job):
        fetched = fetch_sources(sub.sources, sync=sync,
                                concurrency=concurrency, interval=interval)
        chapters: list[Chapter] = []
        first_article = None

        for source, got in zip(sub.sources, fetched):
            if got is None:
                if source.kind != 'url':
                    # для url причина уже напечатана в fetch_sources
                    print(f'SKIP {source.md_path}')
                skipped += 1
                continue
            try:
                article = None
                if source.kind == 'md':
                    chapter = chapter_from_md(source)
                else:
                    article = get_article(source.url, source.html)
                    article.filename = sanitize_filename(article.filename)
                    chapter = chapter_from_article(article)
                    first_article = first_article or article
            except Exception as e:
                print(f'FAIL {source.url or source.md_path}: {type(e).__name__}: {e}')
                skipped += 1
                continue

            chapters.append(chapter)
            done += 1
            if article is not None and 'md' in outputs:
                write_md(article, md_dir)
            if 'html' in outputs:
                write_html(chapter, html_name(source, article), html_dir)

        if 'epub' in outputs:
            write_epub(chapters, sub, first_article)

    return done, skipped


def run(args, *, outputs=ALL_OUTPUTS, urls_list=False, split=False, sync=False,
        concurrency=5, interval=0, md_dir=MD_DIR, html_dir=HTML_DIR,
        author=None, name=None) -> int:
    jobs = parse_args(args, urls_list=urls_list, split=split)
    for job in jobs:
        if author is not None:
            job.author = author
        if name is not None:
            job.name, job.dynamic_name = name, False

    done = skipped = 0
    for job in jobs:
        if not job.sources:
            print(f'SKIP {job.name or job.author}: не нашлось ни одного url')
            continue
        job_done, job_skipped = run_job(
            job, outputs=outputs, md_dir=md_dir, html_dir=html_dir,
            sync=sync, concurrency=concurrency, interval=interval)
        done += job_done
        skipped += job_skipped

    print(f'готово: {done} статей, {skipped} пропущено')
    return 0 if done else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Скачать статьи и сохранить в md, html и epub',
        epilog='вход: url, .txt со списком url, .html сохранённой страницы, '
               '.md (--urls-list — список url, иначе готовый контент)')
    parser.add_argument('args', nargs='+', metavar='URL/ФАЙЛ')
    parser.add_argument('--urls-list', action='store_true',
                        help='в .md искать список url, а не читать как контент')
    parser.add_argument('--split', action='store_true',
                        help='каждый .md — отдельная книга (по умолчанию все вместе)')
    parser.add_argument('--no-md', action='store_true')
    parser.add_argument('--no-html', action='store_true')
    parser.add_argument('--no-epub', action='store_true')
    parser.add_argument('--sync', action='store_true', help='качать последовательно')
    parser.add_argument('--concurrency', type=int, default=5)
    parser.add_argument('--interval', type=int, default=0, help='пауза между запросами, сек')
    parser.add_argument('--author', help='переопределить автора книги')
    parser.add_argument('--name', help='переопределить название книги')
    return parser


def main(argv=None, **overrides) -> int:
    ns = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    outputs = tuple(
        name for name, skip in
        (('md', ns.no_md), ('html', ns.no_html), ('epub', ns.no_epub)) if not skip
    )
    kwargs = dict(
        outputs=outputs, urls_list=ns.urls_list, split=ns.split, sync=ns.sync,
        concurrency=ns.concurrency, interval=ns.interval,
        author=ns.author, name=ns.name,
    )
    kwargs.update(overrides)
    return run(ns.args, **kwargs)


if __name__ == '__main__':
    raise SystemExit(main())
