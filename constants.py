name="epdlib" # Replace with your own username
author="Aaron Ciuffo"
author_email="aaron.ciuffo@gmail.com"
description="EpdLib is a library for creating dynamically scaled screen layouts for frame-buffered devices such as e-paper/e-ink displays."
url="https://github.com/txoof/epdlib"
classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent"]
keywords="graphics e-paper display waveshare"
install_requires=["Pillow", "spidev", "RPi.GPIO", "requests",
                  "omni-epd @ git+https://github.com/robweber/omni-epd.git#egg=omni-epd"]
#dependency_links=["https://github.com/robweber/omni-epd.git#egg=omni-epd"]
project_urls={"Source": "https://github.com/txoof/epdlib"}
python_requires='>=3.7'
