import setuptools

# with open("../README.md", "r") as fh:
#     long_description = fh.read()

setuptools.setup(
    name="pamet_desktop",
    version="4.0.0.a1",
    author="Petko Ditchev",
    author_email="pditchev@gmail.com",
    description="An application for organizing thoughts, notes and projects",
    # long_description=long_description,
    # long_description_content_type="text/markdown",
    url="https://github.com/petko10/misli",
    packages=setuptools.find_packages(),
    scripts=['bin/pamet'],
    # classifiers=[
    #     "Programming Language :: Python :: 3",
    #     "License :: OSI Approved :: MIT License",
    #     "Operating System :: OS Independent",
    # ],
)
