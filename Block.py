#!/usr/bin/env python
#!/usr/bin/env python
# coding: utf-8


# In[8]:


#get_ipython().run_line_magic('alias', 'nbconvert nbconvert ./Block.ipynb')




# In[9]:


#get_ipython().run_line_magic('nbconvert', '')




# In[1]:


import logging
import textwrap
from random import randrange
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path

try:
    from . import constants
except ImportError as e:
    import constants




# In[2]:


# logger = logging.getLogger(__name__)
# logger.root.setLevel('DEBUG')




# In[4]:


class Block:
    """Base constructor for Block class.
    
    Individual image block used in assembling composite epdlib.Screen images 
    when writing to a WaveShare ePaper display
    
    Block objects are aware of their dimensions, absolute coordinates, and 
    contain an grayscale PIL.Image object of the specified area.
    """
    def __init__(self, area=(600, 448), hcenter=False, vcenter=False, rand=False, 
                 abs_coordinates=(0,0), padding=0, inverse=False):
        """initialize the Block object
        
        Args:
            area (:obj:`tuple` of :obj:`int`): x, y integer dimensions of 
                maximum area in pixles
            hcenter (boolean, optional): True - horizontal-align image within the area, 
                False - left-align image                
            vcenter (boolean, optional): True - vertical-align image within the area,
                False - top-align image        
            rand (boolean, optional): True - ignore vcenter, hcenter choose random position for
                image within area
            padding(int) number of pixles to pad around edge of block
            abs_coordinates (:obj:`tuple` of `int`, optional): x, y integer coordinates of image area
                within a larger image 
            inverse (boolean, optional): True - invert black and white from default of black text
            on white background
            
        Properties:
            fill (int): fill color integer of 0 (black) or 255 (white)
            bkground (int): bkground integer of 0 (black) or 255 (white)
            img_coordinates(:obj:`tuple` of :obj:`int`): coordinates of image within the block 
                (legacy, no longer used)
            image (None): None in base class 
            dimensions (:obj:`tuple` of :obj:`int`): dimensions of image in pixels"""
        
        # default to black on white background
        self.fill = 0
        self.bkground = 255
        self.dimensions = (0, 0)
        # declare img_coordinates - none until defined
        self.img_coordinates = None
        
        self.area = area
        self.padding = padding
        self.hcenter = hcenter
        self.vcenter = vcenter
        self.rand = rand
        self.inverse = inverse
        self.abs_coordinates = abs_coordinates

        # init the property
        self.image = None

    @property
    def hcenter(self):
        """:obj:`bool`: horizontallly center contents of block"""
        return self._hcenter
    
    @hcenter.setter
    def hcenter(self, hcenter):
        if not isinstance(hcenter, bool):
            raise TypeError (f'hcenter must be of type `bool`')
        else:
            self._hcenter = hcenter
                        
    
    @property
    def vcenter(self):
        """:obj:`bool`: vertically center contents of block"""
        return self._vcenter
    
    @vcenter.setter
    def vcenter(self, vcenter):
        if not isinstance(vcenter, bool):
            raise TypeError(f'vcenter must be of type `bool`')
        else:
            self._vcenter = vcenter
    
    @property
    def padding(self):
        """:obj:`int`: number of pixels to add around edge of block"""
        return self._padding
    
    
    @padding.setter
    def padding(self, padding):
        if not isinstance(padding, int):
            raise TypeError (f'padding must be of type `int`: {padding}')
        else:
            self._padding = padding
        
    
    @property
    def inverse(self):
        """:obj:`boolean`: True - invert black and white pixles
        
        Sets properties:
            fill (int): fill color (0: black, 255: white)
            bkground (int): background color (0: black, 255: white)"""
        return self._inverse
    
    @inverse.setter
    def inverse(self, inv):
        if not isinstance(inv, bool):
            raise Type
        logging.debug(f'set inverse: {inv}')
        self._inverse = inv
        if inv:
            bkground = 0
            fill = 255
        else:
            bkground = 255
            fill = 0
        
        self.fill = fill
        self.bkground = bkground
    
    @property
    def area(self):
        """:obj:`tuple` of :obj:`int`: area in pixles of imageblock
        
        Raises:
            TypeError: if not a tuple of int
            ValueError: if ints are not positive"""
        return self._area

    @area.setter
    def area(self, area):
        if self._coordcheck(area):
            self._area = area
            logging.debug(f'block area: {area}')
        else:
            raise ValueError(f'bad area value: {area}')    
    
    @property
    def abs_coordinates(self):
        """:obj:`tuple` of :obj:`int`: absolute_coordinates of area within larger image.
        
        Raises:
            TypeError: if not a tuple of int
            ValueError: if ints are not positive"""
        return self._abs_coordinates
    
    @abs_coordinates.setter
    def abs_coordinates(self, abs_coordinates):
        if self._coordcheck(abs_coordinates):
            self._abs_coordinates = abs_coordinates
            self.img_coordinates = abs_coordinates #FIXME remove this in future version
            logging.debug(f'absolute coordinates: {abs_coordinates}')
        else:
            raise ValueError(f'bad absoluote coordinates: {abs_coordinates}')
    
    def update(self, update=None):
        """Update contents of object.
        
        Placeholder method intended to be overridden by child classes
        
        Args:
            update (:obj:): data
            
        Returns:
            bool: True upon success"""
        return True
    
    def _coordcheck(self, coordinates):
        """Check that coordinates are of type int and positive.

        Args:
            coordinates (:obj:`tuple` of :obj: `int`)

        Raises:
            TypeError: if `coordinates` are not a list or tuple
            TypeError: if `coordinates` elements are not an integer
            ValueError: if `coordinates` are not >=0"""
        if not isinstance(coordinates, (tuple, list)):
            raise TypeError(f'must be type(list, tuple): {coordinates}')
        for i, c in enumerate(coordinates):
            if not isinstance(c, int):
                raise TypeError(f'must be type(int): {c}')
                return False
            if c < 0:
                raise ValueError(f'coordinates must be positive: {c}')
                return False
        return True




# In[5]:


class ImageBlock(Block):
    """Constructor for ImageBlock Class
    
    Child class of Block
    
    Individual image block used in assembling composite epdlib.Screen images 
    when writing to a WaveShare ePaper display.
    
    ImageBlock objects are aware of their dimensions, absolute coordinates, and 
    contain an grayscale PIL.Image object of the specified area.
    
    ImageBlock objects can format PIL.Image objects or jpeg/png or other supported
    image types.
    
    Format options include scaling, inverting and horizontal/vertical centering
    
    Overrides:
        image (:obj:`PIL.Image` or str): PIL image object or string path to image file
        upate (method): update contents of ImageBlock"""
    def __init__(self, image=None, *args, **kwargs):
        """Initializes ImageBlock"""
        super().__init__(*args, **kwargs)
        logging.info('ImageBlock created')
        self.image = image
        
        
    @property
    def image(self):
        """:obj:`PIL.Image`: grayscale formatted image object
        
        property accepts a PIL image object or string path to image file
            
        Sets:
            dimension (:obj:`tuple` of :obj:`int`): dimension in pixles of image"""
        return self._image
    
    @image.setter
    def image(self, image):
        image_area = Image.new('L', self.area, self.bkground)
        
        if not image:
            logging.debug(f'no image provided - setting to blank image: {self.area}')
            self._image = image_area
            return
        
        dim = min(self.area)-self.padding*2
        size = (dim, dim)
        logging.debug(f'setting usable image area to: {size} with padding {self.padding}')
       
        # handle image path
        if isinstance(image, str):
            logging.debug(f'using image file: {image}')
            try:
                im = Image.open(image)
                im.thumbnail(size)
            except (PermissionError, FileNotFoundError, OSError) as e:
                logging.warning(f'could not open image file: {image}')
                logging.warning(f'error: {e}')
                logging.warning(f'using empty image')
                self._image = image_area
                return
        elif isinstance(image, Image.Image):
            logging.debug(f'using PIL image')
            im = image
            if im.size != size:
                logging.debug(f'resizing image to {size}')
                
#                 im = im.resize(size)
                im.thumbnail(size)

        self.dimensions = im.size
        logging.debug(f'dimensions: {self.dimensions}')   
        logging.debug(f'area: {self.area}')
        
        
        x_pos = 0
        y_pos = 0
        
        if self.rand:
            # pick a random coordinate for the image
            logging.debug(f'using random coordinates')
            x_range = self.area[0] - self.dimensions[0]
            y_range = self.area[1] - self.dimensions[1] 
            logging.debug(f'x range: {x_range}, y range: {y_range}')
            x_pos = randrange(x_range)
            y_pos = randrange(y_range)
            
        # h/v center is mutually exclusive to random
        else:
            if self.hcenter:
                logging.debug(f'h centering image')
                x_pos = round((self.area[0]-self.dimensions[0])/2)
            if self.vcenter:
                logging.debug(f'v centering')
                y_pos = round((self.area[1]-self.dimensions[1])/2)
        
        if self.inverse:
            im = ImageOps.invert(im)
        
        logging.debug(f'pasting image into area at: {x_pos}, {y_pos}')
        image_area.paste(im, (x_pos, y_pos))
        
        self._image = image_area
        return
        
        
        

    def update(self, update=None):
        """Update image data including coordinates (overrides base class)
        
        Args:
            update (:obj:`PIL.Image` or str): image or string containing path to image file"""
        if update:
            try:
                self.image = update
            except Exception as e:
                logging.error(f'failed to update: {e}')
                return False
            return True
        else:
            logging.warn('update called with no arguments')
            return False

            
    
        




# In[ ]:


class TextBlock(Block):
    """Constructor for TextBlock Class
    
    Child class of Block
    
    Individual image block used in assembling composite epdlib.Screen images 
    when writing to a WaveShare ePaper display.
    
    TextBlock objects are aware of their dimensions, absolute coordinates, and 
    contain an 1 bit PIL.Image object of the specified area.
    
    TextBlock objects format strings into multi-line text using wordwrap to 
    fit the maximum number of characters on each line given a particular font.
    
    TextBlock objects will calculate the maximum number of characters that will
    reasonably fit per line based on the font face, font size, area provided and
    the character distribution for a supported language. 
    
    TTF fonts (excluding monotype faces) render each character at a different width.
    The letter i takes less space than the letter W on a line. Each language 
    inherently has a different character distribution. In English, the lower-case
    `e` appears most frequently; Portugese and Turkish use `a` most frequently. 
    
    TextBlock objects use the letter distribution from a selected language (default
    is english) to calculate a random string and then size that string to fit the 
    area. 
    
    Supported languages can be found in the constants.py file.
    
    Format options include scaling, inverting and horizontal/vertical centering.
    
    Overrides:
        image (:obj:`PIL.Image` or str): PIL image object or string path to image file
        upate (method): update contents of ImageBlock"""    
    def __init__(self, font, text='.', font_size=24, max_lines=1, maxchar=None,
                 chardist=None, *args, **kwargs):
        """Intializes TextBlock object
        
        Args:
            font (str): path to TTF font to use for rendering text
            text (str): string to render
            font_size (int): size of font in points
            max_lines (int): maximum number of lines of text to use 
            maxchar (int, optional): maximum number of characters to render
                per line. If this is not specified, it will be calculated
                using the fontface and a typical character distribution for 
                a given language (see chardist below)
            chardist (str, optional): string matching one of the character 
                distributions in constants.py (default USA_CHARDIST)
            """
        super().__init__(*args, **kwargs)
        logging.info('TextBlock created')
        self.font_size = font_size
        self.font = font
        
        if chardist:
            self._chardist = chardist
        else:
            self._chardist = constants.USA_CHARDIST
        self.max_lines = max_lines
        self.maxchar = maxchar
        self.image = None
        self.text = text
        
    def update(self, update=None):
        """Update image data including coordinates (overrides base class)
        
        Args:
            update (str): text to format and use"""
        if update:
            try:
                self.text = update
            except Exception as e:
                logging.error(f'failed to update: {e}')
                return False
            return True
    
    @property
    def font_size(self):
        """:obj:int: Size of font in points"""
        return self._font_size
    
    @font_size.setter
    def font_size(self, font_size):
        self._font_size = font_size
 
    
    @property
    def font(self):
        """:obj:Path: Path to TTF font file"""
        return self._font
    
    @font.setter
    def font(self, font):
        if font:
            self._font = ImageFont.truetype(str(Path(font).resolve()), size=self.font_size)
        else: 
            raise TypeError('font file required')
    
    @property
    def maxchar(self):
        """int: maximum number of characters per line
        
        If no value is provided, a random string of characters is generated based on the
        frequency tables: `chardist`. The default distribution is American English. 
        Based on this string the maximum number of characters for a given font and font size."""
        return self._maxchar
    
    @maxchar.setter
    def maxchar(self, maxchar):
        if maxchar:
            self._maxchar = maxchar
        else:
            s = ''
            n = 1000
            # create a string of characters containing the letter distribution
            for char in self._chardist:
                s = s+(char*int(self._chardist[char]*n))
            s_length = self.font.getsize(s)[0] # string length in Pixles
            avg_length = s_length/len(s)
            maxchar = round(self.area[0]/avg_length)
            self._maxchar = maxchar
            logging.debug(f'maximum characters per line: {maxchar}')
            

    @property
    def text(self):
        """:obj:str: raw text to be formatted.
        
        Sets:
            text (str): unformatted raw text
            text_formatted (list): of (str): wrapped text
            image (:obj:`PIL.Image`): image based on wrapped and formatted text
            img_coordinates (:obj:`tuple` of :obj:`int`): coordinates of text image adjusted 
                for size of textblock"""
        return self._text
    
    @text.setter
    def text(self, text):
        self._text = text
        self.text_formatted = self.text_formatter()
        self.image = self._text2image()
    
    def text_formatter(self, text=None, max_lines=None, maxchar=None):
        """format text using word-wrap strategies. 
        
        Formatting is based on number of lines, area size and maximum characters per line
        
        Args:
            text (str): raw text
            maxchar (int): maximum number of characters on each line
            max_lines (int): maximum number of lines
            
        Returns:
            :obj:`list` of :obj:`str`"""
        if not text:
            text = self.text
        if not maxchar:
            maxchar = self.maxchar
        if not max_lines:
            max_lines = self.max_lines
        
        wrapper = textwrap.TextWrapper(width=maxchar, max_lines=max_lines, placeholder='…')
        formatted = wrapper.wrap(text)
        logging.debug(f'formatted list:\n {formatted}')
        return(formatted)
    
    def _text2image(self):
        """Converts text to grayscale image using
        
        Sets:
            dimension (:obj:`tuple` of :obj:`int`): dimensions in pixles of image
        
        Returns:
            :obj:`PIL.Image`: image of formatted text"""
        logging.debug(f'creating blank image area: {self.area} with inverse: {self.inverse}')
        
        # create image for holding text
        text_image = Image.new('1', self.area, self.bkground)
        # get a drawing context
        draw = ImageDraw.Draw(text_image)
        
        # create an image to paste the text_image into
        image = Image.new('1', self.area, self.bkground)
        
        # set the dimensions for the text portion of the block
        y_total = 0
        x_max = 0
        for line in self.text_formatted:
            x, y = self.font.getsize(line)
            logging.debug(f'line size: {x}, {y}')
            y_total += y # accumulate height
            if x > x_max:
                x_max = x # find the longest line
                logging.debug(f'max x dim so far: {x_max}')
                
        # dimensions of text portion for formatting later
        self.dimensions = (x_max, y_total)
        logging.debug(f'dimensions of text portion of image: {self.dimensions}')     
        
        # layout the text with hcentering
        y_total = 0
        for line in self.text_formatted:
            x_pos = 0
            x, y = self.font.getsize(line)
            if self.hcenter:
                logging.debug(f'hcenter line: {line}')
                x_pos = round(self.dimensions[0]/2-x/2)
            logging.debug(f'drawing text at {x_pos}, {y_total}')
            logging.debug(f'with dimensions: {x}, {y}')
            draw.text((x_pos, y_total), line, font=self.font, fill=self.fill)
            y_total += y
            
        # produce the final image
        # Start in upper left corner
        x_pos = 0
        y_pos = 0

        if self.rand:
            logging.debug('randomly positioning text within area')
            x_range = self.area[0] - self.dimensions[0]
            y_range = self.area[1] - self.dimensions[1]
            

            x_pos = randrange(x_range)

            y_pos = randrange(y_range)

        else: # random and h/v center are mutually exclusive            
            if self.hcenter:
                x_pos = round(self.area[0]/2 - self.dimensions[0]/2)
            if self.vcenter:
                y_pos = round(self.area[1]/2 - self.dimensions[1]/2)
    
    
        logging.debug(f'pasting text portion at coordinates: {x_pos}, {y_pos}')
        image.paste(text_image, (x_pos, y_pos))
            
                
        return image


