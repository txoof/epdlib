#!/usr/bin/env python
#!/usr/bin/env python
# coding: utf-8


# In[1]:


#get_ipython().run_line_magic('alias', 'nbconvert nbconvert ./Screen.ipynb')

#get_ipython().run_line_magic('nbconvert', '')




# In[2]:


import logging
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
from pathlib import Path




# In[3]:


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




# In[4]:


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




# In[5]:


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
        self.update = True
        
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
    
    @last_updated.setter
    def update(self, update=True):
        """update the object
        
        Args:
            update(boolean): True updates object"""
        if update:
            self._last_updated = self.now
    




# In[3]:


class Screen:
    """Class for interfacting with WaveShare EPD screens.
    
    `Screen` creates an object that provides methods for assembling images
    and updating a WaveShare EPD."""
        
    def __init__(self, resolution=None, elements=None, epd=None):
        """Constructor for Screen class.
                    
        Properties:
            resolution (tuple): resolution of screen
            epd (WaveShare EPD object)
            
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
            s.concat()
            # init and write the composite to the EPD
            s.initEPD()
            s.writeEPD()
            ```
            """
        logging.info('Screen created')
#         self.resolution = resolution
        self.elements = elements
        
        if resolution:
            if isinstance(resolution, (list, tuple)):
                self.resolution = resolution
            else:
                raise TypeError('resolution must be a list-like object with a length of 2')

        if epd:
            self.epd = epd
            self.image = self.clearScreen()
            
        self.update = Update()
    
    @property
    def epd(self):
        return self._epd
    
    @epd.setter
    def epd(self, epd):
        self._epd = epd.EPD()
        # set resolution for screen
        resolution = [epd.EPD_HEIGHT, epd.EPD_WIDTH]
        # sort to put longest dimension first for landscape layout
        resolution.sort(reverse=True)
        self.resolution = resolution
        self.image = self.clearScreen()
    
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
            image (:obj:`PIL.Image`, optional): if none is provided use object `image`
            sleep (bool): default - True; put the EPD to low power mode when done writing
            
        Returns:
            bool: True if successful
        '''
        epd = self.epd
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
        try:
            epd.display(epd.getbuffer(self.image))
            self.update.update = True
            if sleep:
                epd.sleep()
        except Exception as e:
            logging.error(f'failed to write to epd: {e}')
            return False
        return True
        


