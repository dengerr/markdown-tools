start.html:
	.venv/bin/python md_to_html.py ~/org/Zettelkasten/buryi_de/start.md > start.html
	scp start.html root@killdozer:/var/www/html/buryi.de/start.html

clean:
	rm md/*
	echo "" > urls.txt

epub:
	uv run bulk_get_articles_to_md.py
	uv run md_to_epub.py md/*.md

rss:
	uv run rss_to_epub.py "Oleg - `date +%Y-%m-%d`=https://olegmakarenko.ru/data/rss"
	uv run rss_to_epub.py "ammo1 - `date +%Y-%m-%d`=http://ammo1.ru/feed"
	uv run rss_to_epub.py "ksoftware - `date +%Y-%m-%d`=https://ksoftware.livejournal.com/data/rss"
