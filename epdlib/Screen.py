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
    """Class for interfacting with WaveShare EPD screens.
    
    `Screen` creates an object that provides methods for assembling images
    and updating a WaveShare EPD."""
        
    def __init__(self, resolution=None, elements=None, epd=None, rotation=0):
        """Constructor for Screen class.
                    
        Properties:
            resolution (tuple): resolution of screen
            epd (WaveShare EPD object)
            buffer_no_image (blank image to support writing to 3 color displays)
            
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
            s.initEPD()
            s.writeEPD(l.image)
            ```
            """
        logging.info('Screen created')
        
        if resolution:
            if isinstance(resolution, (list, tuple)):
                self.resolution = resolution
            else:
                raise TypeError('resolution must be a list-like object with a length of 2')

        if epd:
            self.epd = epd
            self.image = self.clearScreen()
            
        self.rotation = rotation
        
        self.update = Update()

    @property
    def epd(self):
        '''epd type 
        
        Sets properties:
            resolution: epd width and height (defaults to landscape)
            image: empty `PIL.Image`
            buffer_no_image: empty `epd.getbuffer(Image)` to support colored screens that require an additional image'''
        return self._epd
    
    @epd.setter
    def epd(self, epd):
        ''''''
        self._epd = epd.EPD()
        # set resolution for screen
        resolution = [epd.EPD_HEIGHT, epd.EPD_WIDTH]
        # sort to put longest dimension first for landscape layout
        resolution.sort(reverse=True)
        self.resolution = resolution
        self.image = self.clearScreen()
        self.buffer_no_image = self._epd.getbuffer(Image.new('L', self.resolution, 255))
    
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    @strict_enforce(int)
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
            self.image = self.clearScreen()
            self.buffer_no_image = self.epd.getbuffer(Image.new('L', self.resolution, 255))
    
    def clearScreen(self):
        '''Sets a clean base image for building screen layout.
        
        Returns:
            :obj:PIL.Image
        '''
        image = Image.new('L', self.resolution, 255)
        return image
    
#     def concat(self, elements=None):
#         '''Concatenate multiple image objects into a single composite image
        
#         Args:
#             elements (:obj:`list` of :obj:`ImageBlock` or `TextBlock`) - if none are
#                 provided, use the existing elements
                
#         Sets:
#             image (:obj:`PIL.Image`): concatination of all image members of `elements` 
#             last_updated (:obj: `Update`): registeres the time the images were updated
            
#         Returns:
#             image (:obj:`PIL.Image`)
#         '''
#         self.image = self.clearScreen()
#         # register that the object has been modified
#         self.update.update = True
#         if elements:
#             elements = elements
#         else:
#             elements = self.elements
            
#         for e in elements:
#             logging.debug(f'pasting image at: {e.abs_coordinates}')
#             self.image.paste(e.image,  e.abs_coordinates)

#             logging.debug(f'pasting image at: {e.img_coordinates}')
#             self.image.paste(e.image,  e.img_coordinates)
#         return(self.image)
    
    def initEPD(self):
        '''Initialize the connection with the EPD Hat.
        
        Returns:
            bool: True if successful
        '''
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        try:
            self.epd.init()
        except Exception as e:
            logging.error(f'failed to init epd: {e}')
            
        logging.info(f'{self.epd} initialized')
        return True
    
    def clearEPD(self):
        '''Clear the EPD screen.
        
        Raises:
            UnboundLocalError: no EPD has been intialized
        
        Returns:
            bool: True if successful'''
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        try:
            self.epd.Clear();
        except Exception as e:
            logging.error(f'failed to clear epd: {e}')
        return True
    
    def writeEPD(self, image, sleep=True):
        '''Write an image to the EPD.
        
        Args:
            image (:obj:`PIL.Image`): write a PIL image to the screen 
            sleep (bool): default - True; put the EPD to low power mode when done writing
            
        Returns:
            bool: True if successful
        '''
        epd = self.epd
        # rotate the image as needed
        if self.rotation == 180 or self.rotation == -90:
            image = image.rotate(180)
    
        
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        try:
            logging.debug('writing to epd')
#             epd.display(epd.getbuffer(self.image))
            epd.display(epd.getbuffer(image))
            self.update.update()
        # if this is a 3 color display, pass a clear image as the secondary image
        except TypeError as e:
            args = inspect.getfullargspec(epd.display)
            if len(args.args) > 2:
                # send a 1x1 pixel image to the colored layer
                epd.display(epd.getbuffer(image), self.buffer_no_image)
                self.update.update()
        except Exception as e:
            logging.error(f'failed to write to epd: {e}')
            return False
        finally:
            if sleep:
                epd.sleep()
        return True
        






def main():
    # set your screent type here
    from waveshare_epd import epd5in83 as my_epd
    import Layout
    import sys
    
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
        s.initEPD()
        s.writeEPD(l.concat())
        print('refresh screen -- screen should flash and be wiped')
        s.initEPD()
        s.writeEPD(s.clearScreen())






if __name__ == '__main__':
    main()









