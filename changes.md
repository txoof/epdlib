## 0.4.2
**Screen**

* now supports IT8951 based panels
* `Screen.epd` object is now supplied as a string, not an object
    - use `epdlib.Screen.list_compatible_modules()` to show compatible waveshare_epd panels
    - use `Screen(epd='HD', vcom=[your IT8951 vcom (see ribon cable)]` for IT8951 based panels
* `Screen.writeEPD()` now supports partial refresh on IT8951 panels for partial refresh of black & white pixels
    - use `writeEPD(image, partial=True)`
    - partial refresh does not affect gray pixels

**Block**

* now supports 8 bit grayscale images, text and background on IT8951 based panels
    - previously 8 bit images were downscaled to dithered 1 bit images; this is still the case on 1 bit panels
    - use `Block.mode = "L"` for 8 bit support within a block
* now supports 8 bit fill and background on IT8951 panels
    - use `Block.background=[0-255]` and `Block.fill=[0-255]` 0 is black, 255 is fully white
* padding now fully supported in all block types
    - previosuly only worked properly on `ImageBlock` objects

**Layout**
* now supports the following features when specified in the layout dictionary:
    - `'fill': 0-255` specify text fill (8 bit gray 0 is black)
    - `'bkground: 0-255` specify background color (8 bit gray 0 is black)
    - `'mode': "L"/"1"` specify block image mode "L" 8 bit, "1" 1 bit
## 0.1.1
**Screen.Screen()** 

* add property: rotation(`int`): rotate the output image by 0, 90, -90 or 180 degrees

**Layout.Layout()**

* fix typos in example layout docstrings
