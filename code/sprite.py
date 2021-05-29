import pygame


class Sprite:
    # This is my own sprite class, not related to the Pygame sprite class
    def __init__(self, **kwargs):
        # Create permanent ID
        self.id = str(id(self))

        # Set up general attributes
        self.name = 'sprite'
        self.type = 'sprite'
        self.location = False
        self.status = False

        # Set up geometry variables
        self.w = 100  # Using 100 instead of 0 for possible troubleshooting with grey boxes
        self.h = 100
        self.x = 100
        self.y = 100

        # Set up visual variables
        self.color = (128, 128, 128)
        self.color_name = 'grey'
        self.filename = False
        self.template_filename = False
        self.fill = True
        self.border = 5
        self.fontsize = 20
        self.font_color = (0, 0, 0)
        self.alignment = 'center'
        self.alpha = 255  # Transparency

        self.text = False
        self.border_color = False
        self.colorkey = False
        self.artwork = False
        self.highlight = False
        self.check_highlight = True
        self.is_active = False
        self.is_hidden = False
        # Overlay
        self.over_tint = (0, 0, 0)  # For tinting the sprite
        self.over_alpha = 0
        self.over_fill = True


        # Widget Attributes
        self.is_toggle = False
        self.toggle_active = False
        # Text Boxes
        self.is_text_box = False
        self.old_text = False

        # Set up animation variables
        self.is_static = True
        self.image_traits = ['w', 'h', 'color', 'text', 'toggle_active']
        self.layer = 0
        self.x_target = 0
        self.y_target = 0
        self.update = True
        self.drag_with_mouse = False
        self.x_rel_mouse = 0
        self.y_rel_mouse = 0
        self.lock_to_object = False
        self.subsprites = []  # Positions are relative to their host
        self.host = False

        self.changed = True  # Image will re-update if it is changed.  Must be toggled for each object.
        self.base = False  # Background for drawing objects more quickly

        self.dest = False

        # Game-specific variables - should go in a subclass eventually?
        self.is_target = False
        self.is_card = False
        self.Player = None

        # Process additional arguments
        for key in kwargs:
            self.__dict__[key] = kwargs[key]

    def draw_image(self, artwork=False, template=False, extras=[]):
        # Create image surface
        new_image = pygame.Surface([self.w, self.h])

        # Fill Box
        if self.fill:
            if self.color:
                new_image.fill(self.color)
            if self.alpha < 255:
                new_image.set_alpha(self.alpha)
        else:
            # Set transparent middle
            new_image.fill(self.color)
            new_image.set_colorkey(self.color)

        # Add Artwork
        if artwork:
            scaled_art = pygame.transform.scale(artwork, (self.w, self.h))
            new_image.blit(scaled_art, (0, 0))

        # Draw Outline
        if self.border > 0 and not self.fill:
            # Use true color for outline
            pygame.draw.rect(new_image, self.color, [0, 0, self.w, self.h], self.border)
        elif self.border > 0:
            # Use modified color for outline
            if self.border_color:
                line_color = self.border_color
            else:
                line_color = shade(self.color)
            pygame.draw.rect(new_image, line_color, [0, 0, self.w, self.h], self.border)

        # Draw Text
        if self.text:
            buffer = 2*self.border
            wrap_text_2(new_image, self.text, buffer, buffer, self.w - buffer, self.h - buffer,
                        alignment=self.alignment, fontsize=self.fontsize, font_color=self.font_color)

        # Set Colorkey
        if self.colorkey:
            if self.colorkey == 'get corner':
                self.colorkey = new_image.get_at((1, 1))[:3]
            new_image.set_colorkey(self.colorkey)

        # Adjust Transparency
        new_image.set_alpha(self.alpha)
        if self.alpha == 1:
            new_image.convert()
        else:
            new_image.convert_alpha()

        return new_image, None

    def decorate(self, screen):
        # Various things that need to be drawn after the object is blitted on screen

        # Status Outlines that 'Pop'
        if self.is_target or self.status == 'available' or self.status == 'active':
            if self.is_target:
                color = (255,50,50)
                shift = 2
                line_w = 6
            elif self.status == 'available':
                color = (0,200,255)
                shift = 2
                line_w = 6
            elif self.status == 'active':
                color = (50,255,0)
                shift = 4
                line_w = 12
            big_w = self.w + 2*shift
            big_h = self.h + 2*shift
            glow = pygame.Surface((self.w + 2*shift, self.h + 2*shift))
            glow.fill((0, 0, 0))
            glow.set_colorkey((0, 0, 0))
            k = 3
            points_list = [(2+shift, 0), (big_w - 4-shift, 0), (big_w, 4+shift), (big_w, big_h - 6-shift),
                           (big_w - 6-shift, big_h), (6+shift, big_h), (0, big_h - 6-shift), (0, 2+shift)]
            pygame.draw.polygon(glow, color, points_list, line_w)
            screen.blit(glow, (self.x - shift, self.y - shift))

        if self.highlight or self.is_active:
            # Apply Over Tint
            overlay = pygame.Surface((self.w, self.h))
            if self.over_fill:
                overlay.fill(self.over_tint)
            else:
                overlay.fill((0, 0, 0))
                overlay.set_colorkey((0, 0, 0))
                pygame.draw.rect(overlay, self.over_tint, (0, 0, self.w, self.h), self.border)
            overlay.set_alpha(self.over_alpha)
            screen.blit(overlay, (self.x, self.y))

    def collide(self, position):
        x, y = position
        if self.x <= x <= self.x + self.w:
            if self.y <= y <= self.y + self.h:
                return True
        return False

    def __repr__(self):
        return '%s(%s)' % (self.name, self.location)

    def clone(self):
        return self

    def update_subsprites(self):
        pass

    # Text Box Effects
    def activate(self):
        self.toggle_active = True
        self.old_text = self.text
        self.text = ''

    def deactivate(self):
        if self.text == '':
            self.text = self.old_text
        self.toggle_active = False

    def toggle(self):
        if self.toggle_active:
            self.deactivate()
        else:
            self.activate()

    def input_text(self, events, hovered_sprites):
        if self.toggle_active:
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.deactivate()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.deactivate()
                    elif event.key == pygame.K_BACKSPACE:
                        self.text = self.text[:-1]
                    else:
                        self.text += event.unicode
        else:
            for e in events:
                if e.type == pygame.MOUSEBUTTONUP:
                    if self in hovered_sprites:
                        self.activate()

        return self.text


class Ellipse(Sprite):
    def __init__(self, **kwargs):
        super().__init__()
        self.center_x = 10
        self.center_y = 10
        self.rx = 10
        self.ry = 10
        self.max_w = False

        # Process additional arguments
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def draw_image(self, artwork=False, template=False, extras=[]):
        # Create image surface
        new_image = pygame.Surface([self.w, self.h])

        # Calculate rectangle holding ellipse using internal coordinates
        rect = (0, 0, self.w, self.h)
        if self.fill:
            pygame.draw.ellipse(new_image, self.color, rect)
            line_color = shade(self.color)
            pygame.draw.ellipse(new_image, line_color, rect, self.border)
        else:
            pygame.draw.ellipse(new_image, self.color, rect, self.border)

        # Draw Text
        if self.text:
            buffer = 2*self.border
            wrap_text_2(new_image, self.text, buffer, buffer, self.w - buffer, self.h - buffer,
                        alignment='center', fontsize=self.fontsize, font_color=self.font_color)

        # Set Colorkey
        if self.colorkey:
            new_image.set_colorkey(self.colorkey)
        return new_image, None

    def decorate(self, screen):
        # Various things that need to be drawn after the object is blitted on screen
        if self.is_target:
            color = (255, 50, 50)
            line_w = 5
            pygame.draw.ellipse(screen, color, (self.x, self.y, self.w, self.h), line_w)

        if self.highlight or self.is_active:
            # Apply Over Tint
            overlay = pygame.Surface((self.w, self.h))
            overlay.fill((0, 0, 0))
            overlay.set_colorkey((0, 0, 0))
            rect = (0, 0, self.w, self.h)
            if self.over_fill:
                pygame.draw.ellipse(overlay, self.over_tint, rect)
            else:
                pygame.draw.ellipse(overlay, self.over_tint, rect, self.border)
            if self.max_w and self.w > self.max_w:
                # Trim edges
                buffer = (self.w - self.max_w) / 2
                pygame.draw.rect(overlay, (0, 0, 0), (0, 0, buffer, self.h))
                pygame.draw.rect(overlay, (0, 0, 0), (self.w - buffer, 0, self.w, self.h))
                overlay.set_colorkey((0, 0, 0))
            overlay.set_alpha(self.over_alpha)
            screen.blit(overlay, (self.x, self.y))

    def collide(self, position):
        x, y = position
        if self.x <= x <= self.x + self.w:
            if self.y <= y <= self.y + self.h:
                return True
        return False


def wrap_text_2(surface, text, xmin, ymin, xmax, ymax,
                alignment = 'center', line_spacing = -2, font = 'arial', fontsize = 20, font_color = (0,0,0)):

    # Parse string into individual words
    words = text.split(' ')
    for i, w in enumerate(words):
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
        else:
            shift = (line_width - current_line_width)/2
        n_filled_lines = len([j for j in lines if j])
        vertical_shift = (max_lines-n_filled_lines)/2 * font_height
        for p in line:
            surface.blit(p,(xmin + shift, ymin + i*(font_height + line_spacing)+ vertical_shift))
            shift += pygame.Surface.get_width(p)

    return True


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


def distribute(items, dimension, low=0, center=0, high=0, spacing=10, fixed_size = False):

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
        # Assume center=0, spacing=10
        # pass
        print('Distribute requires two nonzero keyword arguments')
        raise

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


def shade(color, shade_fraction=0.5, shade_color=(0, 0, 0)):
    red = int(shade_color[0]*shade_fraction + color[0]*(1-shade_fraction))
    green = int(shade_color[1]*shade_fraction + color[1] * (1-shade_fraction))
    blue = int(shade_color[2]*shade_fraction + color[2] * (1-shade_fraction))
    return red, green, blue
