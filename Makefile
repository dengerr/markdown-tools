start.html:
	.venv/bin/python md_to_html.py ~/org/Zettelkasten/buryi_de/start.md > start.html
	scp start.html root@killdozer:/var/www/html/buryi.de/start.html

clean:
	rm *.html
	rm md/*
	echo "" > urls.txt

epub:
	uv run bulk_get_articles_to_md.py
	uv run md_to_epub.py md/*.md
