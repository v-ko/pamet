from pathlib import Path
import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

version = (Path(__file__).parent / 'fusion' / 'VERSION').read_text()

setuptools.setup(
    name="fusion",
    version=version,
    author="Petko Ditchev",
    author_email="pditchev@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/v-ko/misli",
    packages=setuptools.find_packages(),
)
