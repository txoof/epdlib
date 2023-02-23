# Block Module

`Block` objects are containers for text and images. `Block` objects are aware of their dimensions and can be made aware of their position within a larger [layout](./Layout.md).


## *Class* `Block(area, hcenter=False, vcenter=False, rand=False, inverse=False, abs_coordinates=(0, 0), padding=0, fill='BLACK', bkground='WHITE', border_config={}, pillow_palette=False)`

All sub-classes of the `Block` class inherit the properties and methods of this class.

### Args

 *  `area` (list/tuple): x and y integer values for dimensions of block area (property)
 *  `hcenter` (bool): True: horizontally center contents [False] (property)
 *  `vcenter` (bool): True: vertically center contents [False] (property)
 *  `rand` (bool): True: randomly place contents in area [False] (property)
 *  `inverse` (bool): True: invert pixel values [False] (property)
 *  `abs_coordinates` (list/tuple): x, y integer coordinates of this block area within a larger image [(0, 0)] (property)
 *  `padding` (int): number of pixels to pad around edge of contents [0] (property)
 *  `fill` (int): 0-255 8 bit value for fill color for text/images [0 black] (property)
 *  `bkground` (int): 0-255 8 bit value for background color [255 white] (property)
 *  `mode` (str): color mode for block '1': 1 bit color, 'L': 8 bit grayscale, 'RGB': (Red, Green, Blue) values (property)
 *  `border_config` (dict): dictionary containing kwargs configuration for adding border to image see `help(add_border)` (property)
 *  `pillow_palette`(bool): True map standard HTML RGB values for fill/bkground color names; False (default) use WaveShare specific values. (property)

### Properties

 *  `image`: None - overridden in child classes'''

### **Methods**

*****

### `update(update)`

Place holder method for child classes used for updating the contents of the block.

## *Class* `DrawBlock(area, *args, shape=None, abs_x=None, abs_y=None, scale_x=1, scale_y=1, halign='center', valign='center', draw_format={}, no_clip=True, **kwargs)`

Child class of `Block` that contains `pillow.ImageDraw` drawing objects. `DrawBlock` objects can contain ellipses, rounded_rectangles or rectangles. These are useful for creating horizontal and vertical rules and separators. DrawBlock objects can be aligned horizontally ('center', 'left', 'right' or vertically ('center', 'top', 'bottom') within the block area.

`DrawBlock` objects that are fully initialized with `area` and `shape` will automatically generate an image. No further updates are necessary. When using `DrawBlock` in a `Layout` layout, it is not necessary to send an update when the block is refreshed unless the properties have been changed. The generated image will remain in memory until the program is terminated.

### Properties       

 * `area` (tuple of int): area of block in pixels
 * `shape` (str): shape to draw (see DrawBlock.list_shapes())
 * `abs_x` (int): absolute x dimension in pixels of drawing (overrides scale_x)
 * `abs_y` (int): absolute y dimension in pixels of drawing (overrides scale_y)
 * `scale_x` (float): percentage of total x area (0..1) (abs_x overrides)
 * `scale_y` (float): percentage of total y area (0..1) (abs_y overrides)
 * `halign` (str): horizontal alignment of drawing; 'center', 'left', 'right' 
 * `valign` (str): vertical alignment of drawing; 'center', 'top', 'bottom'
 * `draw_format` (dict): dict of kwargs for shape drawing function
 * `no_clip` (bool): when True fit shapes completely within area
 * `image` (PIL:Image): rendered shape
 
###  **Methods**

*****

### `list_shapes()`

Static method: list supported shapes that can be drawn

#### Args

* None

### `draw_help()`

Static method: print the docstring for the currently set shape

#### Args

* None

### `update(update=True)`

Update the image. This is **only** necessary if the object properties have been changed or the object was not created with a `shape` property.

#### Args

* `update` (bool) True forces update of image

### `draw_image()` 

Update the image using the selected drawing function and `draw_format` property

### Args

* None

### Returns

* None
  
## *Class* `TextBlock(font, area, text='NONE', font_size=0, max_lines=1, maxchar=None, chardist=None)`

Child class of `Block` that contains formatted text. `TextBlock` objects can do basic formatting of strings. Text is always rendered as a 1 bit image (black on white or white on black). Text can be horizontally justified and centered and vertically centered within the area of the block. 

`TextBlock` objects will attempt to calculate the appropriate number of characters to render on each line given an area, font face and character distribution. Each font face renders characters at a different width and each TTF character uses a different X width (excluding fixed-width fonts). 

### Properties

* `font` (str): path to TTF font face - relative paths are acceptable
* `area` (2-tuple of int): area of block in pixles - required
* `text` (str): string to format 
    - Default: 'NONE'
* `font_size` (int): font size in points (updates font object when set)
    - Default: 0
* `max_lines` (int): maximum number of lines to use when wrapping text
    - Default: 1
* `maxchar` (int): maximum number of characters to fit on a line
    - if set to `None`, the text block will calculate this value based on the font face and specified `chardist`
    - Default: None
* `chardist` (dict): statistical character distribution for a supported language to use for a specified font
    - dictionary of letter and float representing fractional distribution (see `print_chardist`)
* `image` (PIL.Image): resultant image generated of formatted text
*  `align` (str): 'left', 'right', 'center' justify text (default: left)

### Functions

* `print_chardist(chardist=None)` - print supported character distributions
    - chardist (str): `chardist='USA_CHARDIST'` print the character distribution for USA English

### Methods

#### `update(update=None)`

Update the text string with a new string and sets `image` property

#### Args

* `update` (str): string to display

## *Class* `Block.ImageBlock(area, image=None)`

Child class of `Block` that contains formated images. `ImageBlock` objects do basic formatting of color, centering and scaling. All `ImageBlock` images are 8 bit grayscale `Pillow.Image(mode='L')`. Images that are too large for the area are rescaled using the `Pillow.Image.thumbnail()` strategies to limit distortion. Images that are smaller than the set area will **not** be resized.

All properties of the parent class are inherited.


### Properties

* `image` (:obj:PIL.Image or :obj:str) - `Pillow` image or path provided as a `str` to an image file; relative paths are acceptable
* `remove_alpha(bool)`: true: remove alpha chanel of PNG or similar files; see: https://stackoverflow.com/a/35859141/5530152

### **Methods**

*****

### `update(update=None)`

Update the image with a new image and sets `image` property

#### Args

* `update` (image) image to display

#### Returns

* True on success

### `remove_transparency(im, bg_colour=(255, 255, 255))` 

Static method: remove transparency from PNG and similar images

#### Args

* `im` (PIL image) image to process
* `bg_color` (background) color to replace alpha/transparency

### *Block Module Functions*

*****

### `add_border(img, fill, width, outline=None, outline_width=1, sides=['all'])`

Add a border around an image. Used by the `Block` class to add borders to images

#### Args

 * `img` (PIL.Image): image to add border to
 * `fill` (int): border fill color 0..255 8bit gray shade
 * `width` (int): number of pixels to use for border
 * `outline` (int): 0..255 8bit gray shade for outline of border region
 * `outline_width` (int): width in pixels of outline
 * `sides` (list of str): sides to add border: "all", "left", "right", "bottom", "top" 

#### Returns:

* PIL.Image