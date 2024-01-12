# Screen Module

`Screen` objects provide a method for waking and writing images to a WaveShare E-Paper Display (EPD). `Screen` objects are aware of their resolution and when they were last updated (stored in monotonic time). 

Use a [`Layout`](./Layout.md) object to generate images that can be written by `Screen` objects to a variety of WaveShare screens. 

For a short demo that tests the currently attached screen use:

```bash
$ python -m Screen  
```

## *Class* `Screen.Screen(resolution=None, epd=None)`

### Args

### Properties

* `resolution` (list): X x Y pixels
* `clear_args` (dict): kwargs dict of any additional kwargs that are needed for clearing a display
* `buffer_no_image` (PIL:Image): "blank" image for clearing bi-color panels (empty for all others)
* `vcom (float): negative vcom voltage from panel ribon cable
* `HD` (bool): True for IT8951 panels
* `rotation` (int): rotation of screen (0, -90, 90, 180)
* `mirror` (bool): mirror the output 
* `update` (obj:Update): monotoic time aware update timer


### **Methods**

*****

### `blank_image():` 

Return a blank PIL.Image in of `mode` type of `resolution` dimensions.

#### Args

* None

### `clearEPD()`

Send the clear signal to the EPD to wipe all contents and set to "white" that is appropriate for configured EPD.

#### Args

* None

#### Returns

* None

### `colors2palette(colors=constants.COLORS_7_WS.values(), num_colors=256)`

Static method to generate a palette that can be used in reducing an image to a fixed set of colors. Use this in combination with the `reduce_palette` method.

#### Args

* `colors` (list of tuples of RGB values): colors to use in defining the pallet. The default are the 'standard' values of the 7 color epd screens.
* `num_colors`: total number of colors to use in remapping. For RGB, 256 should sufficient.


<!-- #region -->
#### Returns

* list of RGB values 

### `intiEPD()`

This method should not be used, but is preserved for compatibility. Initializes the EPD for writing (deprecated and no longer functional). This is now handled automatically by the class to ensure that SPI file handles are opened and closed properly. There is no need to init the EPD under normal circumstances. 

For non HD (IT8951) displays, use `epd.init()` to manually init the screen. It is imperative to track `init()` calls and close the SPI file handles with `epd.sleep()`. Failure to do this will result in long-running jobs to fail due to running out of SPI file handles. USE AT YOUR OWN RISK.

#### Args

* None

##### Returns

* None

### `list_compatible_modules()`

Static method to print a list of all waveshare_epd panels that are compatible with epdlib

#### Args

* None

#### Returns

* None

###  `reduce_palette(image, palette, dither=False)`

Reduce an image to a fixed palette of colors. This method creates a posterized version of the original image forcing all colors to set colors. This is useful for matching the supported colors of an EPD.

#### Args

* `image`: `PIL.Image` image to be reduced
* `palette`: `list` of RGB color values - this is a flat list, not a list of lists or tuples
    - Use `colors2palette()` to generate an appropriate list
* `dither`: `bool` True: creates a dithered image, False creates color fields

#### Returns

* `PIL.Image`

#### Example

```Python
# create reduced palette images 
import Screen
from PIL import Image
# create screen object
s = Screen(epd='epd5in65f')
# load image
image = Image.Open('./images/portrait-pilot_SW0YN0Z5T0.jpg')
image.thumbnail(s.resolution)
# create color palette
color_palette = s.colors2palette()
# create image with solid color fields and reduced palette
posterized = s.reduce_palette(image=image, palette=color_palette, dither=False)
# create image with dithered color fields and reduced palette
dithered = s.reduce_palette(image=image, palette=color_palette, dither=True)
```
Sample Images

![Posterized Image](./portrait-pilot_posterized.png)
![Dithered Image](./portrait-pilot_dithered.png)

### `writeEPD(image, sleep=True, partial=False)`

Write `image` to the EPD and resets the monotonic `update` timer property.

#### Args

* `image`:`PIL.Image` object that matches the resolution of the screen
* `sleep`: `bool` put the display to low power mode (deprecated and no longer has any function)
* `partial`: `bool` update only changed portions of the screen (faster, but only works with black and white pixels) (default: False) on HD screens

#### Returns 

* True on success

#### Example

```Python
from Screen import Screen
import waveshare_epd
myScreen = Screen()
myScreen.epd = "epd5in83"
myScreen.initEPD()
myScreen.writeEPD('./my_image.png')
```

## *Class* `Screen.Update()`

Create a monotonically aware object that records the passage of time. Monotonic time objects track the absolute passage of time rather than the clock time. The `Update` objects know how long ago they were created and the last time they were updated, but are completely unaware of clock time.

### Properties

* `age` (float): age in seconds since creation
* `now` (float): time in [CLOCK_MONOTONIC](https://linux.die.net/man/3/clock_gettime) time
* `last_updated` (float): time in seconds since last updated
* `update` (bool): True - trigger resets last_updated time

### **Methods**

*****

### `update(update=True)`

#### Args

* `update` (bool): reset the last_updated timer to zero

#### Returns

* None

#### Example

```Python
>>> import Screen
>>> u = Screen.Update()
>>> u.now
79723.444216334
>>> u.last_updated
4.211982905995683
>>> u.update()
>>> u.last_updated
2.484465518995421
```

### `close_spi()`

Close the most recently opened SPI file handles. 

#### Args

* None

#### Returns

* None

### `module_exit()`

Shutdown the interface completely

    Note: it is necessary to completely reinit non HD interfaces after calling this method.
    This should primarily be used to completely shutdown the interface at the end of
    program execution.

#### Args

* None

#### Returns

* None


## *Class* `Screen.ScreenShot(path='./', n=2, prefix=None)`

Capture a rolling set of screenshots. When the total number of screenshots exceeds `n` the oldest is deleted. Images are stored as .png.

This is useful for debugging over time.

### Properties

* `total` (int): total number of screenshots to keep
* `prefix` (str): prefix to add to filenames
* `time` (str): time in format: %y-%m-%d_%H%M.%S - 2020-02-29_1456.39
* `img_array` (list): list of files stored in `path`

### **Methods**

*****

###  `delete(img)`: 

deletes specified image

#### Args

* `img` (Path): path to file to delete

#### Returns

* None

### `save(img)`

Saves img immediately

#### Args

* `img` (Path): path to save image
<!-- #endregion -->

#### Returns

* string of time image saved

```
import Screen
scrnShot = Screen.ScreenShot(path='/temp/', n=20)
spam = PIL.Image.new(mode='L', size=(100, 100), color=0)
scrnShot.save(spam)
```

## NOTES

Screens with cable along long edge
```text
Rotation = 0
  ┌───────────────┐
  │          (__) │
  │  `\------(oo) │
  │    ||    (__) │
  │    ||w--||    │
  └─────┬───┬─────┘
        │|||│

Rotation = 180
        │|||│
  ┌─────┴───┴─────┐
  │          (__) │
  │  `\------(oo) │
  │    ||    (__) │
  │    ||w--||    │
  └───────────────┘

```

Screens with cable along short edge
```text
Rotation = 0
  ┌───────────────┐
  │          (__) ├──
  │  `\------(oo) │--
  │    ||    (__) │--
  │    ||w--||    ├──
  └───────────────┘

Rotation = 180
  ┌───────────────┐
──┤          (__) │
--│  `\------(oo) │
--│    ||    (__) │
──┤    ||w--||    │
  └───────────────┘

```
