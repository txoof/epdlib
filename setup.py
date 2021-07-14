import setuptools

# import most of the setup vars from here
from constants import *

exec(open('epdlib/version.py').read())


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=name,
    #version='0.4.3.7',
    version=__version__,
    author=author,
    author_email=author_email,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=url,
    packages=setuptools.find_packages(),
    classifiers=classifiers,
    keywords=keywords,
    install_requires=install_requires,
    project_urls=project_urls,
    python_requires=python_requires,
    package_data={"documentation": ["./docs"]},
)
