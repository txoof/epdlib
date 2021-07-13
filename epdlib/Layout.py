#!/usr/bin/env python3
# coding: utf-8








import logging
from pathlib import Path
import copy
from PIL import Image, ImageDraw, ImageFont






try:
    from . import constants
except ImportError as e:
    import constants
    
try: 
    from . import Block as Block
except ImportError as e:
    import Block as Block






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






class Layout:
    def __init__(self, resolution, layout=None):
        '''init layout object
        
        Args:
            resolution(tuple of int): X, Y screen resolution
            layout(dict): layout rules
            
        Attributes:
            blocks(dict of Block obj): dictionary of ImageBlock and TextBlock objects
            screen(PIL.Image): single image composed of all blocks defined in the layout
            mode(str): "L" (8bit) or "1" (1bit) if any blocks are 8bit, this will be set to "L" '''
        
        self.resolution = resolution
        self.screen = None
        self.mode = "1"
        self.layout = layout
        self._calculate_layout()
        self._set_blocks()

    @property
    def resolution(self):
        '''tuple of int: absolute resolution of screen'''
        return self._resolution

    @resolution.setter
    @strict_enforce((list, tuple))
    def resolution(self, resolution):
        for i in resolution:
            if i < 0:
                raise ValueError('resolution values must be positive integers')

            if not isinstance(i, int):
                raise ValueError('resolution values must be positive integers')

        self._resolution = resolution

    @property
    def layout(self):
        return self._layout
    
    @layout.setter
    @strict_enforce((dict, type(None)))
    def layout(self, layout):
        self._layout = layout
        
        if layout:
            self._calculate_layout()
            self._set_blocks()
            
    def _set_blocks(self):
        '''create dictionary of all image blocks using the specified layout'''
        if not self.layout:
            return        
        
        blocks = {}
        logging.info('setting blocks')
        
        mode_count = 0
        
        for section in self.layout:
            logging.info(f'section: [{section:.^30}]')            
            vals = self.layout[section]
            if vals['mode'] == "L":
                mode_count += 1
                
            if not vals['image']:
                logging.info(f'set text block: {section}')
                blocks[section] = Block.TextBlock(**vals)
            
            if vals['image']:
                logging.info(f'set image block: {section}')
                blocks[section] = Block.ImageBlock(**vals)
                
        self.blocks = blocks
        if mode_count > 0:
            self.mode = 'L'
        else:
            self.mode = '1'
    
    
    def _calculate_layout(self):
        if not self.layout:
            return
        logging.debug('calculating layouts for sections')
        for section in self.layout:
            logging.info(f'section: [{section:.^30}]')
            this_section = self.layout[section]
            # add default values if they are missing
            for key, value in constants.layout_defaults.items():
                if not key in this_section:
                    logging.debug(f'setting missing value to default: {key}: {value}')
                    this_section[key] = value
            
            # absolute area in pixles
            area = (round(self.resolution[0]*this_section['width']),
                          round(self.resolution[1]*this_section['height']))
            this_section['area'] = area
            # usable area (absolute-x, y padding)
            padded_area = (area[0] - this_section['padding']*2, 
                                 area[1] - this_section['padding']*2)
            this_section['padded_area'] = padded_area
            
            # set the thumbnail 
            if this_section['image']:
                maxsize = min(area)
                this_section['thumbnail_size'] = (maxsize, maxsize)
            
            if this_section['abs_coordinates'][0] is None or this_section['abs_coordinates'][1] is None:
                logging.debug(f'calculating absolute position')
                pos = [None, None]
                for idx, r in enumerate(this_section['relative']):
                    if r == section:
                        # use the coordinates from this section
                        pos[idx] = this_section['abs_coordinates'][idx]
                    else:
                        # use the coordinates from another section
                        try:
                            pos[idx] = self.layout[r]['area'][idx] + self.layout[r]['abs_coordinates'][idx]
                        except KeyError as e:
                            raise KeyError(f'bad relative section value: "{r}" in section "{section}"')
                this_section['abs_coordinates'] = (pos[0], pos[1])
            else:
                logging.debug('absolute coordinates provided')
                
            logging.debug(f'coordinates for this block: {this_section["abs_coordinates"]}')
            
            if not this_section['image']:
                this_section['font_size'] = self._scalefont(this_section)
            
    def _scalefont(self, this_section):
        text = 'WwQq'
        logging.debug('scaling font size')
        x_target, y_target = this_section['padded_area']
        
        y_target = y_target/this_section['max_lines']
        font = this_section['font']
        
        
        cont = True
        fontsize = 0
        while cont:
            fontsize += 1
            testfont = ImageFont.truetype(font, fontsize)
            
            fontdim = testfont.getsize(text)
            
            if fontdim[0] > x_target:
                cont = False
                logging.debug('x target size reached')
            
            if fontdim[1] > y_target:
                cont = False
                logging.debug('y target size reached')
            
        fontsize -= 1
        logging.debug(f'calculated font size: {fontsize}')
        return fontsize
    

    def update_contents(self, update=None):
        if not update:
            return
        
        if not isinstance(update, dict):
            raise TypeError('update must be of type `dict`')
        
        for key, val in update.items():
            if key in self.blocks:
                self.blocks[key].update(val)
            else:
                logging.debug(f'"{key}" is not a recognized block, skipping')
                
    def concat(self):
        self.image = Image.new('L', self.resolution, 255)
        if self.blocks:
            for b in self.blocks:
                self.image.paste(self.blocks[b].image, self.blocks[b].abs_coordinates)
        return self.image






# ml = Layout(resolution=(800, 600))
# ml.layout = l
# ml.update_contents(update)

# ml.concat()






# # create the layout object
# # myLayout = Layout(resolution=(1200, 825))

# l = { # basic two row layout
#     'weather_img': {                
#             'image': True,               # image block
# #             'padding': 2,               # pixels to padd around edge
#             'width': 1/4,                # 1/4 of the entire width
#             'height': 1/4,               # 1/4 of the entire height
#             'abs_coordinates': (0, 0),   # this block is the key block that all other blocks will be defined in terms of
#             'hcenter': True,             # horizontally center image
#             'vcenter': True,             # vertically center image
#             'relative': False,           # this block is not relative to any other. It has an ABSOLUTE position (0, 0)
#             'mode': 'L',
#             'bkground': 128
#         },
#     'temperature': { 
#                 'image': None,           # set to None if this is a text block
#                 'max_lines': 1,          # maximum lines of text to use when wrapping text
#                 'padding': 10,           # padding around all edges (in pixles)
#                 'width': 1/4,            # proportion of the entire width
#                 'height': 1/4,           # proprtion of the entire height
#                 'abs_coordinates': (None, 0), # absolute coordinates within the final image (use None for those
#                                               # coordinates that are relative to other blocks and will be calculated
#                 'hcenter': True,         # horizontal-center the text and the resulting image
#                 'vcenter': True,         # vertically-center the text within the block
#                 'relative': ['weather_img', 'temperature'], # blocks to which THIS block's coordinates are relative to
#                                                             # -- in this case X: `weather_img` and Y: `temperature`
#                                                             # the width of the block `weather` will be used to
#                                                             # to calculate the X value of this block and the Y value
#                                                             # specified within the `temperature` block will be used 
#                 'font': './fonts/Open_Sans/OpenSans-ExtraBold.ttf', # TTF Font face to use; relative paths are OK
#                 'font_size': None,         # set this to None to automatically scale the font to the size of the block
#                 'bkground': 255,
#                 'align': 'center',
#                 'mode': 'L'
#     },
#     'wind': { 
#                 'image': None,
#                 'max_lines': 3,
#                 'padding': 0,
#                 'width': 1/4,
#                 'height': 1/4,
#                 'abs_coordinates': (None, 0),
#                 'hcenter': True,
#                 'vcenter': True,
#                 'relative': ['temperature', 'wind'],
#                 'font': './fonts/Open_Sans/OpenSans-ExtraBold.ttf',
#                 'font_size': None
#     },
#     'rain': { 
#                 'image': None,
#                 'max_lines': 3,
#                 'padding': 0,
#                 'width': 1/4,
#                 'height': 1/4,
#                 'abs_coordinates': (None, 0),
#                 'hcenter': True,
#                 'vcenter': True,
#                 'relative': ['wind', 'rain'],
#                 'font': './fonts/Open_Sans/OpenSans-ExtraBold.ttf',
#                 'font_size': None
#     },    
#     'forecast': {
#                 'image': None,
#                 'max_lines': 7,
#                 'padding': 10,
#                 'width': 1,
#                 'height': 3/4,
#                 'abs_coordinates': (0, None),
#                 'hcenter': False,
#                 'vcenter': True,
#                 'relative': ['forecast', 'temperature'],
#                 'font': './fonts/Open_Sans/OpenSans-Regular.ttf',
#                 'font_size': None,
#                 'padding': 10,
#                 'align': 'left',
#                 'mode': 'L'
# #                 'scale_y': .85
#     }

# }

# # # apply the layout instructions to the layout object
# # myLayout.layout = l


# update = {
#     'weather_img': '../images//portrait-pilot_SW0YN0Z5T0.jpg',      # weather_img block will recieve a .png
#     'temperature': '15C',                     # temperature block will receive `15C`
#     'wind': 'Wind: East 3m/s',                 # wind block will recieve this text
#     'rain': 'Rain: 0%',                       # rain block
# #     'forecast': 'Partly cloudy throughout the day with an east wind at 3m/s. High of 20, low of 12 overnight. Tomorrow: temperatures falling to 15 with an increased chance of rain'
#     'forecast': "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam sed nunc et neque lobortis condimentum. Mauris tortor mi, dictum aliquet sapien auctor, facilisis aliquam metus. Mauris lacinia turpis sit amet ex fringilla aliquet."
# }
# # myLayout.update_contents(update)

# # # join all the sub images into one complete image
# # myImg = myLayout.concat()

# # # write the image out to a file
# # # myImg.save('./my_forecast.png')

# # myImg






# logger = logging.getLogger(__name__)
# logger.root.setLevel('DEBUG')
# logging.root.setLevel('DEBUG')









