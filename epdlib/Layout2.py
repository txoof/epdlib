#!/usr/bin/env python
#!/usr/bin/env python
# coding: utf-8


# In[73]:


#get_ipython().run_line_magic('load_ext', 'autoreload')
#get_ipython().run_line_magic('autoreload', '2')

#get_ipython().run_line_magic('reload_ext', 'autoreload')




# In[75]:


#get_ipython().run_line_magic('alias', 'nbconvert nbconvert Layout2.ipynb')
#get_ipython().run_line_magic('nbconvert', '')




# In[1]:


import logging
from pathlib import Path
import copy
from PIL import Image, ImageDraw, ImageFont




# In[2]:


try:
    from . import constants
except ImportError as e:
    import constants
    
try: 
    from . import Block as Block
except ImportError as e:
    import Block as Block




# In[3]:


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




# In[61]:


class Layout:
    
    def __init__(self, resolution, layout=None):
        logging.debug('creating layout')           
        self.resolution = resolution
        self.layout = layout
        
    @property
    def resolution(self):
        return self._resolution
    
    
    @resolution.setter
    @strict_enforce((list, tuple))
    def resolution(self, resolution):
        for each in resolution:
            if each < 0:
                raise ValueError(f'resolution must be positive integers: {each}')
        
        self._resolution = resolution
        
    
    @property
    def layout(self):
        return self._layout
    
    @layout.setter
    def layout(self, layout):
        if layout:
            logging.debug(f'calculating layout for resolution {self.resolution}')
        else:
            self._layout = None
            return
        
        self._layout = copy.deepcopy(layout)
        logging.debug(f'layout id({id(self._layout)})')
        self._calculate_layout()
        self._set_images()
        
    def _calculate_layout(self):
        if not self.layout:
            return None
        
        # required values that will be used in calculating the layout
        values = {'image': None, 'max_lines': 1, 'padding': 0, 'width': 1, 'height': 1, 
                  'abs_coordinates': (None, None), 'hcenter': False, 'vcenter': False, 
                  'rand': False, 'inverse': False, 'relative': False, 'font': None, 
                  'font_size': None, 'maxchar': None, 'dimensions': None}               
        
        for section in self.layout:
            logging.debug(f'*****{section}*****')
            this_section = self._check_keys(self.layout[section], values)
            dimensions = (round(self.resolution[0]*this_section['width']),
                          round(self.resolution[1]*this_section['height']))
                    
            this_section['dimensions'] = dimensions
            logging.debug(f'dimensions: {dimensions}')
            
            # set the thumbnail_size for resizing images
            if this_section['image']:
                maxsize = min(this_section['dimensions'])
                this_section['thumbnail_size'] = (maxsize, maxsize)
            
            # calculate the relative position if either of the abs_coordinate X or Y is None
            if this_section['abs_coordinates'][0] is None or this_section['abs_coordinates'][1] is None:
                logging.debug(f'section has calculated position')
                pos = []
                # check each value in relative section
                for idx, r in enumerate(this_section['relative']):
                    if r == section:
                        # use the value from this section
                        pos.append(this_section['abs_coordinates'][idx])
                    else:
                        # use the value from another section
                        try:
                            pos.append(self.layout[r]['dimensions'][idx] + self.layout[r]['abs_coordinates'][idx])
                        except KeyError as e:
                            m = f'bad relative section value: "{r}" in section "{section}"'
                            raise KeyError(m)
                
                # save the values as a tuple
                this_section['abs_coordinates']=(pos[0], pos[1])
            else:
                logging.debug('section has absolute coordinates')
                ac = this_section['abs_coordinates']
            logging.debug(f'coordinates: {ac}')
            
            # calculate fontsize
            if not this_section['font_size'] and not this_section['image']:
                this_section['font_size'] = self._scalefont(font=this_section['font'], 
                                                            dimensions=this_section['dimensions'],
                                                            lines=this_section['max_lines'],
                                                            maxchar=this_section['maxchar'])
                
    def _scalefont(self, font, dimensions, lines, maxchar, text="W W W "):
        if not maxchar:
            maxchar = 6
        
        font = str(Path(font).resolve())
        
        logging.debug(f'calculating maximum font size for area: {dimensions}')
        logging.debug(f'using font: {font}')
        
        # start calculating at size = 1
        fontsize = 1
        x_fraction = .85 # fraction of x height to use
        y_fraction = .70 # fraction of y width to use
        xtarget = dimensions[0]/x_fraction # target width of font
        ytarget = dimensions[1]/lines*y_fraction # target heigight of font
        
        logging.debug(f'target X font dimension {xtarget}')
        logging.debug(f'target Y font dimension {ytarget}')
        
        testfont = ImageFont.truetype(font, fontsize)
        
        fontdim = testfont.getsize(text)
        
        cont = True
        
        while cont:
            fontsize += 1
            testfont = ImageFont.truetype(font, fontsize)
            
            fontdim = testfont.getsize(text)
            if fontdim[0] > xtarget:
                cont = False
                logging.debug(f'X target reached')
                
            if fontdim[1] > ytarget:
                cont = False
                logging.debug(f'Y target reached')
                
        # back off one
        fontsize -= 1
        logging.debug(f'test string: {text}; pixel dimensions for fontsize {fontsize}: {fontdim}')
        return fontsize
        
    
        
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
    
    def _check_keys(self, dictionary, values):
        logging.debug('checking layout keys')
        for k, v in values.items():
            try:
                dictionary[k]
            except KeyError as e:
                logging.debug(f'adding key: {k}: {v}')
                dictionary[k] = v
        return dictionary
    
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




# In[62]:


# logger = logging.getLogger(__name__)
# logger.root.setLevel('DEBUG')




# In[63]:


# l = Layout(resolution=(600, 440), layout=lo)
# q = Layout(resolution=(300, 200), layout=lo)




# In[66]:


# l.update_contents(update)
# q.update_contents(update)




# In[71]:


# l.blocks['temperature'].image




# In[72]:


# q.blocks['temperature'].image




# In[64]:


# update = {
#     'weather_img': '../Avatar_cloud.png',      # weather_img block will recieve a .png
#     'temperature': '15C',                     # temperature block will receive `15C`
#     'forecast': 'Partly cloudy throughout the day with an east wind at 3m/s. High of 20, 12 overnight.'
# }




# In[41]:


# lo = { # basic two row layout
#     'weather_img': {                
#             'image': True,               # image block
#             'width': 1/2,                  # 1/1 of the width - this stretches the entire width of the display
#             'height': 1/4,               # 1/3 of the entire height
#             'abs_coordinates': (0, 0),   # this block is the key block that all other blocks will be defined in terms of
#             'hcenter': True,             # horizontally center text
#             'vcenter': True,             # vertically center text 
#             'relative': False,           # this block is not relative to any other. It has an ABSOLUTE position (0, 0)
#         },
#     'temperature': { 
#                 'image': None,
#                 'max_lines': 1,
#                 'padding': 10,
#                 'width': 1/2,
#                 'height': 1/4,
#                 'abs_coordinates': (None, 0),
#                 'hcenter': True,
#                 'vcenter': True,
#                 'relative': ['weather_img', 'temperature'],
#                 'font': '../fonts/Open_Sans/OpenSans-ExtraBold.ttf',
#                 'font_size': None
#     },
#     'forecast': {
#                 'image': None,
#                 'max_lines': 5,
#                 'padding': 10,
#                 'width': 1,
#                 'height': 1/2,
#                 'abs_coordinates': (0, None),
#                 'hcenter': False,
#                 'vcenter': True,
#                 'relative': ['forecast', 'temperature'],
#                 'font': '../fonts/Open_Sans/OpenSans-Regular.ttf',
#                 'font_size': None
#     }

# }




# In[ ]:





