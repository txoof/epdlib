## 0.6.2.0 - 2023.09.16

**Block**

* explicitly remove all mutables from default value assignments in methods
    - no changes to public/private methods

**Layout**

* explicitly remove all mutables from default value assignments in methods
* deepcopy the supplied layout into new property `_master_layout`
    - this resolves [issue #51](https://github.com/txoof/epdlib/issues/51#issuecomment-1722217690)
    - `_layout` contains the calculated layout with all of the areas and absolute coordinates
    - `_master_layout` contains the user-supplied raw layout with relative positions
* small internal changes to `resolution` method

## 0.6.1.2 - 2023.06.28

**requirements**

* remove unneeded requests requirement

## 0.6.1.0 - 2023.02.25

**Documentation**

* Rewrite and reformat documentation
* Split modules into independent documents

**Block**

* Add `pillow_palette` argument; True: map color names to RGB standard HTML color values, False (default) map color names to WaveShare values. 
   - WaveShare 7 color panels use different "ORANGE" and "GREEN" values from the standard HTML color values.
* Blocks now default to `fill='BLACK` and `bkground='WHITE'` instead of `fill=0` and `bkground=255`
* Fill and bkground colors appropriately map to match the block color mode
* Resetting font size for `TextBlock` objects now update the font size without redefining the font path

**Screen**

* `colors2palette` uses WaveShare R, O, Y, B, G, Blk, W values by default

**Layout**

* Improve logic for determining block color mode

## 0.6.0.0 - 2023.02.10

**Screen**

* Add "RGB" as valid value for `mode` property
    - This is auto-detected for all 7 Color Screens
* Add method `reduce_palette` to reduce all of the colors in an image to a set palette
   
* Add method `colors2palette` to produce a palette that can be used with the `reduce_palette` method
    - The default is a 7-color palette of w3 colors: 'RED', 'ORANGE', 'YELLOW', 'GREEN', 'BLUE', 'WHITE', 'BLACK' 
* Update `list_compatible_modules` module function to show supported mode

**Layout**

* Add `mode` property to `__init__`
    - Supports "1", "RGB", "L"
* Mode property validates value against `constants.MODES` and throws `AttributeError`
* API Change in `Layout` class: add public method `set_block` to create or update a single block
* API Change in `Layout` class: add public method `update_block_props` to allow changing the layout settings for a block
    - the block must be updated using `update_contents` after the properties are changed
* API Change in `Layout` class: all `Layout.layout` dictionaries must now contain the key `type` that indicates the block type: (`TextBlock`, `ImageBlock`, `DrawBlock`). Failure to include this key will raise a `KeyError`.

**Block**

* `Block` superclass for all block classes now supports "RGB" mode
* All classes support the following for `fill`, `bkground` and `outline` 
    - RGB tuples: `(128, 128, 128)`
    - hex `0x808080`
    - integers: `8421504`
    - colormap colors: `"gray"`- (see `ImageColor.getcolor`)


## 0.5.2.1 - 2022.12.11

* add option to mirror screen: `Screen(mirror=True)`
* Screen() now handles kwargs on init and maps them to properties

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
