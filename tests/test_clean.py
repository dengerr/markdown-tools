from bs4 import BeautifulSoup

from article_to_md import clean_for_reading, sanitize_filename


def clean(html: str) -> str:
    soup = BeautifulSoup(html, 'lxml')
    return clean_for_reading(soup.body or soup).decode_contents()


def test_drops_script_style_and_noise_tags():
    out = clean('<p>текст</p><script>alert(1)</script><style>a{}</style>'
                '<form><input></form><iframe src="x"></iframe><button>ok</button>')
    assert 'текст' in out
    for junk in ('alert', '<style', '<form', '<input', '<iframe', '<button'):
        assert junk not in out, junk


def test_drops_react_comment_artifacts():
    assert '<!--[-->' not in clean('<p>a</p><!--[--><p>b</p><!--]-->')
    assert 'b' in clean('<p>a</p><!--[--><p>b</p><!--]-->')


def test_drops_negative_class_blocks():
    out = clean('<p>статья</p><div class="comments">мусор</div>'
                '<div class="post-share">поделиться</div>'
                '<div class="author-bio">кто я</div>')
    assert 'статья' in out
    for junk in ('мусор', 'поделиться', 'кто я'):
        assert junk not in out, junk


def test_keeps_negative_tokens_that_are_only_text():
    assert 'search engine' in clean('<p>search engine</p>')


def test_strips_presentational_attributes_keeps_meaningful():
    out = clean('<p class="x" style="color:red" data-id="7" onclick="f()">t</p>'
                '<img src="a.png" alt="описание" srcset="a-2x.png 2x" sizes="100vw"'
                ' loading="lazy" width="10">'
                '<a href="https://x" target="_blank">link</a>')
    for junk in ('class=', 'style=', 'data-id', 'onclick', 'srcset', 'sizes', 'loading='):
        assert junk not in out, junk
    assert 'src="a.png"' in out
    assert 'alt="описание"' in out
    assert 'width="10"' in out
    assert 'href="https://x"' in out


def test_keeps_id_for_anchors():
    assert 'id="section"' in clean('<h2 id="section">заголовок</h2>')


def test_unwraps_empty_wrappers():
    out = clean('<div><div></div><div> </div><p>текст</p></div>')
    assert out.count('<div>') == 1
    assert 'текст' in out


def test_keeps_empty_img():
    assert '<img' in clean('<div><div></div><img src="a.png"></div>')


def test_does_not_mutate_original():
    soup = BeautifulSoup('<div><p class="x">t</p></div>', 'lxml')
    clean_for_reading(soup.div)
    assert soup.div.find('p')['class'] == ['x']


def test_sanitize_filename_keeps_punctuation_keeps_titles_readable():
    # `:` и `?` оставляем — они есть в именах уже скачанных статей
    assert sanitize_filename('a/b\\c') == 'a-b-c'
    assert sanitize_filename('Статья: про 5G! Норм?') == 'Статья: про 5G! Норм?'
    assert sanitize_filename('  много   пробелов  ') == 'много пробелов'
    assert sanitize_filename('') == 'article'
    assert sanitize_filename('///') == '---'
    assert sanitize_filename('хвост.') == 'хвост'


def test_sanitize_filename_truncates_on_word_boundary():
    name = sanitize_filename('слово ' * 60, max_len=40)
    assert len(name) <= 40
    assert not name.endswith('слов')


def test_get_fetch_url_for_does_not_touch_network():
    import article_to_md
    from article_to_md import get_fetch_url_for
    # раньше слой загрузки делал get_config(url) — а он в __init__ качает страницу
    calls = []
    original = article_to_md.get_raw_html
    article_to_md.get_raw_html = lambda url: calls.append(url) or '<html></html>'
    try:
        assert get_fetch_url_for('https://t.me/memes/1') == 'https://t.me/memes/1?embed=1&mode=tme'
        assert get_fetch_url_for('https://vas3k.blog/a/b') == 'https://vas3k.blog/a/b'
        assert get_fetch_url_for(None) == ''
    finally:
        article_to_md.get_raw_html = original
    assert calls == []


def test_telegram_fetch_url_keeps_existing_query():
    from article_to_md import get_fetch_url_for
    assert get_fetch_url_for('https://t.me/s/1?x=2') == 'https://t.me/s/1?x=2&embed=1&mode=tme'


def test_body_tag_is_unwrapped():
    # фрагмент идёт в главу epub: <body> внутри div невалиден для XHTML
    soup = BeautifulSoup('<body><h1>Заголовок</h1><p>текст</p></body>', 'lxml')
    clean = str(clean_for_reading(soup.body))
    assert '<body>' not in clean and '</body>' not in clean
    assert 'текст' in clean and 'Заголовок' in clean
