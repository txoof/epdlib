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
    def __init__(self, resolution, layout=None, force_onebit=False, mode='1'):
        self.resolution = resolution
        self.force_onebit = force_onebit
        self.mode = mode
        self.blocks = {}
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
        
    @property
    def layout(self):
        return self._layout

    @layout.setter
    @strict_enforce((dict, type(None)))
    def layout(self, layout):
        '''set the layout property and creates the blocks if layout is provided
        
        Sets:
            self.blocks'''
        self._layout = layout
        
        if self._layout:
            self._add_defaults()
            self._calculate_layout()
            
            blocks = {}
            logging.debug(f'layout config: resolution, {self.resolution}, force_onebit: {self.force_onebit}, mode: {self.mode}')
            logging.info(f'[[{"SETTING SECTION BLOCKS":_^30}]]')
            for name, values in self.layout.items():
                blocks[name] = self.set_block(name, values)
            self.blocks = blocks


    def set_block(self, name, values, force_recalc=False):
        '''create a block object using values
        
        Allows recalculating all blocks; this is useful if the area, resolution,
        or coordinates are changed.
        
        Args:
            name(str): reference name for block
            values(dict): settings for block
            force_recalc(bool): force recalculation of all the blocks'''
#         if not self.layout:
#             return
        
        

        
#         for section, vals in self.layout.items():
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
        logging.debug('[[----checking default values for layout----]')
        for section, values in self.layout.items():
            logging.debug(f'section: [{section:-^30}]')
            
            
            if not 'type' in values:
                logging.critical(f'epdlib v{version.__version__}: section "{section}" is missing key "type". As of v0.6 all layout sections must include the key "type". Please see v0.5 changelog')
                raise KeyError(f'section "{section}" is missing key "type"! Each section in the layout must have the correct block type')
                
#                 ## backwards compatibility for pre v0.5 layouts -- remove this in v0.6
#                 logging.warning(f'guessing block type for section "{section}"')
#                 if values['image']:
#                     my_type = 'ImageBlock'
#                 else: 
#                     my_type = 'TextBlock'              
#                 logging.warning(f'guessed: {my_type} -- if this is incorrect add the key "type" with the appropriate Block type in this section of the layout.')
#                 values['type'] = my_type
                ## end backwards compatibility
                
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
        if not self._layout:
            return
        
        
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
            
#             # scale the selected font face size into the available area/lines
#             if values['type'] == 'TextBlock':
#                 values['font_size'] = self._scale_font(values)
            
            
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
            


