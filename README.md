# epdlib v0.6

EpdLib provides an interface for creating and displaying scalable layouts that work with most of WaveShare's EPaper displays (EPD). The `Layout` module can also be used for generating layouts for any screen-buffered display that does not require fast updates. 

EpdLib provides classes for interfacing with the screen (`Screen`), building layouts that will work at any resolution (`Layout`), and blocks that are used to assemble layouts (`Block`). EpdLib makes it trivial to build a project that will work on almost any WaveShare display without worrying about the resolution or recoding the display functions.

![3x2 Sample](./docs/weather_3x2.png)

![5x5 Sample](./docs/weather_5x5.png)

EpdLib supports almost all of WaveShare's EPD screens. See the [Supported Screens](#supported-screens) below.

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

Generally, the following features are available:

| Screen Type*                    | Basic Support | Color | Grayscale | Partial Refresh |
|---------------------------------|---------------|-------|-----------|-----------------|
| 16 Gray Scale (HD IT8951)       | ✅             | ➖     | ✅         | ✅ (~1 second)   |
| E6 Full Color                   | ✅             | ❌     | ➖         | ➖               |
| 7-Color                         | ✅             | ✅     | ➖         | ➖               |
| 4-Color                         | ✅             | ❌     | ➖         | ➖               |
| 3-Color                         | ✅             | ❌     | ➖         | ➖               |
| Black & White                   | ✅             | ➖     | ➖         | ❌               |
| Black & White, <br>4 Gray Scale | ✅             | ➖     | ✅         | ❌               |

\* Please see [Waveshare's website](https://www.waveshare.com/2.7inch-e-Paper-HAT.htm#tab-wiki) for a list of available
devices and their types.

✅ = Supported by epdlib  
❌ = Not supported by epdlib   
➖ = Not available on this screen type  

### Screen List

|Screen              |Supported |Mode                |
|:-------------------|:---------|:-------------------|
|00. epd13in3b       |True      |"1" 1 bit b/w       |
|01. epd13in3k       |True      |"L" 2 bit grayscale |
|02. epd1in02        |True      |"1" 1 bit b/w       |
|03. epd1in54        |True      |"1" 1 bit b/w       |
|04. epd1in54_V2     |True      |"1" 1 bit b/w       |
|05. epd1in54b       |True      |"1" 1 bit b/w       |
|06. epd1in54b_V2    |True      |"1" 1 bit b/w       |
|07. epd1in54c       |True      |"1" 1 bit b/w       |
|08. epd1in64g       |True      |"1" 1 bit b/w       |
|09. epd2in13        |True      |"1" 1 bit b/w       |
|10. epd2in13_V2     |True      |"1" 1 bit b/w       |
|11. epd2in13_V3     |True      |"1" 1 bit b/w       |
|12. epd2in13_V4     |True      |"1" 1 bit b/w       |
|13. epd2in13b_V3    |True      |"1" 1 bit b/w       |
|14. epd2in13b_V4    |True      |"1" 1 bit b/w       |
|15. epd2in13bc      |True      |"1" 1 bit b/w       |
|16. epd2in13d       |True      |"1" 1 bit b/w       |
|17. epd2in13g       |True      |"1" 1 bit b/w       |
|18. epd2in15b       |True      |"1" 1 bit b/w       |
|19. epd2in15g       |True      |"1" 1 bit b/w       |
|20. epd2in36g       |True      |"1" 1 bit b/w       |
|21. epd2in66        |True      |"1" 1 bit b/w       |
|22. epd2in66b       |True      |"1" 1 bit b/w       |
|23. epd2in66g       |True      |"1" 1 bit b/w       |
|24. epd2in7         |True      |"L" 2 bit grayscale |
|25. epd2in7_V2      |True      |"L" 2 bit grayscale |
|26. epd2in7b        |True      |"1" 1 bit b/w       |
|27. epd2in7b_V2     |True      |"1" 1 bit b/w       |
|28. epd2in9         |True      |"1" 1 bit b/w       |
|29. epd2in9_V2      |True      |"L" 2 bit grayscale |
|30. epd2in9b_V3     |True      |"1" 1 bit b/w       |
|31. epd2in9b_V4     |True      |"1" 1 bit b/w       |
|32. epd2in9bc       |True      |"1" 1 bit b/w       |
|33. epd2in9d        |True      |"1" 1 bit b/w       |
|34. epd3in0g        |True      |"1" 1 bit b/w       |
|35. epd3in52        |True      |"1" 1 bit b/w       |
|36. epd3in7         |False     |Unsupported         |
|37. epd4in01f       |True      |"RGB" Color         |
|38. epd4in2         |True      |"L" 2 bit grayscale |
|39. epd4in26        |True      |"L" 2 bit grayscale |
|40. epd4in2_V2      |True      |"L" 2 bit grayscale |
|41. epd4in2b_V2     |False     |Unsupported         |
|42. epd4in2b_V2_old |False     |Unsupported         |
|43. epd4in2bc       |True      |"1" 1 bit b/w       |
|44. epd4in37g       |True      |"1" 1 bit b/w       |
|45. epd5in65f       |True      |"RGB" Color         |
|46. epd5in79        |True      |"L" 2 bit grayscale |
|47. epd5in79b       |True      |"1" 1 bit b/w       |
|48. epd5in79g       |True      |"1" 1 bit b/w       |
|49. epd5in83        |True      |"1" 1 bit b/w       |
|50. epd5in83_V2     |True      |"1" 1 bit b/w       |
|51. epd5in83b_V2    |True      |"1" 1 bit b/w       |
|52. epd5in83bc      |True      |"1" 1 bit b/w       |
|53. epd7in3e        |True      |"1" 1 bit b/w       |
|54. epd7in3f        |True      |"RGB" Color         |
|55. epd7in3g        |True      |"1" 1 bit b/w       |
|56. epd7in5         |True      |"1" 1 bit b/w       |
|57. epd7in5_HD      |True      |"1" 1 bit b/w       |
|58. epd7in5_V2      |True      |"L" 2 bit grayscale |
|59. epd7in5_V2_old  |True      |"1" 1 bit b/w       |
|60. epd7in5b_HD     |True      |"1" 1 bit b/w       |
|61. epd7in5b_V2     |True      |"1" 1 bit b/w       |
|62. epd7in5b_V2_old |True      |"1" 1 bit b/w       |
|63. epd7in5bc       |True      |"1" 1 bit b/w       |
|64. All HD IT8951   |True      |"L" 8 bit grayscale |

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


