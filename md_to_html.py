#!/bin/python

import markdown
import sys

for filename in sys.argv[1:]:
    with open(filename, 'r') as f:
        output = markdown.markdown(f.read())
        print(output)

