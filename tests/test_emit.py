import markdown
from pathlib import Path

from md_to_epub import Chapter
from pipeline import chapter_from_article, chapter_from_md, html_name
from sources import Source

MD = """# Заголовок

[url](https://example.com/a)

Абзац с **жирным** и [ссылкой](https://example.com/inline).
"""


def test_md_becomes_chapter_without_article():
    source = Source(kind='md', url='https://example.com/a', md_path=_write(MD), title='Заголовок')
    chapter = chapter_from_md(source)
    assert isinstance(chapter, Chapter)
    assert chapter.title == 'Заголовок'
    assert '<strong>жирным</strong>' in chapter.html
    assert 'https://example.com/inline' in chapter.html


def test_article_becomes_chapter_using_prebuilt_html():
    article = _article('Заголовок', html='<h1>Заголовок</h1><p>текст</p>')
    chapter = chapter_from_article(article)
    assert chapter.title == 'Заголовок'
    assert chapter.html == article.html_content


def test_chapter_from_md_matches_markdown_conversion():
    source = Source(kind='md', md_path=_write(MD), title='t')
    assert chapter_from_md(source).html == markdown.markdown(MD)

def test_html_name_uses_article_filename_and_md_stem():
    article = _article('Заголовок', html='')
    assert html_name(Source(kind='url'), article) == article.filename
    assert html_name(Source(kind='md', md_path=_write(MD)), None) == Path(_write(MD)).stem


def test_save_imgs_and_epub_take_chapters_only():
    # Chapter — единственный контракт: ни Article, ни пути к файлам
    chapter = Chapter('Заголовок', '<h1>Заголовок</h1>')
    assert chapter.title == 'Заголовок'


def _write(text: str) -> Path:
    import tempfile
    path = Path(tempfile.gettempdir()) / 'mdtools_tests' / 'article.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf8')
    return path


def _article(title: str, html: str):
    from article_to_md import Article
    return Article(raw_html='', success=True, error_code='', title=title,
                   md_content='', html_content=html, filename=title)
