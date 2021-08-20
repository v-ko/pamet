import setuptools

setuptools.setup(
    name="pamet",
    version="4.0.0.pre-alpha1",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'pamet=pamet.desktop.main:main',
            'pamet-debug=pamet.desktop.main_debug:main',
        ],
    },
    install_requires=['PySide6']
)
