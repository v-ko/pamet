import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(name="misli",
                 version="0.1.0",
                 author="Petko Ditchev",
                 author_email="pditchev@gmail.com",
                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 url="https://github.com/fusion-a/misli",
                 packages=setuptools.find_packages(),
                 scripts=[
                     'tools/watch-and-rebuild-qt-ui',
                     'tools/watch-and-rebuild-qt-ui-pyside2'
                 ])
