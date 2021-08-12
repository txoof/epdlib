#!/usr/bin/env python3
# coding: utf-8








import logging
from PIL import Image, ImageDraw
from datetime import datetime
from pathlib import Path
import time






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
    
#     @last_updated.setter
    def update(self):
        """update the object   
        Args:
            update(boolean): True updates object"""
        self._last_updated = self.now
    






class Screen():
    '''WaveShare E-Paper screen object for standardizing init, write and clear functions.
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
            clear_args(dict): kwargs dict of any additional kwargs that are needed for clearing a display
            buffer_no_image(PIL:Image): "blank" image for clearing bi-color panels (empty for all others)
            vcom(float): negative vcom voltage from panel ribon cable
            HD(bool): True for IT8951 panels
            rotatio(int): rotation of screen (0, -90, 90, 180)
            update(obj:Update): monotoic time aware update timer'''
        self.vcom = vcom        
        self.resolution = [1, 1]
        self.clear_args  = {}
        self.buffer_no_image = []
        self.constants = None
        self.mode = None
        self.HD = False
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
            if not obj.HD:
                logging.debug('Non HD display')
                try:
                    obj.epd.init()
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
                    
            if obj.HD:
                logging.debug('HD display')
                try:
                    obj.epd.epd.run()
                except Exception as e:
                    raise ScreenError(f'failed to init display')
                func(*args, **kwargs)
                
                logging.debug('sleeping display')
                try:
                    obj.epd.epd.sleep()
                except Exception as e:
                    raise ScreenError(f'failed to sleep display: {e}')
        # update monotonic clock 
        return wrapper
        
    @property
    def epd(self):
        return self._epd
    
    @epd.setter
    @strict_enforce((type(None), str))
    def epd(self, epd):
        '''configures epd display for use
        
        use `Screen().list_compatible_modules()` to see a list of supported non IT8951 screens
        use "HD" for IT8951 screens
        
        Args:
            epd(str): name of waveshare module, or "HD" for IT8951 based screens
        
        Sets:
            epd(obj): epd read/write object
            resolution(list): resolution of screen
            clear_args(dict): arguments required for clearing the screen
            constants(namespace): constants required for read/write of IT8951 screens
            HD(bool): True for IT8951 based screens
            mode(str): "1" or "L" (note this does not override the mode if already set)'''
        
        if not epd or epd.lower == 'none':
            self._epd = None
            return
        
        myepd = None
        
        if epd == 'HD':
            self.HD = True
            myepd = self._load_hd(epd)
        else:
            self.HD = False
            myepd = self._load_non_hd(epd)
            
        if not myepd:
            self._epd = None
            return
        
        self._epd = myepd['epd']
        self.resolution = myepd['resolution']
        self.clear_args = myepd['clear_args']
        self.constants = myepd['constants']
        self.one_bit_display = myepd['one_bit_display']
        self.mode = myepd['mode']
        
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
            
        self.image = Image.new(self.mode, self.resolution, 255)
        if not self.HD:
            self.buffer_no_image = self.epd.getbuffer(self.blank_image())

        self._rotation = rotation
        logging.debug(f'rotation={rotation}, resolution={self.resolution}')        

    def _load_hd(self, epd, timeout=20):
        '''configure IT8951 (HD) SPI epd 
        
        Args:
            epd(str): ignored; used for consistency in _load_non_hd config
        
        Returns:
            dict:
                epd: epd object, 
                resolution: [int, int],
                clear_args: [arg1: val, arg2: val],
                constants: None            
        '''
        
        from IT8951.display import AutoEPDDisplay
        from IT8951 import constants as constants_HD
        
        
        logging.debug('configuring IT8951 epd')
        
        if not self.vcom:
            raise ScreenError('`vcom` property must be provided when using "HD" epd type')
            
        
        try:
            myepd = AutoEPDDisplay(vcom=self.vcom)
        except ValueError as e:
            raise ScreenError(f'invalid vcom value: {e}')
        resolution = list(myepd.display_dims)
        clear_args = {}
        one_bit_display = False
        
        return {'epd': myepd, 
                'resolution': resolution, 
                'clear_args': clear_args, 
                'one_bit_display': one_bit_display,
                'constants': constants_HD,
                'mode': 'L'}    
        

    def _load_non_hd(self, epd):
        '''configure non IT8951 SPI epd
        
        For a complete list see the list_compatible_modules() functon
        
        Args:
            epd(str): name of EPD module to load
            
        Returns:
            dict:
                epd: epd object, 
                resolution: [int, int],
                clear_args: [arg1: val, arg2: val],
                constants: None
                '''
        
        import waveshare_epd
        import pkgutil
        import inspect
        from importlib import import_module
        
        logging.debug(f'configuring waveshare_epd.{epd}')
        
        non_hd = []
        for i in pkgutil.iter_modules(waveshare_epd.__path__):
            non_hd.append(i.name)
        
        if epd in non_hd:
            try:
                myepd = import_module(f'waveshare_epd.{epd}')
            except ModuleNotFoundError as e:
                raise ScreenError(f'failed to load {epd} with error: {e}')
        else:
            raise ScreenError(f'unrecongized waveshare module: {epd}')

        # check specs
        # check for supported `Clear()` function
        try:
            clear_args_spec = inspect.getfullargspec(myepd.EPD.Clear)
        except AttributeError:
            raise ScreenError(f'"{epd}" has an unsupported `EPD.Clear()` function')
        clear_args = {}
        if 'color' in clear_args_spec:
            clear_args['color'] = 0xFF
        
        # check for "standard" `display()` function
        try:
            display_args_spec = inspect.getfullargspec(myepd.EPD.display)
        except AttributeError:
            raise ScreenError(f'"{epd}" has an unsupported `EPD.display()` function and is not usable with this module')

        logging.debug(f'args_spec: {display_args_spec.args}')
        if len(display_args_spec.args) <= 2:
            one_bit_display = True
        else:
            one_bit_display = False
            
        resolution = [myepd.EPD_HEIGHT, myepd.EPD_WIDTH]
        
        
        return {'epd': myepd.EPD(), 
                'resolution': resolution, 
                'clear_args': clear_args,
                'one_bit_display': one_bit_display,
                'constants': None,
                'mode': '1'}
    
    def initEPD(self, *args, **kwargs):
        '''**DEPRICATED** init EPD for wirting
        
        For non IT8951 boards use `epd.init()` at your own risk -- SPI file handles are NOT automatically closed
        '''
        logging.warning('this method is depricated and does nothing. If you really know what you are doing, use `epd.init()` at your own risk')
    
    def blank_image(self):
        '''retrun a PIL image that is entirely blank that matches the resolution of the screen'''
        return Image.new(self.mode, self.resolution, 255)     
    
    @_spi_handler
    def clearEPD(self):
        '''wipe epd screen entirely'''
        logging.debug('clearing screen')
        if self.HD:
            clear_function = self._clearEPD_hd
        else:
            clear_function = self._clearEPD_non_hd
        
        return clear_function()
        
    
    def _clearEPD_hd(self):
        '''clear IT8951 screens entirely'''
        status = False
        try:
            self.epd.clear()
        except Exception as e:
            raise ScreenError(f'failed to clear screen: {e}')
        return status
    
    def _clearEPD_non_hd(self):
        '''clear non IT8951 screens'''
        status = False
        try:
            self.epd.Clear(**self.clear_args)
            status = True
        except Exception as e:
            raise ScreenError(f'failed to clear screen: {e}')
        return status
        
        
    
    @_spi_handler
    def writeEPD(self, image, sleep=True, partial=False):
        '''write an image to the screen 
        
        Args:
            image(PIL image): image to display
            sleep(bool): put the display to sleep after writing () (Depricated kwarg)
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
                write_function = self._full_writeEPD_non_hd

        else:
            if self.HD:
                write_function = self._full_writeEPD_hd
            else:
                write_function = self._full_writeEPD_non_hd

        write_function(image)
        if sleep==False:
            logging.warning('`sleep` kwarg is depricated and no longer used; display will be put to sleep after write')
        
        return True
    
    def _full_writeEPD_hd(self, image):
        '''redraw entire screen, no partial update with waveform GC16
        
            see: https://www.waveshare.net/w/upload/c/c4/E-paper-mode-declaration.pdf for display modes'''
        # create a blank buffer image to write into
        try:
            self.epd.frame_buf.paste(0xFF, box=(0, 0, self.resolution[0], self.resolution[1]))

            self.epd.frame_buf.paste(image, [0,0])


            self.epd.frame_buf.paste(image, [0, 0])
            logging.debug('writing to display using GC16 (full display update)')
            self.epd.draw_full(self.constants.DisplayModes.GC16)
        except Exception as e:
            raise ScreenError(f'failed to write image to display: {e}')
            
    
    def _full_writeEPD_non_hd(self, image):
        '''wipe screen and write an image'''
        image_buffer = self.epd.getbuffer(image)
        
        try:
            if self.one_bit_display:
                self.epd.display(image_buffer)
            else:
                self.epd.display(image_buffer, self.buffer_no_image)
        except Exception as e:
            raise ScreenError(f'failed to write image to display: {e}')

    def _partial_writeEPD_hd(self, image):
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







# !lsof |grep spidev0 |wc -l






def list_compatible_modules(print_modules=True):
    '''list compatible waveshare EPD modules
    
        This list includes only modules provided by the waveshare-epd git repo
        and does **NOT** include HD IT8951 based panels'''
    import pkgutil
    import waveshare_epd
    import inspect
    from importlib import import_module
    

    panels = []
    for i in pkgutil.iter_modules(waveshare_epd.__path__):
        supported = True
        display_args = []
        clear_args = []
        reason = []
        if not 'epd' in i.name:
            continue

        try:
            myepd = import_module(f'waveshare_epd.{i.name}')                
        except ModuleNotFoundError:
            reason.append(f'ModuleNotFound: {i.name}')
        
        try:
            clear_args_spec = inspect.getfullargspec(myepd.EPD.Clear)
            clear_args = clear_args_spec.args
            if len(clear_args) > 2:
                supported = False
                reason.append('Non-standard, unsupported `EPD.Clear()` function')
        except AttributeError:
            supported = False
            reason.append('AttributeError: module does not support `EPD.Clear()`')
            
        try:
            display_args_spec = inspect.getfullargspec(myepd.EPD.display)
            display_args = display_args_spec.args
        except AttributeError:
            supported = False
            reason.append('AttributeError: module does not support `EPD.display()`')
            
        


        panels.append({'name': i.name, 
                       'clear_args': clear_args, 
                       'display_args': display_args,
                       'supported': supported,
                       'reason': reason})
        
    panels.append({'name': 'HD IT8951 Based Screens',
                   'display_args': {},
                   'supported': True,
                   'reason': []})
    
    if print_modules:
        print(f'NN. Board        Supported:')
        print( '---------------------------')
        for idx, i in enumerate(panels):
            print(f"{idx:02d}. {i['name']:<12s} {i['supported']}")
            if not i['supported']:
                print(f'    Issues:')
                for j in i['reason']:
                    print(f"     * {j}")
                
    return panels






def main():
    '''run a demo/test of attached EPD screen showing rotations and basic writing'''
    import pkgutil
    import sys

    import waveshare_epd
    
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

#     print(f"{len(panels)-1}. {panels[-1]['name']}")
        
    choice = input('Enter the number of your choice: ')
    
    try:
        choice = int(choice)
    except ValueError as e:
        print(f'"{choice}" does not appear to be an valid choice. Exiting.')
        return
    myepd = panels[choice]['name']
    
    if choice > len(panels)+1:
        print(f'"{choice}" is not a valid panel option. Exiting.')
        return
    
    if 'IT8951' in myepd:
        myepd = 'HD'
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
    

        
    
#     sys.path.append('../')
    
    myLayout = {
            'title': {                       # text only block
                'image': None,               # do not expect an image
                'max_lines': 3,              # number of lines of text
                'width': 1,                  # 1/1 of the width - this stretches the entire width of the display
                'height': .6,               # 1/3 of the entire height
                'abs_coordinates': (0, 0),   # this block is the key block that all other blocks will be defined in terms of
                'hcenter': True,             # horizontally center text
                'vcenter': True,             # vertically center text 
                'relative': False,           # this block is not relative to any other. It has an ABSOLUTE position (0, 0)
                'font': str(constants.absolute_path/'../fonts/Font.ttc'), # path to font file
                'font_size': None            # Calculate the font size because none was provided
            },

            'artist': {
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






# import Layout
# l = {
#     'text_a': {
#         'image': None,
#         'padding': 10, 
#         'width': 1,
#         'height': .25,
#         'abs_coordinates': (0, 0),
#         'mode': '1',
#         'font': './fonts/Open_Sans/OpenSans-ExtraBold.ttf',
#         'max_lines': 3,
#         'fill': 0,
#         'font_size': None},
    
#     'text_b': {
#         'image': None,
#         'padding': 10,
#         'inverse': True,
#         'width': 1,
#         'height': .25,
#         'abs_coordinates': (0, None),
#         'relative': ['text_b', 'text_a'],
#         'mode': '1',
#         'font': './fonts/Open_Sans/OpenSans-ExtraBold.ttf',
#         'max_lines': 3,
#         'font_size': None},
    
#     'image_a': {
#         'image': True,
#         'width': 1/2,
#         'height': 1/2,
#         'mode': 'L',
#         'abs_coordinates': (0, None),
#         'relative': ['image_a', 'text_b'],
#         'scale_x': 1,
#         'hcenter': True,
#         'vcenter': True,
#         'inverse': True},
    
#     'image_b': {
#         'image': True,
#         'width': 1/2,
#         'height': 1/2,
#         'mode': 'L',
#         'abs_coordinates': (None, None),
#         'relative': ['image_a', 'text_b'],
#         'bkground': 255,
#         'vcenter': True,
#         'hcenter': True},
        
# }

# # full layout update
# u1 = {'text_a': 'The quick brown fox jumps over the lazy dog.',
#      'text_b': 'Pack my box with five dozen liquor jugs. Jackdaws love my big sphinx of quartz.',
#      'image_a': '../images/PIA03519_small.jpg',
#      'image_b': '../images/portrait-pilot_SW0YN0Z5T0.jpg'}

# # partial layout update (only black/white portions)
# u2 = {'text_a': 'The five boxing wizards jump quickly. How vexingly quick daft zebras jump!',
#       'text_b': "God help the noble Claudio! If he have caught the Benedick, it will cost him a thousand pound ere a be cured."}






# s = Screen(epd='HD', vcom=-1.93, rotation=0)
# mylayout_hd = Layout.Layout(resolution=s.resolution, layout=l)

# mylayout_hd.update_contents(u1)
# s.writeEPD(mylayout_hd.concat())
# time.sleep(5)

# mylayout_hd.update_contents(u2)
# s.writeEPD(image=mylayout_hd.concat(), partial=True)
# time.sleep(5)
# mylayout_hd.update_contents(u1)
# s.writeEPD(image=mylayout_hd.concat(), partial=True)
# time.sleep(5)
# s.clearEPD()
# # clean up the open SPI handles
# s.epd.epd.spi.__del__()






# import multiprocessing
# import time
# from IT8951.display import AutoEPDDisplay


# def worker(procnum, return_dict):
#     """worker function"""
#     print(str(procnum) + " represent!")
#     return_dict[procnum] = procnum


# if __name__ == "__main__":
#     manager = multiprocessing.Manager()
#     return_dict = manager.dict()
#     jobs = []
#     for i in range(5):
#         p = multiprocessing.Process(target=worker, args=(i, return_dict))
#         jobs.append(p)
#         p.start()

#     for proc in jobs:
#         proc.join()
#     print(return_dict.values())






# epd2in7 = Screen(epd='epd2in7', rotation=0)
# mylayout_non = Layout.Layout(resolution=epd2in7.resolution, layout=l)

# mylayout_non.update_contents(u1)
# epd2in7.writeEPD(mylayout_non.concat())
# time.sleep(5)
# mylayout_non.update_contents(u2)
# epd2in7.writeEPD(image=mylayout_non.concat(), partial=True)
# mylayout_non.update_contents(u1)
# time.sleep(5)
# epd2in7.writeEPD(image=mylayout_non.concat(), partial=True)
# time.sleep(5)
# epd2in7.clearEPD()






# logger = logging.getLogger(__name__)
# logger.root.setLevel('DEBUG')






if __name__ == '__main__':
    e= main()


