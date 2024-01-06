import setuptools

# import most of the setup vars from here

exec(open('epdlib/version.py').read())


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="epdlib",
    #version='0.4.3.7',
    version=__version__,
    author="Aaron ciuffo",
    author_email="aaron.ciuffo@gmail.com",
    description="library for creating dynamic layouts for frame-buffered devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/txoof/epdlib",
    packages=setuptools.find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent"],
    keywords="graphics e-paper display waveshare",
    install_requires=["Pillow", "spidev", "RPi.GPIO", "gpiozero", "lgpio"],
    project_urls={"Source": "https://github.com/txoof/epdlib"},
    python_requires=">=3.7",
    package_data={"documentation": ["./docs"]},
)


