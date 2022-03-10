## v0.6.0.0 - 2022.03.09
**Screen**
* Migrated to Omni-EPD for screen support
* Added support for Inky screens
* Removed the sleep attribute from writeEPD()

## 0.5.1.1 - 2022.01.16
**TextBlock**

* add option to stop text wrapping (textwrap=False)
* changed test string used for calculating maximum characters per line to include digits: 9QqMm
    - this results in all calculated font sizes being slightly smaller, but fitting better in most cases

## 0.5.1.0 - 2022.01.16
**ImageBlock**

* add static method `remove_transparency(im, bg_colour=(255, 255, 255))` to `ImageBlock` 
    - removes alpha/transparency chanels from PNG and similar images and replaces with bg_color
* add propery `remove_alpha=True` to remove transparency/alpha on PNG images by default

## 0.5.0.4 - 2021.08.12
**Screen**

* when SPI is not enabled, `writeEPD` returns `FileNotFoundError` instead of `ScreenError`
    - this makes it easier to provide useful feedback to users when SPI is not setup

## 0.5.0.3 - 2021.08.09
* handle exeptions when writing to EPD

## 0.5.0.0 - 2021.08.07
Add new Block type "DrawBlock" and Layout support

**Block**

* add class "DrawBlock" for drawing `ImageDraw` basic shapes
    - DrawBlock blocks are useful for creating horizontal and vertical rules in Layout displays
    - supported shapes: `ellipse`, `rounded_rectangle`, `rectangle`
    - DrawBlock shapes can be horizontally (center, left, right) and vertically (center, top, bottom) aligned
    - all formatting paramaters can be used when drawing supported shapes
* add option to add a border around each block type
    - `Block` objects accept the kwarg `border_config` to add borders around the top, bottom, left and right sides
    - see

* update docstrings
* add dummy `update()` method to `Block` parent class for completness

**Layout**

* Layouts now support ImageBlock, TextBlock and DrawBlock objects
    - DrawBlock objects are included similar to Text and Image blocks, but **MUST** include the key "type"
        * 'type': 'DrawBlock'
    - As of epdlib v0.6, all layout sections **MUST** include the key "type"
        * Layout v0.5 attempts to guess the appropriate block type; this will be removed in v0.6
* Small changes in logging output to decrease verbosity and make verbose output easier to follow

## 0.4.6.0 - 2021.08.05
Fix issue #15 - "unknown module" when display = "HD" and no vcom value set

## 0.4.5.0 - 2021.08.02
Add option to force all blocks in a layout to 1bit mode. TT Fonts are rendered with anti-aliasing in all modes except for 1bit mode. Anti-aliased fonts display poorly on 1bit screens with extremely jagged edges.

**Layout**

* `Layout` objects now support boolean property `force_onebit` 
    - When set to `True` all blocks are forced to `mode = '1'`

## 0.4.4 - 2021.07.31
rewrite of `Screen` module to fix unclosed SPI file handles
**Screen**

* `initEPD()` method is now depricated and no longer needed; this can be removed from the code 
    - displays are automatically woken prior to write/clear and put to sleep after write/clear
    - at your own risk, use `writeEPD(sleep=True)` to keep display awake after write. For non-IT8951 boards, you **must** manually call `epd.sleep()` prior to the next write/clear event to ensure the SPI file handle is properly closed.
* `writeEPD()` and `clearEPD()` methods now handle all init, write and sleep operations automatically
    - it is no longer necessary to call 
* added convenience static method `list_compatible()` to print list of non-IT8951 boards 

## 0.4.3
rework of `Block` and `Layout` modules to fix padding and text scaling

**Block**

* parent `Block` class now consumes any unknown `kwargs`
  - this makes it much easier to pass any values from a `Layout.layout` obj.
* rewrite of text scaling to provide a cleaner image and crisper font rendering
* add `align` argument to `Block.TextBlock` for aligning text
* fixed various padding issues (again)
* Switched to using `multiline_text()` method of ImageDraw for better leading and line spacing

**Layout**

* Remove scale_x, scale_y from layouts
    - this feature was not as useful as it appeared and is a pain to maintain   
* update private methods:
  - `_set_image` now `_set_blocks` 
  - removed `_check_keys`
  - `_scalefont` minor updates
* default values for expected/necessary `Layout` and `Block` kwargs are now stored in `constants.layout_defaults`
* add property `mode` "L" when *any* block is 8bit "1" when all blocks are 1bit

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
