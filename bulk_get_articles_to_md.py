#!/usr/bin/python3
# Скачать список статей в md. Читает .txt со списком url или .md со списком
# ссылок, последовательно, с паузой. Эпилог пайплайна: pipeline.py.

import sys

from pipeline import main

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:], outputs=('md',), urls_list=True, sync=True, interval=4))
