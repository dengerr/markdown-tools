#!/bin/python

import markdown
import sys


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


if __name__ == "__main__":
    md_and_template(sys.argv[1:])

