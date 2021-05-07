import random
import time  # For troubleshooting performance
import os
import json

import pygame

from sprite import *
from globals import *


class Card(Sprite):
    # This class represents a card, whether in the deck, in a hand, on the board, or
    # discarded
    def __init__(self, player=False):
        super().__init__()

        # Attributes that need adjustments before serializing
        self.player = player
        self.location = False
        self.aura_list = []  # I think this can be server-only

        # Attributes to aid with serialization
        self.player_id = False
        self.location_type = 'None'
        self.space = False

        # Server + Client Attributes
        self.attack = False
        self.health = None
        self.amount = 0
        self.name = 'Card'
        self.long_name = False
        self.cost = None
        self.ability_cost = None
        self.type = False
        self.special = []
        self.tags = []
        self.handicap = 0
        self.priority = 0
        self.status = 'none'
        self.is_card = True
        self.is_tapped = False
        self.is_new = False
        self.is_available = False
        self.color_name = None
        self.active_locations = []
        self.duration = 0

        self.starting_cost = None
        self.starting_ability_cost = None
        self.starting_attack = 0
        self.starting_health = 0
        self.max_health = 0
        self.starting_amount = 0
        self.starting_special = []
        self.starting_tags = []

        self.visible = True  # Clean up these three
        self.is_revealed = False
        self.is_hidden = True
        self.layer = 1
        self.check_hover = False

        self.is_alive = True
        self.last_hit = False
        self.toggle_active = False

        # Client Only Attributes
        self.targets = []
        self.is_target = False
        self.n_hand_targets = 1
        self.n_board_targets = 1

        self.image_traits = ['w', 'h', 'color', 'text', 'size', 'status', 'cost', 'ability_cost', 'attack', 'health',
                             'quantity']
        self.key_traits = ['id', 'player',
                           'is_card', 'is_static',
                           'color_name', 'type', 'status',
                           'location', 'color', 'handicap',
                           'attack', 'health', 'cost', 'ability_cost', 'special_text', 'space',
                           'name', 'long_name', 'filename',
                           'n_hand_targets', 'n_board_targets', 'special', 'tags'
                           ]
        self.color = (0, 0, 0)
        self.special_text = False

        self.size = 'small'
        self.w = 0
        self.h = 0
        self.resize()

        # Animation Variables
        self.is_static = False

        # Set up out-of-game variables
        self.quantity = 1
        self.summary = False
        self.set = 0

    def __repr__(self):
        return '%s(%s)' % (self.long_name, self.location)

    def clone(self):
        new_card = Card(self.player)
        for item in self.key_traits:
            new_card.__dict__[item] = self.__dict__[item]
        new_card.id = id(new_card)
        return new_card

    def encode(self, hide_from_player=False):
        # Prepares Card object for JSON serialization.
        simple_dict = {}
        for attr in self.key_traits:
            simple_dict[attr] = self.__dict__[attr]
        if self.space:
            simple_dict['space'] = self.space.column
        if self.location:
            simple_dict['location_type'] = self.location.type
            simple_dict['location'] = False
        simple_dict['player_id'] = self.player.id if self.player else False
        simple_dict['location_id'] = self.location.id if self.location else False
        return simple_dict

    def decode(self, simple_dict):
        new = load_card(simple_dict['name'])
        for attr in self.key_traits:
            new.__dict__[attr] = simple_dict[attr]
        return new

    def resize(self):
        # Good way to put all of the size data in one place, and other size-change factors
        if self.size == 'small':
            self.w, self.h = 100, 120
            self.check_highlight = True
        elif self.size == 'big':
            self.w, self.h = 195, 260
            self.check_highlight = 'click_only'
            self.highlight = False
        elif self.size == 'emblem':
            self.w, self.h = 70, 100
            self.check_highlight = True
        elif self.size == 'summary':
            self.w, self.h = 300, 30
            self.check_highlight = True

        if self.name == 'Hero':
            self.w, self.h = 140, 200
            self.check_hover = False

    def draw_image(self, artwork=False, template=False, extras=[]):
        tic = time.time()

        # Create surface in correct size
        self.resize()
        new_image = pygame.Surface([self.w, self.h])

        if self.size == 'summary':
            breaks = [30, 60, 270]
            pygame.draw.rect(new_image, Colors['Mana'], [0, 0, 30, 30])
            pygame.draw.rect(new_image, Colors['Handicap'], [30, 0, 60, 30])
            pygame.draw.rect(new_image, self.color, [60, 0, self.w - 30, self.h])
            pygame.draw.rect(new_image, (150, 100, 150), [self.w - 30, 0, self.w, self.h])
            pygame.draw.rect(new_image, Colors['Dark Blue'], [0, 0, self.w, self.h], 1)

            buffer = -5

            wrap_text_2(new_image, str(self.cost), 0, 2, breaks[0] - buffer, self.h - buffer,
                        alignment='center', fontsize=20, font_color=(0, 0, 0))
            wrap_text_2(new_image, '%.0f' % self.handicap, breaks[0], 2, breaks[1] - buffer, self.h - buffer,
                        alignment='center', fontsize=20, font_color=(0, 0, 0))
            wrap_text_2(new_image, self.long_name, breaks[1], 2, breaks[2] - buffer, self.h - buffer,
                        alignment='center', fontsize=20, font_color=(0, 0, 0))
            wrap_text_2(new_image, str(self.quantity), breaks[2], 2, self.w - buffer, self.h - buffer,
                        alignment='center', fontsize=20, font_color=(0, 0, 0))

            return new_image, None

        if self.name == 'Card':  # Blank place holder for a face-down card
            pygame.draw.rect(new_image, (0,0,0), [0, 0, self.w, self.h])
            pygame.draw.rect(new_image, (100, 0, 75), (0, 0, self.w, self.h), 7)
            return new_image, None

        f = self.w**0.5/8  # Attempt at smooth scaling using square root

        card_art = artwork

        # Set Fonts
        if self.size == 'big':
            font_dictionary = BigFonts
        else:
            font_dictionary = CardFonts
        cost_font = font_dictionary['cost']
        inner_cost_font = font_dictionary['cost inner']
        attack_font = font_dictionary['attack']
        health_font = font_dictionary['health']
        h_font = font_dictionary['handicap']
        name_font = font_dictionary['name']
        special_font = font_dictionary['special']

        if card_art:
            if self.size == 'small' or self.size == 'emblem':
                scaled_art = pygame.transform.scale(card_art, (int(self.h*1.61), self.h))
                x_trim = int(self.h*1.61 - self.w)/2
                new_image.blit(scaled_art,(0,0),(x_trim, 0, self.h*1.61-x_trim, self.h))
            else:
                new_image.fill(self.color)
                scaled_art = pygame.transform.scale(card_art, (int(self.h*1.61/2), int(self.h/2)))
                new_image.blit(scaled_art, (-15, 0))
        else:
            pygame.draw.rect(new_image, self.color, [0, 0, self.w, self.h])

        # Choose items to draw and blit templates
        if self.size == 'big':
            if self.type == 'Minion':
                items = ['cost', 'attack', 'health', 'handicap', 'name', 'text', 'tags']
                new_image.blit(CardTemplates['big'], (0, 0))
            elif self.type == 'Structure':
                items = ['cost', 'health', 'handicap', 'name', 'text', 'tags']
                new_image.blit(CardTemplates['big structure'], (0, 0))
            else:
                items = ['cost', 'handicap', 'name', 'text', 'tags']
                new_image.blit(CardTemplates['big spell'], (0, 0))
        elif self.name == 'Hero':
            items = ['health', 'attack']
        elif self.location.type == 'hand':
            items = ['cost']
            new_image.blit(CardTemplates['hand spell'], (0, 0))
        elif self.location.type == 'board':
            if self.type == 'Minion':
                items = ['attack', 'health']
            elif self.type == 'Structure':
                items = ['health']
            new_image.blit(CardTemplates['board'], (0, 0))
        elif self.location.type == 'tableau':
            if self.type == 'Item':
                items = []
            elif self.type == 'Skill':
                items = ['ability_cost']
        else:
            items = ([])
        if not artwork:
            items.append('small name')

        # Draw Cost Label
        if 'cost' in items:
            if 'Star' in self.special:
                cost = "*"
                cost_label = special_font.render(cost, 1, (0, 0, 0))
            else:
                cost = str(self.cost)
                cost_label = cost_font.render(cost, 1, (0, 0, 0))
            new_image.blit(cost_label, (7 * f, 3 * f))

        # Draw Attack Label
        if 'attack' in items:
            if self.size == 'small':
                pygame.draw.polygon(new_image, (200,100,100), chamfer(0, self.h,f*24,f*16,1,-1))
                pygame.draw.polygon(new_image, (100,50,50), chamfer(0, self.h,f*24,f*16,1,-1), 2)
            attack = str(self.attack)
            attack_label = attack_font.render(attack, 1, (0, 0, 0))
            new_image.blit(attack_label, (7 * f, self.h - 23 * f))

        # Draw health Label
        if 'health' in items:
            if self.size == 'small':
                pygame.draw.polygon(new_image, (100,200,100), chamfer(self.w, self.h,f*24,f*16,-1,-1))
                pygame.draw.polygon(new_image, (50,100,50), chamfer(self.w, self.h,f*24,f*16,-1,-1), 2)
            health = str(self.health)
            health_label = health_font.render(health, 1, (0, 0, 0))
            new_image.blit(health_label, (self.w - health_label.get_rect()[2]/1.5 - 9*f, self.h - 23 * f))

        # Draw Handicap Icon
        if 'handicap' in items:
            handicap = str(int(round(self.handicap)))
            handicap_label = h_font.render(handicap, 1, (220, 220, 255))
            adjust = len(handicap)
            new_image.blit(handicap_label, (24.5*f - adjust, 11*f))

        # Draw Ability Cost Icon
        if 'ability_cost' in items:
            length = self.w / 4
            shift = self.w / 4
            # points = [(self.w / 2, self.h / 2 + length + shift), (self.w / 2 - length, self.h / 2 + shift),
            #           (self.w / 2, self.h / 2 - length + shift), (self.w / 2 + length, self.h / 2 + shift)]
            points = [(0, self.h), (self.w, self.h), (self.w / 2, self.h - self.w / 2)]
            pygame.draw.polygon(new_image, Colors['Mana'], points)
            pygame.draw.polygon(new_image, shade(Colors['Mana']), points, 2)
            ability_cost = str(int(round(self.ability_cost)))
            ability_cost_label = cost_font.render(ability_cost, 1, (0, 0, 0))
            adjust = len(ability_cost)
            new_image.blit(ability_cost_label, (self.w / 2 - adjust * 5, self.h - length - 12))


        # Draw Name Plate
        if 'name' in items:
            line_color = (self.color[0] / 2, self.color[1] / 2, self.color[2] / 2)
            pygame.draw.rect(new_image, line_color, (0, self.h/2, self.w, 12*f))
            name = str(self.long_name)

            name_label = name_font.render(name, 1, (255,255,255))
            new_image.blit(name_label,(5*f, self.h/2))
        elif 'small name' in items:
            name = str(self.long_name)
            buffer = 10
            wrap_text_2(new_image, name, buffer, buffer, self.w - buffer, self.h - buffer, fontsize=18)

        # Draw Effect Text
        if 'text' in items and self.special_text:
            buffer = 10
            wrap_text_2(new_image, self.special_text, buffer, self.h / 2 + buffer + 10, self.w - buffer, self.h - buffer)

        # Draw Tags
        self.update_subsprites()
        if 'tags' in items:
            if len(extras) == len(self.subsprites):
                for i, s in enumerate(self.subsprites):
                    new_image.blit(extras[i], (s.x, s.y), area=(1, 1, 1000, 1000))

        # Draw Status Outline
        if self.is_target:
            color = (255, 50, 50)
        elif self.status == 'none':  # Scrubbed Card
            color = (100, 0, 100)
        elif self.status == 'active':
            color = (50, 255, 0)
        elif self.status == 'available':
            color = (0, 200, 255)
        elif self.status == 'button':
            color = (0, 200, 255)
        else:
            color = (self.color[0] / 2, self.color[1] / 2, self.color[2] / 2) # for idle, new, etc
        if self.size == 'big':
            line_w = 10
        else:
            line_w = 7
        pygame.draw.rect(new_image, color, (0, 0, self.w, self.h), line_w)

        return new_image, None

    def update_subsprites(self):
        if len(self.subsprites) != len(self.tags):
            self.subsprites = [Sprite(filename=tag_file_dict[t], host=self, w=40, h=40, name='%s Tag' % t,
                                      fill=False, border=0, colorkey='get corner')
                               for t in self.tags if t in tag_file_dict]
        align(self.subsprites, 0, self.w - 3, skew=1)
        distribute(self.subsprites, 1, low=4, spacing=-10)
        # if self.size != 'big':
        #     for i in self.subsprites:
        #         i.x += 20000

    def move_anywhere(self, target, position=False):
        if self.location:  # Cards start with no location
            # Remove from old location
            if self.space:  # Meaning it's on the board
                self.space.status = 'open'
                self.space = False
            if self in self.location.contents:  # Should always be true but there have been errors
                self.location.contents.remove(self)

        # Place in new location
        # if target == 'Exile':
        #     self.location = False  # Card ceases to have a location, effectively deleted
        #     if hasattr(self, 'Aura'):
        #         self.Aura()
        if target.type == 'space':
            self.space = target
            self.space.status = 'full'
            self.location = target.player.board
            self.location.contents.append(self)
            self.is_hidden = False
        else:
            if position == 'Top':
                target.contents = [self] + target.contents
            elif position == 'Random':
                pos = random.randint(0, len(target.contents))
                target.contents = target.contents[:pos] + [self] + target.contents[pos:]
            else:
                target.contents.append(self)
            self.location = target
            if self.location.type == 'tableau':
                self.is_hidden = False
            else: self.is_hidden = True

    def legal_target(self, target):
        # This method serves as a router to the correct method for determining legal targets
        try:
            if self == target:
                return False
            elif target in self.targets:
                return False
            # elif not target.location and target.name != 'Center Box' and target.name != 'Hero':
            #     return False
            elif not target.location:
                return False
            elif not target.is_card and target.type != 'space':
                return False
            elif self.type == 'Spell':
                if self.n_hand_targets > 0:
                    if target.name == 'Hero' and self.player.hero.is_blocked():
                        return False
                    # Defer to requirements of the Enter ability
                    return self.legal_hand_target(target)
                elif target.name == 'Center Box':
                    return True
            elif self.type in ['Minion', 'Structure'] and self.location.type == 'hand':
                if target.__class__.__name__ == 'Space' and not target.has_adjacent_card():
                    return False
                if hasattr(self, 'legal_hand_target'):
                    # Defer to requirements of the Enter ability
                    return self.legal_hand_target(target)
                elif target.status == 'open' and target.player == self.player:  # Only spaces have the status of 'open'
                    return True
            elif self.name == 'Hero':
                return self.legal_attack(target)
            elif self.location.type == 'board':
                if target.status == 'open' and target.player == self.player and 'Immobile' not in self.special:
                    # Card trying to move
                    # Check for Grapple
                    for c in self.player.opponent.board:
                        if 'Grapple' in c.special and self.within_range(c, 1):
                            return False
                    # return True
                    # Disabled for now
                    return False
                elif target.is_card and self.type == 'Minion' and target.location.type == 'board':
                    # Must be an attempted attack
                    return self.legal_attack(target)

            elif self.location.type == 'tableau' and hasattr(self, 'ability'):
                if target.name == 'Hero' and self.player.hero.is_blocked():
                    return False
                return self.legal_board_target(target)

            return False
        except Exception as e:
            pass
            # print('Exception in LegalTarget: Active Card %s Current Targets %s New Target %s' %
            #       (self.name, str(self.targets), target.__repr__()))
            # raise

    def is_blocked(self):
        if 'Flying' in self.special:
            return False
        column = 0 if self.name == 'Hero' else self.space.column
        for c in self.player.opponent.board.contents:
            if abs(c.space.column - column) == 0: # Only direct blocks
                return True
        return False

    def targets_ready(self, possible_targets):
        if self.location.type == 'hand' and len(self.targets) >= max(self.n_hand_targets, 1):
            return True
        elif self.location.type == 'board' and len(self.targets) >= self.n_board_targets:
            return True
        elif self.location.type == 'tableau' and len(self.targets) >= self.n_board_targets:
            return True
        elif len(self.targets) > 0 and not any([i for i in possible_targets if self.legal_target(i)]):
            return True
        return False

    def legal_attack(self, target):
        if self.attack >= 1:
            # Check Effects on Defender
            if 'Immune' in target.special:
                return False

            # Hero has different attack rules
            if self.name == 'Hero':
                if target.name == 'Hero':
                    if self.is_blocked():
                        return False
                    return True
                elif target.location == self.player.opponent.board:
                    return True

            # Can't attack heroland if directly blocked
            if target == self.player.opponent.hero:
                if self.is_blocked():
                    return False
                return True
            elif target.location == self.player.opponent.board:  # Must be a card
                # Can't attack non-adjacent enemies
                if abs(self.space.column - target.space.column) > 1 and target != target.player.hero:
                    return False
                return True
        return False

    def within_range(self, target, n):
        if abs(self.space.column - target.space.column) <= n:
            return True
        else:
            return False

    def restore(self):
        self.cost = self.starting_cost
        self.attack = self.starting_attack
        self.health = self.starting_health
        self.special = list(self.starting_special)
        self.tags = list(self.starting_tags)

    def conceal(self):
        new = Card()
        new.id = self.id
        new.location = self.location
        return new


def import_card_library():
    # Excel version - found on master server only
    if os.path.isfile('../data/SBCCG_Card_library.xlsx'):
        wb = xlrd.open_workbook('../data/SBCCG_Card_library.xlsx')

        card_dictionary = {}
        raw_card_dictionary = {}

        for s in range(wb.nsheets):
            sheet = wb.sheet_by_index(s)
            data = [[sheet.cell_value(row, col)
                     for col in range(sheet.ncols)]
                    for row in range(sheet.nrows)
                    if sheet.cell_value(row, 3)]
            header_row = [row for row in data if 'Name' in row][0]
            data.remove(header_row)

            if sheet.name == 'Cards':
                n_cards = len(data)
                for c in range(n_cards):
                    new_card = dict(zip(header_row, data[c]))
                    raw_card_dictionary[new_card['Name']] = new_card
                card_dictionary = sanitize_card_library(raw_card_dictionary)

                with open('../data/SBCCG_Card_library.json', "w") as write_file:
                    json.dump(card_dictionary, write_file)
    elif os.path.isfile('../data/SBCCG_Card_library.json'):
        with open('../data/SBCCG_Card_library.json', "r") as read_file:
            card_dictionary = json.load(read_file)
    return card_dictionary


def sanitize_card_library(raw_card_dictionary):
    """ Converts loaded dictionary to actual attributes of card objects"""
    card_dictionary = {}
    for name, data in raw_card_dictionary.items():
        card_dictionary[name] = {
            'name':             data['Name'],
            'long_name':        data['LongName'] if data['LongName'] != '' else data['Name'],
            'effect_class':     data['EffectClass'] if data['EffectClass'] else False,
            'color_name':       data['Class'],
            'color':            Colors[data['Class']] if data['Class'] else (0, 0, 0),
            'type':             data['Type'],
            'cost':             int(data['Cost']) if data['Cost'] != '' else None,
            'starting_cost':    int(data['Cost']) if data['Cost'] != '' else None,
            'attack':           int(data['Attack']) if data['Attack'] != '' else None,
            'starting_attack':  int(data['Attack']) if data['Attack'] != '' else None,
            'health':           int(data['Health']) if data['Health'] != '' else None,
            'starting_health':  int(data['Health']) if data['Health'] != '' else None,
            'max_health': int(data['Health']) if data['Health'] != '' else None,
            'amount':           int(data['Amount']) if data['Amount'] != '' else None,
            'starting_amount':  int(data['Amount']) if data['Amount'] != '' else None,
            'ability_cost':     int(data['AbilityCost']) if data['AbilityCost'] != '' else 0,
            'starting_ability_cost': int(data['AbilityCost']) if data['AbilityCost'] != '' else 0,
            'priority':         float(data['Priority']) if data['Priority'] != '' else 0,
            'handicap':         float(data['Handicap']) if data['Handicap'] != '' else None,
            'special_text':     data['Text'],
            'special':          data['Keywords'].split(' ') if [data['Keywords']] != '' else [],
            'starting_special': data['Keywords'].split(' ') if [data['Keywords']] != '' else [],
            'active_locations': data['ActiveLocations'].split(' ') if [data['ActiveLocations']] != '' else [],
            'tags':             data['Tags'].split(' ') if data['Tags'] != '' else [],
            'starting_tags':    data['Tags'].split(' ') if data['Tags'] != '' else [],
            'n_hand_targets':   int(data['HandTargets']) if data['HandTargets'] != '' else 0,
            'n_board_targets':  int(data['BoardTargets']) if data['BoardTargets'] != '' else 0,
            'set':              int(data['Set']) if data['Set'] else 5,
            'filename':         data['Filename'],
            'include':          True if data['Include'] == 'Yes' else False
        }
    return card_dictionary


# card_dictionary is a mutable global variable
card_dictionary = import_card_library()


def save_card_data(card_dictionary):
    with open('../data/SBCCG_Card_library.json', "w") as write_file:
        json.dump(card_dictionary, write_file)  # Using global card_dictionary


def load_card(short_name, player=False):
    import functools
    import sys

    if short_name in card_dictionary:
        data = card_dictionary[short_name]
    else:
        print('Error loading card %s' % short_name)
        data = card_dictionary['ErrorCard']
        data['text'] = short_name

    try:
        effect_class = data['effect_class']
        subclass = functools.reduce(getattr, effect_class.split("."), sys.modules['card_effects'])
        c = subclass(player)
    except:
        c = Card(player)

    for attr in data:
        c.__dict__[attr] = data[attr]

    return c