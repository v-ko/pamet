import setuptools

setuptools.setup(
    name="pamet",
    version="4.0.0.pre-alpha1",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'pamet=pamet.desktop_app.main:main',
            'pamet-debug=pamet.desktop_app.main_debug:main',
        ],
    },
    install_requires=['PySide6', 'misli', 'misli_debug']
)
