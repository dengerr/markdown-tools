#!/usr/bin/python3
# Собрать epub из списка url (.txt / .md) или из одного url.
# Эпилог пайплайна: pipeline.py.

import sys

from pipeline import main

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:], outputs=('epub',), urls_list=True))
