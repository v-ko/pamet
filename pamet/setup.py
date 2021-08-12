import setuptools

setuptools.setup(
    name="pamet",
    version="4.0.0.pre-alpha1",
    packages=setuptools.find_packages(),
    console_scripts=['bin/pamet', 'bin/pamet-debug']
)
