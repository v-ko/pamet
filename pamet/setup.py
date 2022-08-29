from pathlib import Path
import setuptools


version = (Path(__file__).parent / 'pamet' / 'VERSION').read_text()

setuptools.setup(name='pamet',
                 version=version,
                 packages=setuptools.find_packages(),
                 entry_points={
                     'console_scripts': [
                         'pamet=pamet.desktop_app.main:main',
                         'pamet-debug=pamet.desktop_app.main_debug:main',
                     ],
                 },
                 install_requires=[
                     'PySide6', 'fusion', 'click', 'python-slugify', 'thefuzz',
                     'peewee', 'pillow'
                 ])
