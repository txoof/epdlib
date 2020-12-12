#!/usr/bin/env python3
# coding: utf-8






import logging
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
from pathlib import Path
import inspect






def strict_enforce(*types):
    """strictly enforce type compliance within classes
    
    Usage:
        @strict_enforce(type1, type2, (type3, type4))
        def foo(val1, val2, val3):
            ...
    """
    def decorator(f):
        def new_f(self, *args, **kwds):
            #we need to convert args into something mutable   
            newargs = []        
            for (a, t) in zip(args, types):
                if not isinstance(a, t):
                    raise TypeError(f'"{a}" is not type {t}')
#                 newargs.append( t(a)) #feel free to have more elaborated convertion
            return f(self, *args, **kwds)
        return new_f
    return decorator






class ScreenShot:
    """capture a rolling set of `n` screenshots into specified directory"""
    def __init__(self, path='./', n=2, prefix=None):
        """constructor method 
        Properties:
            path (:str:): location to save screenshots - default: './'
            n (:int:): number of screenshots to keep - default: 2
            img_array (:obj:list of :obj: `Path`): list of existing files
            """
        self.total = n
        self.path = Path(path).expanduser().resolve()
        self.prefix = prefix
        
    
    @property
    def total(self):
        """total number of screenshots to save
        Attribute:
            n (int): integer >= 1
        Rasises:
            TypeError - n must be integer
            ValueError - n must be positive"""
        return self._total
    
    @total.setter
    @strict_enforce(int)
    def total(self, n):
        if n < 1:
            raise ValueError(f'`n` must be >= 1')
    
        self._total = n
        self.img_array = []

    def time(self): 
        """returns time string in the format YY-MM-DD_HHMM.SS - 70-12-31_1359.03"""
        return datetime.now().strftime("%y-%m-%d_%H%M.%S")
        
    def delete(self, img):
        """deletes `img`
        Attributes:
            img (:obj: `Path`): unilinks/deletes the path"""
        logging.debug(f'removing image: {img}')
        try:
            img.unlink()
        except Exception as e:
            logging.error(e)
        pass
        
    def save(self, img):
        """saves the most recent `n` images, deleting n+1 older image
        
        Attributes:
            img (:obj: PIL.Image.Image): image to save
        Raises:
            TypeError - img must be of type Image.Image"""
        if not isinstance(img, Image.Image):
            raise TypeError(f'`img` must be of type Image.Image')
            
        filename = self.time() + '.png'
        
        if self.prefix:
            filename = prefix + filename

        filepath = self.path / filename
        logging.debug(f'writing image: {filepath}')
        img.save(filepath)
        self.img_array.insert(0, filepath)
        if len(self.img_array) > self.total:
            self.delete(self.img_array.pop())






class Update:
    """Class for creating a montotonicaly aware object that records passage of time
    
    create an update aware object:
        myObj = Update()
        
    Time since creation:
        myObj.age
        
    Time since last updated:
        myObj.last_updated
        
    
    Update the object:
        myObj.update = True"""
    
    def __init__(self):
        '''constructor for Update class
        
        Properties:
            start (float): floating point number in CLOCK_MONOTONIC time.
                this is a fixed point in time the object was created
            update (boolean): indicates that the object has been updated'''
            
        self.start = self.now
        self.update()
        
    @property
    def age(self):
        """age of the object in seconds since created"""
        return self.now - self.start
    
    @property
    def now(self):
        """time in CLOCK_MONOTONIC time"""
        return time.clock_gettime(time.CLOCK_MONOTONIC)
    
    @property
    def last_updated(self):
        """seconds since object was last updated"""
        return self.now - self._last_updated
    
#     @last_updated.setter
    def update(self):
        """update the object   
        Args:
            update(boolean): True updates object"""
        self._last_updated = self.now
    






class Screen:
    '''Class for interfacing with WaveShare EPD Screens
    
    `Screen` creates an object that provides methods for writing images
    and updating a WaveShare EPD.
    '''
    
    def __init__(self, epd=None, rotation=0):
        '''constructor for Screen class
        
        Properties:
            resolution(`tuple` of `int`): resolution of screen (defaults to landscape orientation)
            blank_image(`Pil` Image): white image
        

        
        Args:
            epd(`waveshare EPD class`): imported waveshare epd class
            rotation(`int`): 0, 90, -90, 180 rotation of screen

        Examples:
        * Create a screen object:
            ```
            import waveshare_epd
            s = Screen()
            s.epd = wavehsare_epd.epd5in83
            ```
        * Create and write a composite image from a layout object
            - See `help(Layout)` for more information
            ```
            # create layout object using a predefined layout
            import Layout
            import layouts
            l = Layout(resolution=(s.epd.EPD_WIDTH, s.epd.EPD_HEIGHT), layout=layouts.splash)
            # update the layout information
            u = {'version': 'version 0.2.1', 'url': 'https://github.com/txoof/slimpi_epd', 'app_name': 'slimpi'}\
            l.update_contents(u)
            # update the screen object with the layout block values
            s.elements = l.blocks.values()
            # create a composite imate from all the blocks
            l.concat()
            # init and write the composite to the EPD
            s.writeEPD(l.image)
        
        '''
        self.epd = epd
        self.rotation = rotation
        self.update = Update()
        
    
    @property
    def epd(self):
        '''epd type'''
        return self._epd
    
    @epd.setter
    def epd(self, epd):
        if epd:
            self._epd = epd.EPD()
            resolution = [epd.EPD_HEIGHT, epd.EPD_WIDTH]
            resolution.sort(reverse=True)
            self.resolution = resolution
            # set a blank image as default
            self.image = Image.new('L', self.resolution, 255)
            # create an empty buffer for using with two color screens
            self.buffer_no_image = self.epd.getbuffer(self.blank_image())
            
            # set kwargs for screens that expect `color` and `mode` arguments
            clear_args_spec = inspect.getfullargspec(self._epd.Clear)
            self.clear_args = {}
            if 'color' in clear_args_spec.args:
                self.clear_args['color'] = 0xFF
            if 'mode' in clear_args_spec.args:
                self.clear_args['mode'] = 0
                
            display_args_spec = inspect.getfullargspec(self._epd.display)
            if len(display_args_spec.args) > 2:
                self._one_bit_display = False
            else:
                self._one_bit_display = True
        else: 
            self._epd = None
            self.resolution = (1, 1)

    @property 
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, rotation):
        '''
        set the display rotation
        Sets or resets properties:
            rotation(`int`): [0, 90, -90, 180]
            resolution: sets resolution to match rotation (width/height)
            image: empty `PIL.Image`
            buffer_no_image: empty `epd.getbuffer(Image)` to support colored screens that require an additional image 
        '''
            
        if rotation not in [0, 90, -90, 180]:
            raise ValueError('value must be type `int` and [0, 90, -90, 180]')
        self._rotation = rotation
        logging.debug(f'Screen rotation set to: {self._rotation}')
        if rotation == 90 or rotation == -90:
                
            resolution = self.resolution
            # set short dimension first
            resolution.sort()
            # set resolution
            self.resolution = resolution
            # set a new clearscreen image
            self.image = Image.new('L', self.resolution, 255)
            self.buffer_no_image = self.epd.getbuffer(self.blank_image())
    
    def blank_image(self):
        return Image.new('L', self.resolution, 255)
        
    def initEPD(self):
        '''init the EPD for writing'''
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        try:
            self.epd.init()
        except Exception as e:
            logging.error(f'failed to init epd: {e}')
        else:
            logging.info(f'{self.epd} initialized')
        return True
    
    def clearEPD(self):
        '''clear the epd screen
        
        inits the screen and then sets it to blank (all white)'''
        
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        try:
            self.initEPD()
            self.epd.Clear(**self.clear_args)
        except Exception as e:
            logging.error(f'failed to clear epd: {e}')
            return False
        return True
    
    def writeEPD(self, image=None, sleep=True):
        '''write an image to EPD
        
        Args:
        image(Pil image or Image file): image to display
        sleep(bool): put the display to sleep after writing (default True)'''
        logging.debug('preparing to write to EPD')
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        
        ret_val = False
        
        if self.rotation == 180 or self.rotation == -90:
            if image:
                try:
                    image = image.rotate(180)
                except AttributeError as e:
                    logging.info(f'image is unset, cannot rotate, skipping')
        
        if image:
            try:
                image_buffer = self.epd.getbuffer(image)
            except AttributeError as e:
                logging.warning(f'{e} - this does not appear to be an image object')
                logging.warning('setting image to blank image')
                image_buffer = self.epd.getbuffer(self.blank_image())
            
        
            try:
                logging.debug('init and write to EPD')
                if self.initEPD():
                    if self._one_bit_display:
                        self.epd.display(image_buffer)
                    else:
                        # send a blank image for the colored layer
                        self.epd.display(image_buffer, self.buffer_no_image)
                    self.update.update()
                    ret_val = True
                else:
                    logging.warning('initEPD failed')
                    ret_val = False
            except Exception as e:
                logging.error(f'{e} - failed to write to epd')
            finally:
                if sleep:
                    self.epd.sleep()
                    
        else:
            logging.warning('no image provided -- no epd write attempted')
            
        return ret_val
            
            
        






def main():
    # set your screent type here
    try:
        import sys
        from waveshare_epd import epd5in83 as my_epd
    except FileNotFoundError as e:
        logging.error(f''''Error loading waveshare_epd module: {e}
        This is typically due to SPI not being enabled, or the current user is 
        not a member of the SPI group.
        "$ sudo raspi-config nonint get_spi" will return 0 if SPI is enabled
        Exiting...''')
        return
    import Layout
    
    sys.path.append('../')
    
    for r in [0, 90, -90, 180]:
        print(f'setup for rotation: {r}')
        s = Screen(epd=my_epd, rotation=r)
        myLayout = {
                'title': {                       # text only block
                    'image': None,               # do not expect an image
                    'max_lines': 3,              # number of lines of text
                    'width': 1,                  # 1/1 of the width - this stretches the entire width of the display
                    'height': 4/7,               # 1/3 of the entire height
                    'abs_coordinates': (0, 0),   # this block is the key block that all other blocks will be defined in terms of
                    'hcenter': True,             # horizontally center text
                    'vcenter': True,             # vertically center text 
                    'relative': False,           # this block is not relative to any other. It has an ABSOLUTE position (0, 0)
                    'font': '../fonts/Font.ttc', # path to font file
                    'font_size': None            # Calculate the font size because none was provided
                },

                'artist': {
                    'image': None,
                    'max_lines': 2,
                    'width': 1,
                    'height': 3/7,
                    'abs_coordinates': (0, None),   # X = 0, Y will be calculated
                    'hcenter': True,
                    'vcenter': True,
                    'font': '../fonts/Font.ttc',
                    'relative': ['artist', 'title'], # use the X postion from abs_coord from `artist` (this block: 0)
                                                   # calculate the y position based on the size of `title` block

                }
        }    
        l = Layout.Layout(resolution=s.resolution)
        l.layout = myLayout
        l.update_contents({'title': 'spam, spam, spam, spam & ham', 'artist': 'monty python'})
        print('print some text on the display')
#         s.initEPD()
        s.writeEPD(l.concat(), sleep=False)
        print('refresh screen -- screen should flash and be refreshed')
#         s.initEPD()
#         s.writeEPD(s.clearScreen())
    s.clearEPD()
    return s






if __name__ == '__main__':
    e= main()


