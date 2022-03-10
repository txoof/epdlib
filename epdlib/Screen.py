#!/usr/bin/env python3
# coding: utf-8








import logging
from PIL import Image, ImageDraw
from datetime import datetime
from pathlib import Path
import time
import omni_epd
from omni_epd import displayfactory, EPDNotFoundError





def strict_enforce(*types):
    """decorator: strictly enforce type compliance within classes
    
    Usage:
    @strict_enforce(type1, type2, (type3, type4))
    def foo(val1, val2, val4):
        ...
    """
    def decorator(f):
        def new_f(self, *args, **kwds):
            #we need to convert args into something mutable   
            newargs = []        
            for (a, t) in zip(args, types):
                if not isinstance(a, t):
                    raise TypeError(f'"{a}" is not type {t}')
                # newargs.append( t(a)) #feel free to have more elaborated convertion
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






class ScreenError(Exception):
    '''general exception for Screen obj errors'''
    pass






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
    
    def __repr__(self):
        return str(self.age)
    
    def __init__(self):
        '''constructor for Update class
        
        Properties:
            start (float): floating point number in CLOCK_MONOTONIC time.
                this is a fixed point in time the object was created
            update (boolean): indicates that the object has been updated'''
            
        self.start = self.now
        self.update()
    
    def __str__(self):
        return str(f'{self.last_updated:.2f} seconds old')
    
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
    
    # @last_updated.setter
    def update(self):
        """update the object   
        Args:
            update(boolean): True updates object"""
        self._last_updated = self.now
    






class Screen():
    '''E-Paper screen object for calling init, write and clear functions.
    Most WaveShare SPI screens including HD IT8951 base screens are supported.
    Use `Screen().list_compatible()` to show all compatible screens.
    
    Screen() objects are aware of:
        * attached screen resolution
        * pixel depth (1 or 8 bit) -- bi-color screens are only supported in 1 bit mode (no color)
        * age since creation (monotonic time)
        * time since last updated with write or clear (monotonic time)
    '''
    def __init__(self, epd=None, rotation=0, vcom=None):
        '''create Screen() object
        
        Args:
            epd(str): name of epd (use Screen().list_compatible() to view a list)
            rotation(int): 0, -90, 90, 180 rotation of screen
            vcom(float): negative float vcom value from panel ribon cable
            
        Properties:
            resolution(list): X x Y pixels
            HD(bool): True for IT8951 panels
            constants(namespace): constants required for read/write of IT8951 screens
            mode(str): current mode of the image (check modes_available for options on each screen)
            mode(tuple): modes available for the selected screen
            update(obj:Update): monotoic time aware update timer'''

        self.vcom = vcom
        self.resolution = [1, 1]
        self.HD = False
        self.constants = None
        self.mode = '1'
        self.screen_mode = 'bw'
        self.modes_available = ('bw')
        self.epd = epd
        self.rotation = rotation
        self.update = Update()


    def _spi_handler(func):
        '''manage SPI file handles and wake/sleep displays
        
        for IT8951 HD displays, wake the driver board, run the passed function, sleep the driver
        
        for non-IT8951 displays, init the SPI bus, run the passed function, sleep and close SPI handles
        
        Args:
            func(function): function to be run'''
        def wrapper(*args, **kwargs):
            # self
            obj = args[0]
            if not obj.epd:
                raise UnboundLocalError('no epd is configured')

            logging.debug('initing display')
            # open the SPI file objects
            try:
                obj.epd.prepare()
            except FileNotFoundError as e:
                raise FileNotFoundError(f'It appears SPI is not enabled on this Pi: {e}')
            except Exception as e:
                raise ScreenError(f'failed to init display: {e}')
            
            # run the SPI read/write command here
            func(*args, **kwargs)
            obj.update.update()    
            
            logging.debug('sleeping display')
            # close the SPI file objects
            try:
                obj.epd.sleep()
            except Exception as e:
                raise ScreenError(f'failed to sleep display: {e}')
            
        return wrapper


    @property
    def epd(self):
        return self._epd


    @epd.setter
    @strict_enforce((type(None), str))
    def epd(self, epd):
        '''configures epd display for use
        
        use `Screen().list_compatible_modules()` to see a list of supported screens
        
        Args:
            epd(str): name of epd module
        
        Sets:
            epd(obj): epd read/write object
            resolution(list): resolution of screen
            constants(namespace): constants required for read/write of IT8951 screens
            HD(bool): True for IT8951 based screens
            mode(str): "1" or "L" (note this does not override the mode if already set)'''
        
        if not epd or epd.lower == 'none':
            self._epd = None
            return
        
        myepd = self._loadEPD(epd)
        
        if not myepd:
            self._epd = None
            return
        
        if len(myepd.modes_available) > 1:
            self.mode = "1" # This will eventually support color
        else:
            self.mode = "1"

        self._epd = myepd
        self.resolution = [myepd.height, myepd.width]

        if 'it8951' in epd:
            self.constants = myepd.it8951_constants
        logging.debug(f'epd configuration {myepd}')


    @property 
    def vcom(self):
        return self._vcom


    @vcom.setter
    @strict_enforce((int, float, type(None)))
    def vcom(self, vcom):
        if not vcom:
            self._vcom = None
        elif 0 < vcom or vcom < -5 :
            raise ValueError('vcom must between 0 and -5')
        else:
            self._vcom = vcom


    @property
    def rotation(self):
        '''rotation of screen
        
        Valid values are 0, 90, 180, 270, -90'''
        return self._rotation


    @rotation.setter
    @strict_enforce(int)
    def rotation(self, rotation):
        if not self.epd:
            self._rotation = rotation
            return
        
        if rotation not in [-90, 0, 90, 180, 270]:
            raise ValueError(f'valid rotation values are [-90, 0, 90, 180, 270]')
        
        if rotation in [90, -90, 270]:
            resolution = self.resolution
            resolution.sort()
            self.resolution = resolution
        else:
            resolution = self.resolution
            resolution.sort(reverse=True)
            self.resolution = resolution

        self._rotation = rotation
        logging.debug(f'rotation={rotation}, resolution={self.resolution}')        


    def _loadEPD(self, epd):
        '''configure epd
        
        For a complete list see the list_compatible_modules() functon
        
        Args:
            epd(str): name of EPD module to load
            
        Returns:
            myepd: epd object, 
        '''
        logging.debug(f'configuring omni_edp.{epd}')
        supported_devices = displayfactory.list_supported_displays()
        if epd in supported_devices:
            try:
                myepd = displayfactory.load_display_driver(epd)
            except EPDNotFoundError:
                print(f"Couldn't find {epd}")
                sys.exit()
        else:
            raise ScreenError(f'unrecongized screen model: {epd}')

        if 'it8951' in epd:
            myepd.HD = True

        return myepd
    
    
    def blank_image(self):
        '''retrun a PIL image that is entirely blank that matches the resolution of the screen'''
        return Image.new(self.mode, self.resolution, 255)     
    

    @_spi_handler
    def clearEPD(self):
        '''wipe epd screen entirely'''
        logging.debug('clearing screen')
        self.epd.clear()


    @_spi_handler
    def writeEPD(self, image, partial=False):
        '''write an image to the screen 
        
        Args:
            image(PIL image): image to display
            partial(bool): attempt to do a partial refresh -- for 1bit pixels on HD Screens only'''

        try:
            image = image.rotate(self.rotation, expand=True)
        except AttributeError as e:
            raise ScreenError(f'image could not be rotated: {e}')

        if partial:
            if self.HD:
                write_function = self._partial_writeEPD_hd
            else:
                logging.warning('partial update is not available on non-hd displays')
                write_function = self.epd.display

            # THIS IS THE CODE THAT I HOPE WILL REPLACE THE ABOVE 'IF' BLOCK - REQUIRES OMNI-EPD CHANGE
            # write_function = self.epd.display_partial
        else:
            write_function = self.epd.display

        write_function(image)
        
        return True
    

    def _partial_writeEPD_hd(self, image):  # This will be obsoleted once partial updates are added to Omni-EPD
        '''partial update, affects only those changed black and white pixels with no flash/wipe

        uses waveform DU see: see: https://www.waveshare.net/w/upload/c/c4/E-paper-mode-declaration.pdf for display modes
        '''
        try:
            pass
        except Exception as e:
            raise ScreenError(f'failed to write partial update to display: {e}')
        self.epd.frame_buf = image
        self.epd.draw_partial(self.constants.DisplayModes.DU)
    
    @staticmethod
    def list_compatible():
        list_compatible_modules()
        
    def close_spi(self):
        '''close the most recently opened SPI file handles'''
        if self.HD:
            try:
                self.epd.epd.spi.__del__()
            except OSError:
                logging.info('there are no handles that are closable')
        else:
            self.epd.sleep()


def list_compatible_modules(print_modules=True):
    '''
    list compatible waveshare EPD modules
    
    This list pulls from Omni-EPD's list_supported_displays() method
    '''

    panels = []
    panels = displayfactory.list_supported_displays()

    if print_modules:
        print(f'NN. Screen          (manufact.)')
        print( '-------------------------------')
        for idx, screen in enumerate(panels):
            print(f"{idx:02d}. {screen.split('.')[1]:<15s} ({screen.split('.')[0][slice(0, 9)]})")
         
    return panels


def main():
    '''run a demo/test of attached EPD screen showing rotations and basic writing'''
    import pkgutil
    import sys

    print('loading Layout module')
    try:
        from epdlib import Layout
        from epdlib import constants
    except ModuleNotFoundError:
        try:
            print('trying alternative module')
            from Layout import Layout
            import constants
        except ModuleNotFoundError:
            sys.exit('failed to import')

    panels = []
    panels = list_compatible_modules()

    choice = input('Enter the number of your choice: ')
    
    try:
        choice = int(choice)
    except ValueError as e:
        print(f'"{choice}" does not appear to be an valid choice. Exiting.')
        return
    myepd = panels[choice]
    
    if choice > len(panels)+1:
        print(f'"{choice}" is not a valid panel option. Exiting.')
        return
    
    if 'it8951' in myepd:
        voltage = input('Enter the vcom voltage for this panel (check the ribbon cable): ')
        try:
            voltage = float(voltage)
        except ValueError as e:
            print('vcom voltage must be a negative float. Exiting')
            return
        if voltage > 0:
            print('vcom voltage must be a negative float. Exiting.')
            return
    else:
        voltage = 0.0

    myLayout = {
        'title': {                       # text only block
            'type': 'TextBlock',         # required as of v0.6
            'image': None,               # do not expect an image
            'max_lines': 3,              # number of lines of text
            'width': 1,                  # 1/1 of the width - this stretches the entire width of the display
            'height': .6,                # 1/3 of the entire height
            'abs_coordinates': (0, 0),   # this block is the key block that all other blocks will be defined in terms of
            'hcenter': True,             # horizontally center text
            'vcenter': True,             # vertically center text 
            'relative': False,           # this block is not relative to any other. It has an ABSOLUTE position (0, 0)
            'font': str(constants.absolute_path/'../fonts/Font.ttc'), # path to font file
            'font_size': None,            # Calculate the font size because none was provided
        },
        'artist': {
            'type': 'TextBlock',
            'image': None,
            'max_lines': 2,
            'width': 1,
            'height': .4,
            'abs_coordinates': (0, None),   # X = 0, Y will be calculated
            'hcenter': True,
            'vcenter': True,
            'font': str(constants.absolute_path/'../fonts/Font.ttc'),
            'relative': ['artist', 'title'], # use the X postion from abs_coord from `artist` (this block: 0)
                                            # calculate the y position based on the size of `title` block
        }
    }    
    
    print(f"using font: {myLayout['title']['font']}")
    s = Screen(epd=myepd, vcom=voltage)
    
    for r in [0, 90, -90, 180]:
        print(f'setup for rotation: {r}')
        s.rotation = r

        l = Layout(resolution=s.resolution)
        l.layout = myLayout
        l.update_contents({'title': 'item: spam, spam, spam, spam & ham', 'artist': 'artist: monty python'})
        print('print some text on the display')

        try:
            s.writeEPD(l.concat())
        except FileNotFoundError as e:
            print(f'{e}')
            print('Try: $ raspi-config > Interface Options > SPI')
            do_exit = True
        else:
            do_exit = False
        
        if do_exit:
            sys.exit()
        print('sleeping for 2 seconds')
        time.sleep(2)


        print('refresh screen -- screen should flash and be refreshed')
    
    print('clear screen')
    s.clearEPD()


logger = logging.getLogger(__name__)
# logger.root.setLevel('DEBUG')

if __name__ == '__main__':
    e= main()


