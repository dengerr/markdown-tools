#!/bin/python

import markdown
from pathlib import Path
import sys


OUTPUT_DIR = 'output'


def one_template(filenames):
    template = open('template.html').read()

    for filename in filenames:
        with open(filename, 'r') as f:
            body = markdown.markdown(f.read())
            title = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]
            with open(f"{title}.html", "w") as out_file:
                result = template % dict(title=title, body=body)
                out_file.write(result)


def md_and_template(filenames, stdout=True):
    for filename in filenames:
        with open(filename, 'r') as f:
            body = markdown.markdown(f.read())
        template_name = filename.rsplit('.', 1)[0] + '_template.html'
        with open(template_name, 'r') as f:
            template = f.read()
        title = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        result = template % dict(title=title, body=body)

        if stdout:
            print(result)
        else:
            with open(f"{title}.html", "w") as out_file:
                out_file.write(result)



def without_template(filenames, stdout=True):
    for filename in filenames:
        with open(filename, 'r') as f:
            body = markdown.markdown(f.read())
        title = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]

        if stdout:
            print(body)
        else:
            with open(Path(OUTPUT_DIR, f"{title}.html"), "w") as out_file:
                out_file.write(body)

if __name__ == "__main__":
    without_template(sys.argv[1:], False)

