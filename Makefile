start.html:
	.venv/bin/python md_to_html.py ~/org/Zettelkasten/buryi_de/start.md > start.html
	scp start.html root@killdozer:/var/www/html/buryi.de/start.html

clean:
	rm -f cache.shelve.db
	rm -rf cache/*

epub:
	uv run pipeline.py urls/*.txt

rss:
	uv run rss_to_epub.py rss_subs.txt

test:
	uv run pytest
