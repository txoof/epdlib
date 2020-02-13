#!/usr/bin/env python
#!/usr/bin/env python
# coding: utf-8


# In[3]:


#get_ipython().run_line_magic('alias', 'nbconvert nbconvert Layout.ipynb')




# In[4]:


#get_ipython().run_line_magic('nbconvert', '')




# In[1]:


#get_ipython().run_line_magic('load_ext', 'autoreload')
#get_ipython().run_line_magic('autoreload', '2')

#get_ipython().run_line_magic('reload_ext', 'autoreload')




# In[2]:


import logging
from pathlib import Path
import copy
from PIL import Image, ImageDraw, ImageFont




# In[3]:


try:
    from . import constants
except ImportError as e:
    import constants

try:
    from . import Block as Block
except ImportError as e:
    import Block




# In[4]:


class Layout:
    """Class for defining layout of epd screen
    
    This class allows screen layouts to be declared in terms of image blocks within an area. 
    Block placement is defined in terms of absolute or relative positions. Only one block 
    with absolute coordinates is needed. Block size is calculated based on screen size making
    it possible to define one layout that will work on screens of different dimensions.
    
    layouts are specified using the following key/value pairs. Those marked with a * are required
    for all blocks
    *'image': (None/True)          # None/False indicates this will NOT be an image block
    'max_lines': (int)             # maximum number of lines of text this block can accomodate
    'padding': (int)               # number of pixles to add around an image
    *'widht': (int/real)           # fractional portion of screen width this block occupies e.g. 
                                   # 1/2, 1, .25
    *'height': (int/real)          # fractional portion of the screen height this block occupies
    *'abs_coordinates': (tuple)    # tuple of X, Y coordinates where this block lies within the 
                                   # larger screen area. EVERY layout must have at least one block
                                   # that is defined ABSOLUTELY - typically: (0, 0)
                                   # When a block is placed relative to another
                                   # block use `None` to indicate that this is a calculated coordiante
                                   # e.g. (0, None) - Use an absolute value of X=0 and Y=None(calculated)
    'hcenter': (bool)              # horizontally center the text and image of the text in the block
    'vcenter': (bool)              # vertically center the text within the image block
    'rand' (bool)                  # True: randomply place the image within the area (overrides v/h center)
    *'relative': (False/list)      # False for blocks with absolute position; use a list other blocks
                                   # to use for calculating the position of this block e.g.
                                   # ['coverart', title] - reference the block `coverart` for the 
                                   # X position and `title` for the Y position of this block
    'font': (str):                 # Path to font file (relative paths are acceptable)
    'font_size': (None/int)        # None - calculate the font size, int - size in points
    'inverse': (bool)              # True: use black background, white fill

    
    Layouts are defined using any name and can be updated by calling the update() method with 
    a parameter that includes a dictionary containing a key/value pair that matches the names
    see the example below.
    Sample Laout:
    myLayout = {
        'title': {                       # text only block
            'image': None,               # do not expect an image
            'max_lines': 2,              # number of lines of text
            'width': 1,                  # 1/1 of the width - this stretches the entire width of the display
            'height': 2/3,               # 1/3 of the entire height
            'abs_coordinates': (0, 0),   # this block is the key block that all other blocks will be defined in terms of
            'hcenter': True,             # horizontally center text
            'vcenter': True,             # vertically center text 
            'relative': False,           # this block is not relative to any other. It has an ABSOLUTE position (0, 0)
            'font': './fonts/Anton/Anton-Regular.ttf', # path to font file
            'font_size': None            # Calculate the font size because none was provided
        }
    
        'artist' {
            'image': None,
            'max_lines': 1,
            'width': 1,
            'height', 1/3,
            'abs_coordinates': (0, None)   # X = 0, Y will be calculated
            'hcenter': True,
            'vcenter': True,
            'relative': ['artist', title], # use the X postion from abs_coord from `artist` (this block: 0)
                                           # calculate the y position based on the size of `title` block
            
        }
    }
    
    
    Example creating and updating a layout:
    layouts.threeRow has the sections: 'title', 'album', 'artist', 'mode', 'coverart'
    # creates the object and calculates the positions based on the rules set 
    # in the layouts file and screen size
    l = Layout(resolution=(600, 448), layout=myLayout)
    # update/add content to the layout object, applying formatting from layout file
    l.update_contents({'title': 'Hannah Hunt', 'album': 'Modern Vampires of the City', 
                       'artist': 'Vampire Weekend')
                       
    Example displaying layout:
    """
       
    def __init__(self, resolution=None, layout=None, font=None):
        """  Initializes layout object
        
        Args:
            resolution (:obj:`tuple` of :obj: `int`): X, Y screen resolution in pixles
            layout: (dict): layout
            font (str): path to default font file if none is provided in layout
        Attributes:
            blocks (:obj:`dict` of :obj:`Block`): dictionary of ImageBlock and TextBlock objects"""
        logging.info('Layout created')
        self.resolution = resolution
        if font:
            logging.debug(f'default font specified: {font}')
            self.font = str(Path(font).resolve())
        else:
            logging.debug('no default font specified')
            self.font = None
        if layout:
            self.layout = layout
        self.images = None #FIXME not needed?

    def _check_keys(self, dictionary, values):
        """Check `dictionary` for missing key/value pairs specified in `values`
        
        Args:
            dictionary(dict): dictionary to check
            values(dict): dictionary of default key and value pairs
            
        Returns:
            dictionary(dict): dictionary with missing key/value pairs updated"""
            
        logging.debug('checking key/values')
        for k, v in values.items():
            try:
                dictionary[k]
            except KeyError as e:
                logging.debug(f'missing key: {k}; adding and setting to {v}')
                dictionary[k] = v
        return dictionary
    
    def _scalefont(self, font=None, lines=1, text="W ", maxchar=6, dimensions=(100, 100)):
        """Scale a font to fit the number of `lines` within `dimensions`
        
        Args:
            font(str): path to true type font
            text(str): string to use when calculating (default: 'W ')
            maxchar(int): number of characters of `text` to use when calculating 
                default is 'W W W ' -- W is a large character and spaces allow 
                textwrap to work properly
            lines(int): number of lines of text to fit within the `dimensions`
            dimensions(:obj:`tuple` of :obj:`int`): dimensions of pixles
            
        Returns:
            :obj:int: font size as integer"""
            
        if not maxchar:
            maxchar = 6
            logging.debug(f'no max char set; using: {maxchar}')
            
        if font:
            font = str(Path(font).resolve())
        else:
            font = str(Path(self.font).resolve())
        
        if len(text) < maxchar:
            multiplyer = round(maxchar/len(text))
            text = text * multiplyer
        else:
            text = text[0:maxchar] 
    
        
        
        logging.debug('calculating font size')
        logging.debug(f'using text: {text}; maxchar: {maxchar}')
        logging.debug(f'using font at path: {font}')
        
        
        # start calculating at size 1
        fontsize = 1
        x_fraction = .85        
        y_fraction = .7
        xtarget = dimensions[0]*x_fraction
        ytarget = dimensions[1]/lines*y_fraction
        try:
            testfont = ImageFont.truetype(font, fontsize)
        except (IOError, OSError) as e:
            logging.error(f'failed to load font: {font}')
            logging.error(f'{e}')
            raise(e)
        fontdim = testfont.getsize(text)
        
        logging.debug(f'target X font dimension {xtarget}')
        logging.debug(f'target Y dimension: {ytarget}')
        
        # loop control variable
        cont = True
        # work up until font covers img_fraction of the resolution return one smaller than this as the fontsize
        while cont:
            fontsize += 1
            testfont = ImageFont.truetype(font, fontsize)
            
            fontdim = testfont.getsize(text)
            if fontdim[0] > xtarget:
                cont = False
                logging.debug(f'X target exceeded')
                
            if fontdim[1] > ytarget:
                cont = False
                logging.debug('Y target exceeded')
            
        # back off one 
        fontsize -= 1
        logging.debug(f'test string: {text}; dimensions for fontsize {fontsize}: {fontdim}')
        return fontsize
    
    @property
    def layout(self):
        ''':obj:dict: dictonary of layout properties and rules for formatting text and image blocks
        
        Sets:
            blocks (dict): dict of ImageBlock or TextBlock objects 
        '''
        return self._layout
    
    @layout.setter
    def layout(self, layout):        
        if not ((isinstance(self.resolution, tuple) or isinstance(self.resolution, list))and len(self.resolution)==2):
            raise ValueError(f'resolution must be a list-like object of length 2: resolution = {self.resolution}')
        logging.debug(f'calculating values from layout for resolution {self.resolution}')
        if not layout:
            logging.info('no layout provided')
            self._layout = None
        else:
            self._layout = self._calculate_layout(layout)
            self._set_images()
    
    def _calculate_layout(self, layout):
        """Calculate the size and position of each text block based on rules in layout
        
        Args:
            layout(dict): dictionary containing the layout to be used
        
        Returns:
            layout(dict): dictionary that includes rules and values for the layout"""
        if not layout:
            return None
        l = layout
        
        resolution = self.resolution
        
        # required values that will be used in calculating the layout
        values = {'image': None, 'max_lines': 1, 'padding': 0, 'width': 1, 'height': 1, 
                  'abs_coordinates': (None, None), 'hcenter': False, 'vcenter': False, 
                  'rand': False, 'inverse': False, 'relative': False, 'font': self.font, 
                  'font_size': None, 'maxchar': None, 'dimensions': None}        
        for section in l:
            logging.debug(f'***{section}***')
            this_section = self._check_keys(l[section], values)
                    
            dimensions = (round(resolution[0]*this_section['width']), 
                          round(resolution[1]*this_section['height']))
            
            this_section['dimensions'] = dimensions
            logging.debug(f'dimensions: {dimensions}')       
        
            # set the thumbnail_size to resize the image
            if this_section['image']:
                maxsize = min(this_section['dimensions'])-this_section['padding']*2
                this_section['thumbnail_size'] = (maxsize, maxsize)
            
            # calculate the relative position if needed
            # if either of the coordinates are set as "None" - attempt to calculate the position
            if this_section['abs_coordinates'][0] is None or this_section['abs_coordinates'][1] is None:
                logging.debug(f'has calculated position')
                # store coordinates
                pos = []
                # check each value in relative section
                for idx, r in enumerate(this_section['relative']):
                    if r == section:
                        # use the value from this_section
                        pos.append(this_section['abs_coordinates'][idx])
                    else:
                        # use the value from another section
                        try:
                            pos.append(l[r]['dimensions'][idx] + l[r]['abs_coordinates'][idx])
                        except KeyError as e:
                            m = f'bad relative section value: "{r}" in section "{section}"'
                            raise KeyError(m)
                
                # save the values as a tuple
                this_section['abs_coordinates']=(pos[0], pos[1])
            else:
                logging.debug('has explict position')
                ac= this_section['abs_coordinates']
            logging.debug(f'abs_coordinates: {ac}')
                          
            # calculate fontsize
            if this_section['max_lines'] and not this_section['image']:
                # use the default font if none is specified
                if not this_section['font']:
                    this_section['font'] = self.font
                
                # calculate font sizes if it is not explicitly specified
                if not this_section['font_size']:
                    this_section['font_size'] = self._scalefont(font=this_section['font'], 
                                                               dimensions=this_section['dimensions'],
                                                               lines=this_section['max_lines'],
                                                               maxchar=this_section['maxchar'])    

            l[section] = this_section    
        return l
                              
    def _set_images(self):
        """create dictonary of all image blocks with using the current set layout
        
         Sets:
            blocks (dict): dictionary of :obj:`TextBlock`, :obj:`ImageBlock`"""
                          
        layout = self.layout
        
        blocks = {}
        for sec in layout:
            logging.debug(f'***{sec}***)')
            section = layout[sec]
            # any section with max lines accepts text
            if not section['image']: # ['max_lines']:
                logging.debug('set text block')
                blocks[sec] = Block.TextBlock(area=section['dimensions'], 
                                              text='.', 
                                              font=section['font'], 
                                              font_size=section['font_size'], 
                                              max_lines=section['max_lines'], 
                                              maxchar=section['maxchar'],
                                              hcenter=section['hcenter'], 
                                              vcenter=section['vcenter'], 
                                              inverse=section['inverse'], 
                                              rand=section['rand'], 
                                              abs_coordinates=section['abs_coordinates'])
            if section['image']:
                logging.debug('set image block')
                blocks[sec] = Block.ImageBlock(image=None, 
                                               abs_coordinates=section['abs_coordinates'], 
                                               area=section['dimensions'], 
                                               hcenter=section['hcenter'],
                                               inverse=section['inverse'], 
                                               vcenter=section['vcenter'], 
                                               padding=section['padding'], 
                                               rand=section['rand'])
        self.blocks = blocks
                              
    def update_contents(self, updates=None):
        """Update the contents of the layout
        
        Args:
            updates(dict): dictionary of keys and values that match keys in `blocks`
        
        Sets:
            blocks """
        logging.info('updating blocks')
        if not updates:
            logging.debug('nothing to do')
        
        for key, val in updates.items():
            if key in self.blocks:
                logging.debug(f'updating block: {key}')
                self.blocks[key].update(val)
            else:
                logging.debug(f'ignoring block {key}')


