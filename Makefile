start.html:
	.venv/bin/python md_to_html.py ~/org/Zettelkasten/buryi_de/start.md > start.html
	scp start.html root@killdozer:/var/www/html/buryi.de/start.html

clean:
	rm start.html
