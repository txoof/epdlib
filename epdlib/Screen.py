#!/usr/bin/env python3
# coding: utf-8








import logging
from PIL import Image, ImageDraw
from datetime import datetime
from pathlib import Path
import time






def strict_enforce(*types):
    """strictly enforce type compliance within classes
    
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
    






class Screen():
    def __init__(self, epd=None, rotation=0, mode='1', vcom=0.0):
        self.vcom = vcom
        self.one_bit_display = True
        self.constants = None
        self.mode = mode
        self.image = None
        self.hd = False
        self.resolution = [1, 1]
        self.HD = False
        self.epd = epd
        self.rotation = rotation
        
        
    @property
    def vcom(self):
        return self._vcom

    @vcom.setter
    @strict_enforce(float)
    def vcom(self, vcom):
        if vcom==0:
            self._vcom = None
        elif vcom > 0:
            raise ValueError(f'vcom must be a negative float value: {vcom}')
        else:
            self._vcom = vcom

    @property
    def rotation(self):
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
            
        self.image = Image.new('L', self.resolution, 255)
        if not self.HD:
            self.buffer_no_image = self.epd.getbuffer(self.blank_image())

        self._rotation = rotation
        logging.debug(f'rotation={rotation}, resolution={self.resolution}')
            
    @property
    def epd(self):
        return self._epd

    @epd.setter
    @strict_enforce((type(None), str))
    def epd(self, epd):
        if not epd:
            self._epd = None
            return
        
        myepd = None
        if epd=='HD':
            if not self.vcom:
                raise ScreenError('no vcom value is set (see the cable on your display for a vcom value)')
            self.HD = True
            myepd = self._epd_hd(epd)
            
        elif epd == 'None':
            myepd = None
        else:
            myepd = self._epd_non_hd(epd)

        if myepd:
            # set the resolution 
            self._epd = myepd['epd']
            resolution = myepd['resolution']
            resolution.sort(reverse=True)
            self.resolution = resolution
            self.clear_args = myepd['clear_args']
            self.constants = myepd['constants']
            self.one_bit_display = myepd['one_bit_display']
            
            logging.debug(f'epd configuration: {myepd}')
            
            # set a blank image as default
            self.image = Image.new('L', self.resolution, 255)
            if self.HD:
                self.buffer_no_image = []
            else:
                self.buffer_no_image = self.epd.getbuffer(self.blank_image())
        else:
            logging.warning('no valid epd is currently configured')
            
    def initEPD(self):
        '''init the EPD for writing'''
        if not self.epd:
            raise UnboundLocalError('no epd object has been assigned')
            
        if self.HD:
            self._epd.epd.run()
        else:
            try:
                self.epd.init()
            except FileNotFoundError as e:
                raise ScreenError('failed to open SPI bus - is spi enabled in raspi-config?')
#                 logging.error(f'failed to init epd: {e}: error: {type(e)}')

        logging.info(f'epd initialized')
            
        return True            

    def clearEPD(self):
        if self.HD:
            self._epd.epd.run()
            self._epd.clear()
        else:
            try:
                self.initEPD()
                self.epd.Clear(**self.clear_args)
            # FIXME -- more explicit output here on failure
            except Exception as e:
                logging.error(f'failed to clear epd: {e}')
                return False
        return True
        
    
    def blank_image(self):
        '''generate PIL image that is entirely blank'''
        return Image.new(self.mode, self.resolution, 255)
            
            

    def writeEPD(self, image=None, sleep=True, partial=False):
        '''write an image to the screen after clearing previous
        
            Non-hd screens should be put to sleep after writing to prevent
            damage to the panel.
        
        Args:
            image(PIL image): image to display
            sleep(bool) Put display to sleep after updating
            
            '''
        if not image:
            raise ScreenError('No image provided')
            
        if not self.epd:
            raise UnboundLocalError('no epd has been assigned')
        
        image = image.rotate(self.rotation, expand=True)
#         if self.rotation in [180, -90]:
#             image = image.rotate(180)
        
        # init epd
        self.initEPD()
    
        if partial:
            if self.HD:
                self._partial_writeEPD_hd(image)
            else:
                logging.warning('partial update not available on non-hd displays')
                self._full_writeEPD_non_hd(image)
                    
        else:
            if self.HD:
                self._full_writeEPD_hd(image)
            else:
                self._full_writeEPD_non_hd(image)
                
        if sleep:
            logging.debug('putting display to sleep')
            if self.HD:
                self.epd.epd.sleep()
            else:
                self.epd.sleep()
        return True
                
    def _partial_writeEPD_hd(self, image):
        '''partial update, affects only changed black and white pixels with no flash
        
            uses waveform DU see: see: https://www.waveshare.net/w/upload/c/c4/E-paper-mode-declaration.pdf for display modes
     '''
        
        self.epd.frame_buf = mylayout_hd.image
        self.epd.draw_partial(self.constants.DisplayModes.DU)
    
    def _full_writeEPD_hd(self, image):
        '''redraw entire screen, no partial update with waveform GC16
        
            see: https://www.waveshare.net/w/upload/c/c4/E-paper-mode-declaration.pdf for display modes'''
        # create a blank buffer image to write into
        self.epd.frame_buf.paste(0xFF, box=(0, 0, self.resolution[0], self.resolution[1]))
        
        self.epd.frame_buf.paste(image, [0,0])


        self.epd.frame_buf.paste(image, [0, 0])

        self.initEPD()
        logging.debug('writing to display using GC16 (full display update)')
        self.epd.draw_full(self.constants.DisplayModes.GC16)
            
        return True
        
    def _full_writeEPD_non_hd(self, image):
        '''redraw entire screen'''
        image_buffer = self.epd.getbuffer(image)
        self.initEPD()
        if self.one_bit_display:
            self.epd.display(image_buffer)
        else:
            # send a blank image to colored layer
            self.epd.display(image_buffer, self.buffer_no_image)
        
        return True
    
    def _epd_hd(self, epd):
        '''configure & init IT8951 Screens
        
        Args:
            epd(str): ignored; used for consistency for non-HD init'''
        from IT8951.display import AutoEPDDisplay
        from IT8951 import constants as constants_HD
        myepd = AutoEPDDisplay(vcom=self.vcom)
        resolution = list(myepd.display_dims)
        clear_args = {}
        one_bit_display = False
        
        return {'epd': myepd, 
                'resolution': resolution, 
                'clear_args': clear_args, 
                'one_bit_display': one_bit_display,
                'constants': constants_HD}    
                    
    def _epd_non_hd(self, epd):
        '''configure and init non IT8951 Screens
        
        Args:
            epd(str): name of waveshare EPD module
                see '''
        import waveshare_epd
        import pkgutil
        import inspect
        from importlib import import_module
        non_hd = []
        for i in pkgutil.iter_modules(waveshare_epd.__path__):
            non_hd.append(i.name)

        if epd in non_hd:
            myepd = import_module(f'waveshare_epd.{epd}')
            resolution = [myepd.EPD_HEIGHT,myepd.EPD_WIDTH]
            
            # set kwargs for screens that expect color or mode arguments to the clear function
            try:
                clear_args_spec = inspect.getfullargspec(myepd.EPD.Clear)
            except AttributeError:
                raise ScreenError(f'"{epd}" has an unsupported `EPD.Clear()` function')
            clear_args = {}
            if 'color' in clear_args_spec:
                clear_args['color'] = 0xFF
                
            try:
                display_args_spec = inspect.getfullargspec(myepd.EPD.display)
            except AttributeError:
                raise ScreenError(f'"{epd}" has an unsupported `EPD.display()` function and is not usable with this module')
            
            logging.debug(f'args_spec: {display_args_spec.args}')
            if len(display_args_spec.args) <= 2:
                one_bit_display = True
            else:
                one_bit_display = False
            
        else:
            raise ScreenError(f'invalid waveshare module: {epd}')
            
        return {'epd': myepd.EPD(), 
                'resolution': resolution, 
                'clear_args': clear_args,
                'one_bit_display': one_bit_display,
                'constants': None}






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
    
#     return panels
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
    # import importlib
    # import inspect

    import waveshare_epd
    # from importlib import import_module
    # get a list of waveshare non-hd models
    panels = []
#     for i in pkgutil.iter_modules(waveshare_epd.__path__):
#         panels.append(i.name)
#     panels.append('All IT8951 Based Panels')
    
#     print('Choose a pannel to test:')
#     for idx, i in enumerate(panels):
#         print(f'  {idx}. {i}')
    panels = list_compatible_modules()
    panels.append({'name': 'All IT8951 Based Panels'})
    print(f"{len(panels)-1}. {panels[-1]['name']}")
        
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
    
    import Layout
    
    sys.path.append('../')
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

    for r in [0, 90, -90, 180]:
        print(f'setup for rotation: {r}')

        s = Screen(epd=myepd, rotation=r, vcom=voltage)
        s.initEPD()

        l = Layout.Layout(resolution=s.resolution)
        l.layout = myLayout
        l.update_contents({'title': 'item: spam, spam, spam, spam & ham', 'artist': 'artist: monty python'})
        print('print some text on the display')
    #         s.initEPD()
        s.writeEPD(l.concat(), sleep=False)
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
#         'height': 1/4,
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
#         'height': 1/4,
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






# s = Screen(epd='HD', vcom=-1.93, mode='L', rotation=0)
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






# logger = logging.getLogger(__name__)
# logger.root.setLevel('DEBUG')






if __name__ == '__main__':
    e= main()


