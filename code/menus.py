from collections import namedtuple
from sprite import *
from globals import *
from client import *


class Menu:
    def __init__(self, window):
        self.pages = {}
        self.current_page = False
        self.chosen_values = {}
        self.window = window
        self.server = '127.00.00.01'
        self.screen_name = 'Player 1'
        self.client = Client(self)
        self.dev_settings = []

    def get_current_page(self):
        return self.current_page

    def set_page(self, page_name, come_back=False):
        if come_back:
            self.pages[page_name].parent = self.current_page.name
        old_page = self.current_page.name if self.current_page else False
        self.current_page = self.pages[page_name]
        if old_page:
            self.pages[old_page].exit(self.current_page)
        self.current_page.enter(old_page)

    def navigate(self, events, hovered_ids):
        for e in events:
            if e.type == pygame.MOUSEBUTTONUP:  # Unclick
                for v in [i for i in self.current_page.view() if i.id in hovered_ids]:
                    if v.name == 'Back':
                        self.set_page(self.current_page.parent)
                    elif v.type == 'link':
                        if v.dest in self.pages:
                            self.pages[v.dest].enter(self.current_page)
                            self.set_page(v.dest)

    def special_inputs(self, events, hovered_ids, pos, mouse):
        pass


class Page:
    def __init__(self, name, host, parent, background, groups=[]):
        self.name = name
        self.host = host
        self.parent = parent
        self.background = background
        self.groups = list(groups)
        self.loop_counter = 0

        self.host.pages[self.name] = self

    def view(self):
        return ([sprite
                for group in self.groups
                for sprite in group.sprites] +
                [subsprite
                 for group in self.groups
                 for sprite in group.sprites
                 for subsprite in sprite.subsprites])

    def get_sprite(self, id):
        results = [i for i in self.view() if i.id == id]
        return results[0] if results else False

    def update_positions(self, window):
        for g in self.groups:
            g.align(window)

    def process_inputs(self, events, hovered_ids, pos, mouse):
        hovered_sprites = [i for i in self.view() if i.id in hovered_ids]
        self.host.navigate(events, hovered_ids)
        self.button_click_animation(events, hovered_ids, pos, mouse)
        self.process_text_boxes(events, hovered_sprites)
        self.host.special_inputs(events, hovered_ids, pos, mouse)
        self.special_inputs(events, hovered_ids, pos, mouse)

        # Check hotkeys for devtools settings
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.mod == pygame.KMOD_LCTRL or e.mod == pygame.KMOD_RCTRL:  # Either control key is held, or both
                    if e.key == pygame.K_a:
                        print('a')

    def special_inputs(self, events, hovered_ids, pos, mouse):
        pass

    def play_snapshots(self, loop):
        pass

    def button_click_animation(self, events, hovered_ids, pos, mouse):
        # Apply tint for hover or click
        for i in self.view():
            if i.check_highlight:
                if i.id in hovered_ids and mouse[0] or i.is_active:
                    i.over_alpha = 150 if i.check_highlight != 'click_only' else 80
                    i.over_fill = True
                    i.highlight = True
                    i.over_tint = shade(i.color, shade_fraction=0.25)
                elif i.id in hovered_ids and i.check_highlight != 'click_only':
                    i.over_alpha = 80
                    i.over_fill = True
                    i.highlight = True
                    i.over_tint = shade(i.color, shade_fraction=0.25)
                else:
                    i.highlight = False

    def process_text_boxes(self, events, hovered_sprites):  # Make an 'update' method for this in sprite?
        for v in self.view():
            if v.is_text_box:
                v.input_text(events, hovered_sprites)
            elif v.is_toggle:
                if v in hovered_sprites:
                    for e in events:
                        if e.type == pygame.MOUSEBUTTONDOWN:
                            v.toggle_active = not v.toggle_active

    def enter(self, source):
        pass

    def exit(self, dest):
        pass

    def __repr__(self):
        return 'Page(%s)' % self.name

    def manage_connection(self, loop):
        pass

    def upkeep(self):
        pass


class Group:
    def __init__(self, name, page, sprites, align_dim, align_ref, align_pos, align_skew,
                      dist_dim, dist_ref, low=0, center=0, high=0, spacing=0, fixed_size=False, couple=False):
        self.name = name
        self.page = page
        self.sprites = sprites
        self.align_dim = align_dim
        self.align_ref = align_ref
        self.align_pos = align_pos
        self.align_skew = align_skew
        self.dist_dim = dist_dim
        self.dist_ref = dist_ref
        self.low = low
        self.center = center
        self.high = high
        self.spacing = spacing
        self.fixed_size = fixed_size
        self.couple = couple

        self.page.groups.append(self)

    def align(self, window):
        try:
            if self.couple:
                for i in self.sprites:
                    coupled_sprite = i.__dict__[self.couple]  # i.e. self.space
                    if coupled_sprite:
                        i.x_target, i.y_target = coupled_sprite.x, coupled_sprite.y
            else:
                window.align_sprites(self.sprites, self.align_dim, self.align_ref, self.align_pos, self.align_skew,
                                     self.dist_dim, self.dist_ref, low=self.low, center=self.center, high=self.high,
                                     spacing=self.spacing, fixed_size=self.fixed_size)
            for i in self.sprites:
                i.update_subsprites()
        except AttributeError as e:
            print('Error while Aligning', self)
            print(e)

    def __repr__(self):
        return 'Group(%s)' % self.name


