import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="epdlib", # Replace with your own username
    version="0.0.1.2",
    author="Aaron Ciuffo",
    author_email="aaron.ciuffo@gmail.com",
    description="EpdLib is a library for creating dynamically scaled screen layouts for frame-buffered devices such as e-paper/e-ink displays.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/txoof/epdlib",
    packages=setuptools.find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    keywords="graphics e-paper display waveshare",
    install_requires=["Pillow"],
    project_urls={"Source": "https://github.com/txoof/epdlib"},
    python_requires='>=3.7',
    package_data={"documentation": ["./docs"]},
)