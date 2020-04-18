import setuptools

# import most of the setup vars from here
from constants import *

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=name,
    version=version,
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
