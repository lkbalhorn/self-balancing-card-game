# This is my compilation of general-purpose classes and methods built from Pygame, which can be used either for
# games or other applications.
import pygame
from LkGUI import *
from pygame.locals import *

# screen parameters
y_skew = -20

class frame():  # A list-like object that can be used to make trees
    def __init__(self, name):
        self.name = name
        self.parent = 'none'
        self.contents = []

    def repr(self):
        return self.name

    def __len__(self):
        return len(self.contents)

    def __getitem__(self, position):
        return self.contents[position]

    def append(self, item):
        self.contents.append(item)

    def remove(self, item):
        self.contents.remove(item)

    def search(self):  # Returns contents of self and of children with frames.  Watch out for duplicates and recursion.
        items = self.contents
        for i in [j for j in self.contents if hasattr(j, 'search')]:
            items = items + i.search
        return items


class FadeImage(pygame.Surface):
    def __init__(self,filename,width,height):
        super().__init__([width,height])
        self.width = width
        self.height = height
        self.w = width
        self.h = height
        self.photo = pygame.image.load(filename).convert_alpha()
        pygame.transform.scale(self.photo,(width,height),self)
        self.status = ''
        self.Player = ''
        # Come back later so it's not loading a photo every time


def wrap_text_2(surface, text, xmin, ymin, xmax, ymax,
                alignment = 'center', line_spacing = -2, font = 'arial', fontsize = 20, font_color = (0,0,0)):

    # Parse string into individual words
    words = text.split(' ')
    for i,w in enumerate(words):
        words[i] = w + ' '  # Add spaces back in

    # Loop until all words fit in the box.  Shrink the font if necessary.
    lines_ready = False
    while not lines_ready:

        # Generate font
        complete_font = pygame.font.SysFont(font, int(fontsize))
        font_height = complete_font.size('Nonsense')[1]

        # Render words into font
        printed_words = []
        for w in words:
            p = complete_font.render(w, 1, font_color)
            printed_words.append(p)

        # Split words into lines
        line_width = xmax - xmin
        current_word = 0
        max_lines = int((ymax-ymin)/font_height)
        lines = [[]] * max_lines  # Create a list of lists, with length max_lines
        for i in range(max_lines):
            lines[i] = []
            current_width = 0
            line_full = False
            while not line_full and current_word < len(words):
                word_width = pygame.Surface.get_width(printed_words[current_word])
                if current_width + word_width < line_width:
                    lines[i].append(printed_words[current_word])
                    current_width += word_width
                    current_word += 1
                else:
                    line_full = True

        # Check if all words fit in the box.  If not, shrink font and try again.
        if current_word == len(words):  # Because current_word starts counting at 0
            lines_ready = True
        else:
            fontsize -= 2
            if fontsize < 5:
                return False  # Text wrapping fails


    # Set word positions based on alignment, then blit them to surface
    for i, line in enumerate(lines):
        current_line_width = sum([pygame.Surface.get_width(p) for p in line])
        if alignment == 'left':
            shift = 0
        elif alignment == 'right':
            shift = line_width - current_line_width
        elif alignment == 'center':
            shift = (line_width - current_line_width)/2
        n_filled_lines = len([j for j in lines if j])
        vertical_shift = (max_lines-n_filled_lines)/2 * font_height
        for p in line:
            surface.blit(p,(xmin + shift, ymin + i*(font_height + line_spacing)+ vertical_shift))
            shift += pygame.Surface.get_width(p)

    return True


def recenter(centered_items,xc,yc,new_xc,new_yc):
    dx = new_xc - xc
    dy = new_yc - yc
    centered_set = set(centered_items)
    for s in centered_set:
        if hasattr(s,'sticky'):
            if s.sticky == 'Left':
                # no change to x
                s.y += dy
            if s.sticky == 'Right':
                s.x += 2*dx
                s.y += dy
        else:
            s.x += dx
            s.y += dy


def align(items, dimension, value, skew=0.5):
    # Skew of 0 is align top/left, 0.5 is align center, 1 is align bottom/right, and everything in between
    for i in items:
        if i.is_static:
            if dimension == 0:  # x values
                i.x = value - i.w * skew
            elif dimension == 1:  # y values
                i.y = value - i.h * skew
        else:
            if dimension == 0:  # x values
                i.x_target = value - i.w * skew
            elif dimension == 1:  # y values
                i.y_target = value - i.h * skew

def distribute(items, dimension, low=0, center=0, high=0, spacing=0, fixed_size = False):
    # Find the total size of all the objects in this dimension
    if fixed_size:
        size_sum = fixed_size * len(items)
    elif dimension == 0:  # distribute along x
        size_sum = sum([i.w for i in items])
    else:
        size_sum = sum([i.h for i in items])

    # Two of the four parameters must be defined, the others can be solved for.
    n_items = len(items)
    if low and center:
        high = 2*center - low
        spacing = (high - low - size_sum) / (n_items - 1)
    elif low and high:
        center = (high + low) / 2
        spacing = (high - low - size_sum) / (n_items - 1)
    elif center and high:
        low = 2*center - high
        spacing = (high - low - size_sum) / (n_items - 1)
    elif low and spacing:
        high = low + size_sum + spacing*(n_items-1)
        center = (high + low) / 2
    elif center and spacing:
        high = center + (size_sum + spacing*(n_items-1)) / 2
        low = 2 * center - high
    elif high and spacing:
        low = high - size_sum - spacing*(n_items-1)
        center = (high + low) / 2
    else:
        raise 'Distribute requires two nonzero keyword arguments'

    # Assign positions
    current_pos = low  # must be tracked because items can be of different sizes
    if dimension == 0:
        for i in items:
            if i.is_static:
                i.x = int(current_pos)
            else:
                i.x_target = int(current_pos)
            if fixed_size:
                current_pos += (spacing + fixed_size)
            else:
                current_pos += (spacing + i.w)
    else:
        for i in items:
            if i.is_static:
                i.y = int(current_pos)
            else:
                i.y_target = int(current_pos)
            if fixed_size:
                current_pos += (spacing + fixed_size)
            else:
                current_pos += (spacing + i.h)

def grid(sprites, startx, starty, rows, columns, xspacing = 10, yspacing = 10):
    total = len(sprites)
    for i in range(rows):
        for j in range(columns):
            n = j + i*columns
            if n < total:
                c = sprites[n]
                c.x = startx + j*(c.width + xspacing)
                c.y = starty + i*(c.height + yspacing)



def tint_surface(color,alpha, width, height):
    image = pygame.Surface([width,height])
    image.fill(color)
    image.set_alpha(alpha)
    return image


def shade(color, shade_fraction = 0.5, shade_color = (0,0,0)):
    red = int(shade_color[0]*shade_fraction + color[0]*(1-shade_fraction))
    green = int(shade_color[1]*shade_fraction + color[1] * (1-shade_fraction))
    blue = int(shade_color[2]*shade_fraction + color[2] * (1-shade_fraction))
    return (red, green, blue)


def ColorScheme():
    # Color Dictionary for loading cards, images
    Colors = {'Neutral':(200, 200, 225),
              'Red':(255, 150, 150),
              'Blue':(100, 150, 255),
              'Light Blue':(200,225,255),
              'Green':(160, 255, 160),
              'Purple':(255, 160, 255),
              'White':(230, 230, 230),
              'Yellow':(255, 255, 160),
              'Black':(150, 150, 150),
              'Wood':(255, 200, 150),
              'Dark_Wood':(205,150,100)}
    return Colors

