# epdlib v0.6

EpdLib provides an interface for creating and displaying scalable layouts that work with most of WaveShare's EPaper displays (EPD). The `Layout` module can also be used for generating layouts for any screen-buffered display that does not require fast updates. 

EpdLib provides classes for interfacing with the screen (`Screen`), building layouts that will work at any resolution (`Layout`), and blocks that are used to assemble layouts (`Block`). EpdLib makes it trivial to build a project that will work on almost any WaveShare display without worrying about the resolution or recoding the display functions.

![3x2 Sample](./docs/weather_3x2.png)

![5x5 Sample](./docs/weather_5x5.png)

EpdLib supports almost all of WaveShare's EPD screens. See the [Supported Screens](#supported-screens) below.

* 7-Color screens are supported in full color
* HD Screens are supported in 8 bit gray and support partial refresh (~1 second)
* All 2 and 3 color screens are supported in 1 bit (black and white) only

## Changes

See the [ChangeLog](./changes.md) for details

### v0.6

* Add support for 8-Color WaveShare screens to Block, Screen and Layout
* All Blocks and Layouts now support "RGB" content
* Layouts and blocks can now be dynamically updated during runtime
* `Layout.layout` dictionaries must contain key `type` that matches the block type
* Layouts support HTML standard color names and map [RED, ORANGE, YELLOW, GREEN, BLUE, BLACK, WHITE] to proper WaveShare Values

## Dependencies

Python Modules:
* Pillow: System dependencies for Pillow:
    * libopenjp2-7
    * libtiff5
* RPi.GPIO
* spidev: ensure SPI is enabled on the pi
* waveshare-epd (Non IT8951 based panels): see [notes](#notes) below for installation instructions
    * this is for interacting with waveshare epaper displays and is not strictly needed to use the Block and Layout objects.
* IT8951 (IT8951 based panels): see [notes](#notes) below for installation instructions


## Modules:

* [Block](./docs/Block.md) - image and text blocks that can be used to create a layout
* [Layout](./docs/Layout.md) - create layouts from Blocks that will work on nearly any WaveShare screen automagically
* [Screen](./docs/Screen.md) - simple interface for writing to WaveShare EPD devices

## Supported Screens


|Screen            |Supported      |Mode          |
|:-----------------|:--------------|:-------------|
|00. epd13in3k     |True           |"1" 1 bit     |
|01. epd1in02      |True           |"1" 1 bit     |
|02. epd1in54      |True           |"1" 1 bit     |
|03. epd1in54_V2   |True           |"1" 1 bit     |
|04. epd1in54b     |True           |"1" 1 bit     |
|05. epd1in54b_V2  |True           |"1" 1 bit     |
|06. epd1in54c     |True           |"1" 1 bit     |
|07. epd1in64g     |True           |"1" 1 bit     |
|08. epd2in13      |True           |"1" 1 bit     |
|09. epd2in13_V2   |True           |"1" 1 bit     |
|10. epd2in13_V3   |True           |"1" 1 bit     |
|11. epd2in13_V4   |True           |"1" 1 bit     |
|12. epd2in13b_V3  |True           |"1" 1 bit     |
|13. epd2in13b_V4  |True           |"1" 1 bit     |
|14. epd2in13bc    |True           |"1" 1 bit     |
|15. epd2in13d     |False          |Unsupported   |
|16. epd2in13g     |True           |"1" 1 bit     |
|17. epd2in36g     |True           |"1" 1 bit     |
|18. epd2in66      |True           |"1" 1 bit     |
|19. epd2in66b     |True           |"1" 1 bit     |
|20. epd2in66g     |True           |"1" 1 bit     |
|21. epd2in7       |True           |"1" 1 bit     |
|22. epd2in7_V2    |True           |"1" 1 bit     |
|23. epd2in7b      |True           |"1" 1 bit     |
|24. epd2in7b_V2   |True           |"1" 1 bit     |
|25. epd2in9       |True           |"1" 1 bit     |
|26. epd2in9_V2    |True           |"1" 1 bit     |
|27. epd2in9b_V3   |True           |"1" 1 bit     |
|28. epd2in9b_V4   |True           |"1" 1 bit     |
|29. epd2in9bc     |True           |"1" 1 bit     |
|30. epd2in9d      |False          |Unsupported   |
|31. epd3in0g      |True           |"1" 1 bit     |
|32. epd3in52      |True           |"1" 1 bit     |
|33. epd3in7       |False          |Unsupported   |
|34. epd4in01f     |True           |"RGB" 7 Color |
|35. epd4in2       |False          |Unsupported   |
|36. epd4in26      |True           |"1" 1 bit     |
|37. epd4in2_V2    |False          |Unsupported   |
|38. epd4in2b_V2   |True           |"1" 1 bit     |
|39. epd4in2bc     |True           |"1" 1 bit     |
|40. epd4in37g     |True           |"1" 1 bit     |
|41. epd5in65f     |True           |"RGB" 7 Color |
|42. epd5in83      |True           |"1" 1 bit     |
|43. epd5in83_V2   |True           |"1" 1 bit     |
|44. epd5in83b_V2  |True           |"1" 1 bit     |
|45. epd5in83bc    |True           |"1" 1 bit     |
|46. epd7in3f      |True           |"RGB" 7 Color |
|47. epd7in3g      |True           |"1" 1 bit     |
|48. epd7in5       |True           |"1" 1 bit     |
|49. epd7in5_HD    |True           |"1" 1 bit     |
|50. epd7in5_V2    |True           |"1" 1 bit     |
|51. epd7in5_V2_old|True           |"1" 1 bit     |
|52. epd7in5b_HD   |True           |"1" 1 bit     |
|53. epd7in5b_V2   |True           |"1" 1 bit     |
|54. epd7in5bc     |True           |"1" 1 bit     |
|55. All HD IT8951 |True           |"L" 8 bit     |

Add your enthusiasm to standardize the `epd1in02` screen to [this Pull Request](https://github.com/waveshare/e-Paper/pull/283). 

The `epd3in7` is an oddball that has several issues:

* 'Non-standard, unsupported `EPD.Clear()` function',
* 'AttributeError: module does not support standard `EPD.display()` function

## Notes

### WaveShare non-IT8951 Screens

The waveshare-epd library is required for non-IT8951 screens and can be installed from the Git repo:

```Shell
pip install -e "git+https://github.com/waveshare/e-Paper.git#egg=waveshare_epd&subdirectory=RaspberryPi_JetsonNano/python"
```

### IT8951 basee Screens

[Greg D Meyer's IT8951 library](https://github.com/GregDMeyer/IT8951) is required and can be installed from the Git repo:

```Shell
pip install -e "git+https://github.com/GregDMeyer/IT8951#egg=IT8951"
```


getting ready for pypi:
https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56


