#!/usr/bin/env python3
# coding: utf-8








import logging
from pathlib import Path
import copy
from PIL import Image, ImageDraw, ImageFont






try:
    from . import constants
    from . import version
except ImportError as e:
    import constants
    import version
    
    
try: 
    from . import Block as Block
except ImportError as e:
    import Block as Block






logger = logging.getLogger(__name__)






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
    def __init__(self, resolution, layout=None, force_onebit=False, mode=None):
        
        if mode is None:
            mode = '1'
        
        self.resolution = resolution
        self.force_onebit = force_onebit
        self.mode = mode
        self.layout = layout
        
    @property
    def resolution(self):
        return self._resolution
    
    @resolution.setter
    @strict_enforce((list, tuple))
    def resolution(self, resolution):
        for i in resolution:
            if i < 0 or not isinstance(i, int):
                raise ValueError(f'resolution values must be positive integers: {resolution}')
        
        self._resolution = resolution
        
        # force an update to the layout when the resolution is reset
        try:
            # deepcopy the master_layout into the layout property and preserve the layout
            self.layout = copy.deepcopy(self._master_layout)
        except AttributeError:
            pass
        
    @property
    def layout(self):
        return self._layout

    @layout.setter
    @strict_enforce((dict, type(None)))
    def layout(self, layout):
        '''set the layout property, calculates positions and creates the blocks 
        
        Sets:
            self.layout
            self.blocks
            '''
        # deep copy the provided layout into the 
        self._master_layout = copy.deepcopy(layout)
        self.blocks = {}

        
        if self._master_layout:
            self._calculate_layout()
            
            blocks = {}
            logging.debug(f'layout config: resolution, {self.resolution}, force_onebit: {self.force_onebit}, mode: {self.mode}')
            logging.info(f'[[{"SETTING SECTION BLOCKS":_^30}]]')
            for name, values in self.layout.items():
                blocks[name] = self.set_block(name, values)
            self.blocks = blocks
        else:
            logging.debug('NO MASTER LAYOUT YET')


    def set_block(self, name, values, force_recalc=False):
        '''create a block object using values
        
        Allows recalculating all blocks; this is useful if the area, resolution,
        or coordinates are changed.
        
        Args:
            name(str): reference name for block
            values(dict): settings for block
            force_recalc(bool): force recalculation of all the blocks'''
        logging.info(f'setting section: [{name:_^30}]')
        
        
        if force_recalc:
            self._calculate_layout()
            
        # scale the selected font face size into the available area/lines
        if values['type'] == 'TextBlock':
            values['font_size'] = self._scale_font(values)        
        
        values['mode'] = values.get('mode', self.mode)
        
        if values.get('rgb_support', False) and self.mode == 'RGB':
            values['mode'] = 'RGB'
        
        if self.force_onebit:
            values['mode'] = '1'
            logging.debug('forcing block to 1 bit mode')
            

        logging.debug(f'setting block type: {values["type"]}')
        try:
            block = getattr(Block, values['type'])(**values)

        except AttributeError:
            raise AttributeError(f'module "Block" has no attribute {values["type"]}. error in section: {section}')
        
        if block.border_config.get('sides', False):
            block.border_config['fill'] = block.fill
        
        return block

    def _add_defaults(self):
        '''check that layout contains the minimum default values '''
        try:
            if not self._layout:
                return
        except AttributeError:
            return

        logging.debug('[[----checking default values for layout----]')
        for section, values in self.layout.items():
            logging.debug(f'section: [{section:-^30}]')
            
            
            if not 'type' in values:
                logging.critical(f'epdlib v{version.__version__}: section "{section}" is missing key "type". As of v0.6 all layout sections must include the key "type". Please see v0.5 changelog')
                raise KeyError(f'section "{section}" is missing key "type"! Each section in the layout must have an explicit block type')
                
            else:
                my_type = values['type']
                
            try:
                my_defaults = getattr(constants, f'LAYOUT_{my_type.upper()}_DEFAULTS')
            except AttributeError:
                raise ModuleNotFoundError(f'"Block" objects do not have a block type "{my_type}"')
            
            ### add kludge to bridge between 0.5 and 0.6 -- temporarily allow no type and guess 
            
            for key, default in my_defaults.items():
                if not key in values:
                    values[key] = default
                    logging.debug(f'adding "{key}: {default}"')
            
            for key, default in constants.LAYOUT_DEFAULTS.items():
                if not key in values:
                    values[key] = default
                    logging.debug(f'adding "{key}: {default}"')
                    
            self.layout[section] = values

            
    def _calculate_layout(self):
        '''calculate values for each block based on resolution, absolute and relative positions'''
        
        try:
            # always start with a fresh copy of the `master_layout` and recalculate everything
            self._layout = copy.deepcopy(self._master_layout)
        except AttributeError:
            return
        
        self._add_defaults()
        
        logging.debug('[[....calculating layouts....]]')
        for section, values in self.layout.items() :
            logging.info(f'section: [{section:.^30}]')
            
            # calculate absolute area and padded area of each block
            
            logging.debug(f"resolution: {self.resolution}")
            logging.debug(f"width: {values['width']}, height: {values['height']}")

            area = (round(self.resolution[0]*values['width']), 
                    round(self.resolution[1]*values['height']))
            
            padded_area = (area[0] - (2* values['padding']),
                           area[1] - (2* values['padding']))
        
            values['area'] = area
            values['padded_area'] = padded_area
            logging.debug(f'area: {area}, padded_area: {padded_area}')
        
        
            # calculate absolute position for each block using the relative positions of reference block(s)
            if values['abs_coordinates'][0] is None or values['abs_coordinates'][1] is None:
                logging.debug('calculating block position from relative positions')
                pos = [None, None]
                
                if not isinstance(values['relative'], (tuple, list)):
                    raise KeyError(f'section "{section}" has a missing or malformed "relative" key.')
                    
                
                for index, val in enumerate(values['relative']):
                    # use the absolute value provided in this section
                    if val == section:
                        pos[index] = values['abs_coordinates'][index]
                    else:
                        # calculate position relative to another block
                        try:
                            pos[index] = self.layout[val]['area'][index] + self.layout[val]['abs_coordinates'][index]
                        except KeyError:
                            raise KeyError(f'bad relative section value: could not locate relative section "{val}"  when processing section "{section}"')
                values['abs_coordinates'] = (pos[0], pos[1])
            else: 
                logging.debug('absolute coordinates provided')
            
            logging.debug(f'block coordinates: {values["abs_coordinates"]}')            
    
    @staticmethod
    def _scale_font(this_section):
        '''scale a font face into the avaialble area/max-lines settings

        Args:
            this_section(dict): layout section dictionary

        Returns
            fontsize(int): integer value for font size'''
        text = constants.LAYOUT_SCALE_FONT_TEXT
        logging.debug('scaling font size')
        x_target, y_target = this_section['padded_area']

        y_target = y_target/this_section['max_lines']
        font = this_section['font']        

        cont = True
        fontsize = 0
        # try different font sizes until an a value that fits within the y_target value is found
        while cont:
            fontsize += 1
            testfont = ImageFont.truetype(font, fontsize)

            fontdim = testfont.getbbox(text)

            if fontdim[2] > x_target:
                cont = False
                logging.debug('x target size reached')

            if fontdim[3] > y_target:
                cont = False
                logging.debug('y target size reached')

        fontsize -= 1
        logging.debug(f'calculated font size: {fontsize}')
        return fontsize
    
    def update_block_props(self, block, props={}, force_recalc=False):
        '''update the properties of a block and optionally recalculates all of the 
        block areas 
        
        block(str): name of block
        props(dict): properties to update or add
        force_recalc(bool): force recalculation of all blocks
        '''
        self.layout[block].update(props)
        self.blocks[block] = self.set_block(block, self.layout[block], force_recalc)
                
    
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
        self.image = Image.new(self.mode, self.resolution, 'white')
        if self.blocks:
            for b in self.blocks:
                self.image.paste(self.blocks[b].image, self.blocks[b].abs_coordinates)
        return self.image    
            






# from random import randint, choice
# from IPython.display import display
# from time import sleep
# bogus_layout = {
#     'l_head': {          
#         'type': 'TextBlock',
#         'image': None,
#         'max_lines': 1,
#         'width': .5,
#         'height': .1,
#         'abs_coordinates': (0, 0),
#         'rand': True,
#         'font': '../fonts/Open_Sans/OpenSans-Regular.ttf',
#         'bkground': 'BLACK',
#         'fill': 'WHITE'
#     },
#     'r_head': {          
#         'type': 'TextBlock',
#         'image': None,
#         'max_lines': 1,
#         'width': .5,
#         'height': .1,
#         'abs_coordinates': (None, 0),
#         'relative': ('l_head', 'r_head'),
#         'rand': True,
#         'font': '../fonts/Open_Sans/OpenSans-Regular.ttf',
#         'bkground': 'RED',
#         'fill': 'BLACK'
#     },

#     'number': {
#         'type': 'TextBlock',
#         'image': None,
#         'max_lines': 1,
#         'width': .6,
#         'height': .4,
#         'abs_coordinates': (0, None),
#         'relative': ('number', 'l_head'),
#         'rand': True,
#         'font': '../fonts/Open_Sans/OpenSans-Regular.ttf',
#     },
#     'small_number': {
#         'type': 'TextBlock',
#         'image': None,
#         'max_lines': 1,
#         'width': .4,
#         'height': .5,
#         'abs_coordinates': (None, None),
#         'relative': ('number', 'l_head'),
#         'rand': True,
#         'font': '../fonts/Open_Sans/OpenSans-Regular.ttf',
#         'fill': 'BLUE',
#         'bkground': 'GREEN',
#         'rgb_support': True
#     },
#     'text': {
#         'abs_coordinates': (0, None),
#         'relative': ('text', 'number'),
#         'type': 'TextBlock',
#         'image': None,
#         'max_lines': 3,
#         'height': .4,
#         'width': 1,
#         'rand': True,
#         'font': '../fonts/Open_Sans/OpenSans-Regular.ttf',
#         'fill': 'ORANGE',
#         'bkground': 'BLACK',
#         'rgb_support': True
#     }
# }


# # config = {
# #     'resolution': [300, 200],
# #     'max_priority': 1,
# #     'refresh_rate': 2,
# #     'update_function': bogus_plugin,
# #     'layout': bogus_layout,
# #     'screen_mode': 'RGB',
# #     'plugin_timeout': 5,
# #     'name': 'Bogus',
# #     'foo': 'bar',
# #     'spam': False
# # }


# #     Plugin.update_function = bogus_plugin

# logger.root.setLevel('DEBUG')

# l = Layout(resolution=(300, 200))
# l.layout = bogus_layout
# p = Layout(resolution=(800, 400))
# p.layout = bogus_layout


# # for i in range(5):
# #     .resolution = (randint(300, 800), randint(300, 600))
# #     logging.info(f'plugin resolution set to: {p.resolution}')
# #     p.layout_obj = None
# #     p.layout = bogus_layout
# #     for s in bogus_layout:
# #         colors = ['RED', 'ORANGE', 'YELLOW', 'GREEN', 'BLUE', 'BLACK', 'WHITE']
# #         fill = choice(colors)
# #         colors.remove(fill)
# #         bkground = choice(colors)
# #         p.layout_obj.update_block_props(block=s, props={'bkground': bkground, 'fill': fill}, force_recalc=True)

# #     print('trying to update plugin')
# #     p.force_update()
# #     print('displaying image')
# #     display(p.image)
# # #         print('sleep for 1 second')
# #     sleep(1)


# print(f'l.layout: {l.resolution}')
# for k, v in l.blocks.items():
#     print(f'{k}\n   a: {v.area}\n   c: {v.abs_coordinates}')
    
# print(f'\n\np.layout: {p.resolution}')
# for k, v in p.blocks.items():
#     print(f'{k}\n   a: {v.area}\n   c: {v.abs_coordinates}')

# p.resolution = (100, 40)

# p._master_layout

# print(f'l.layout: {l.resolution}')
# for k, v in l.blocks.items():
#     print(f'{k}\n   a: {v.area}\n   c: {v.abs_coordinates}')
    
# print(f'\n\np.layout: {p.resolution}')
# for k, v in p.blocks.items():
#     print(f'{k}\n   a: {v.area}\n   c: {v.abs_coordinates}')


