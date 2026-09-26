from pathlib import Path

from sources import book_from_stem, book_name, parse_args, urls_from_md, urls_from_txt

TXT = """https://example.com/a
https://example.com/b
https://example.com/a
"""

TXT_WITH_STEM = """OlegMakarenko=https://example.com/rss/
Ильяхов = https://example.com/ilya
не-урл
"""

TXT_WITH_QUERY = """https://example.com/search?q=a&page=2
https://example.com/ok
"""

MD_LIST = """- [ ] +100 [Заголовок](https://example.com/1)
- [ ] +50 [Другой](https://example.com/2)
- [ ] повтор [Другой](https://example.com/2)
ссылка в тексте (https://example.com/3)
"""

MD_ARTICLE = """# Заголовок статьи

11 июн в 11:00

[https://example.com/article](https://example.com/article)

Текст статьи с [ссылкой](https://example.com/inline).
"""


def test_urls_from_txt_keeps_order_dedups():
    urls = urls_from_txt(Path(_tmp(TXT)))
    assert urls == ['https://example.com/a', 'https://example.com/b']


def test_urls_from_txt_supports_stem_eq_url():
    assert urls_from_txt(Path(_tmp(TXT_WITH_STEM))) == [
        'https://example.com/rss/', 'https://example.com/ilya']


def test_urls_from_txt_keeps_query_equals():
    assert urls_from_txt(Path(_tmp(TXT_WITH_QUERY))) == [
        'https://example.com/search?q=a&page=2', 'https://example.com/ok']


def test_urls_from_md_dedups_keeps_order():
    assert urls_from_md(Path(_tmp(MD_LIST))) == [
        'https://example.com/1', 'https://example.com/2', 'https://example.com/3']


def test_book_from_stem():
    assert book_from_stem('Oleg - 2025-05-25') == ('Oleg', '2025-05-25')
    assert book_from_stem('vas3k') == ('', 'vas3k')


def test_single_url_job_has_dynamic_name_and_domain_author():
    jobs = parse_args(['https://vas3k.blog/blog/post/'])
    assert len(jobs) == 1
    assert jobs[0].author == 'vas3k.blog'
    assert jobs[0].dynamic_name
    assert book_name(jobs[0], _article('Пять сценариев')) == ('vas3k.blog', 'Пять сценариев')


def test_txt_file_becomes_one_book_named_after_stem():
    jobs = parse_args([_tmp(TXT, 'Oleg - 2025-05-25.txt')])
    assert (jobs[0].author, jobs[0].name) == ('Oleg', '2025-05-25')
    assert len(jobs[0].sources) == 2


def test_author_falls_back_to_domain_of_first_source():
    jobs = parse_args([_tmp(TXT, 'tarasenko.txt')])
    assert (jobs[0].author, jobs[0].name) == ('example.com', 'tarasenko')


def test_each_url_and_file_is_own_book():
    jobs = parse_args(['https://a.com/1', 'https://b.com/2', _tmp(TXT, 'c.txt')])
    assert len(jobs) == 3


def test_md_without_flag_is_content():
    jobs = parse_args([_tmp(MD_ARTICLE, 'Oleg - статья.md')])
    assert len(jobs) == 1
    source = jobs[0].sources[0]
    assert source.kind == 'md'
    assert source.title == 'Заголовок статьи'
    assert source.url == 'https://example.com/article'
    # префикс в имени файла — это автор, он сильнее домена из ссылки
    assert (jobs[0].author, jobs[0].name) == ('Oleg', 'статья')


def test_md_without_author_prefix_falls_back_to_domain():
    jobs = parse_args([_tmp(MD_ARTICLE, 'статья.md')])
    assert (jobs[0].author, jobs[0].name) == ('example.com', 'статья')


def test_md_files_merge_into_one_book():
    jobs = parse_args([_tmp(MD_ARTICLE, 'a - раз.md'), _tmp(MD_ARTICLE, 'b - два.md')])
    assert len(jobs) == 1
    assert len(jobs[0].sources) == 2
    # имя и автор книги берутся из первого файла
    assert (jobs[0].author, jobs[0].name) == ('a', 'раз')


def test_split_separates_md_books():
    jobs = parse_args([_tmp(MD_ARTICLE, 'a - раз.md'), _tmp(MD_ARTICLE, 'b - два.md')],
                      split=True)
    assert len(jobs) == 2


def test_md_with_urls_list_flag():
    jobs = parse_args([_tmp(MD_LIST, 'digest.md')], urls_list=True)
    assert [s.kind for s in jobs[0].sources] == ['url'] * 3


def test_html_file_is_read_locally():
    page = ('<html><head><link rel="canonical" href="https://example.com/canonical">'
            '</head><body><p>текст</p></body></html>')
    jobs = parse_args([_tmp(page, 'page.html')])
    source = jobs[0].sources[0]
    assert source.kind == 'html'
    assert source.url == 'https://example.com/canonical'
    assert 'текст' in source.html


def test_html_file_url_comes_from_og_url():
    page = ('<html><head><meta property="og:url" content="https://example.com/og">'
            '</head><body><p>текст</p></body></html>')
    jobs = parse_args([_tmp(page, 'page.html')])
    assert jobs[0].sources[0].url == 'https://example.com/og'


def test_html_file_without_url_still_parses():
    from article_to_md import get_article
    jobs = parse_args([_tmp('<html><body><h1>Заголовок</h1><p>текст</p></body></html>', 'page.html')])
    source = jobs[0].sources[0]
    assert source.url is None
    # раньше на url=None падало `k in url`
    assert 'текст' in get_article(source.url, source.html).md_content


def test_missing_file_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_args(['нет-такого.md'])


def _tmp(text: str, name: str = 'file.txt') -> str:
    import tempfile
    path = Path(tempfile.gettempdir()) / 'mdtools_tests' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf8')
    return str(path)


def _article(title: str):
    from article_to_md import Article
    return Article(raw_html='', success=True, error_code='', title=title,
                   md_content='', html_content='', filename=title)
