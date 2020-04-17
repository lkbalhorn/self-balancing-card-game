import pygame
pygame.init()
import os
import logging
from extras import *
import xlrd

# Mutable Globals (Sometimes changed during operation):
# deck_dictionary is defined in the 'gameboard' module
# card_dictionary is defined in the 'card' module.

# Immutable Globals (Never changed during operation):

# Game Rules
starting_health = 10
starting_lives = 3
half_board_size = 4 # (n_spaces = 2 * half_board_size + 1)
mana_cap = 10**3

# For Handicap
scale = 20 # Handicap per card
second_bonus = 1.5
average_cards = 5


Colors = {'Neutral':(200, 200, 225),
          'Red': (255, 150, 150),
          'Blue': (100, 150, 255),
          'Light Blue': (200,225,255),
          'Green': (160, 255, 160),
          'Purple': (255, 160, 255),
          'White': (230, 230, 230),
          'Grey': (150, 150, 150),
          'Yellow': (255, 255, 160),
          'Black': (150, 150, 150),
          "Wood": (255, 200, 150),
          'Dark_Wood': (205,150,100),
          'Lime': (0, 200, 0),
          'Crimson': (200, 0, 0),
          'Dark Blue': (50, 50, 100),
          'Outline': (100, 0, 75),

          'Thief': (150, 150, 150),
          'Ranger': (160, 255, 160),
          'Scholar': (255, 160, 255),
          'Mage': (100, 150, 255),
          'Fighter': (255, 255, 160),
          'Prince': (230, 230, 230),
          'Villain': (255, 150, 150),


          'Fire': (200, 100, 0),

          'Mana': (150,150,255),
          'Handicap': (150, 150, 150)
          }

def import_card_library_old():
    import csv
    card_dictionary = {}
    with open('../csv/SBCCG_Card_library.csv', newline='') as csvfile:
        table = csv.reader(csvfile, dialect = 'excel')
        for i, row in enumerate(table):
            if i == 0:
                keys = [i for i in row]
                continue
            new_card = dict(zip(keys, row))
            card_dictionary[new_card['Name']] = new_card

    return card_dictionary



# Import Tags
path = '../media/tags'
filenames = os.listdir(path)
tag_file_dict = {}
for f in filenames:
    label = f.split(' ')[0].capitalize()
    tag_file_dict[label] = f

f = 1.25
CardFonts = {
    'cost': pygame.font.SysFont("times", int(20 * f), bold=True),
    'cost inner': pygame.font.SysFont("times", int(20 * f), bold=False),
    'attack': pygame.font.SysFont("times", int(20 * f)),
    'health': pygame.font.SysFont("times", int(20 * f)),
    'handicap': pygame.font.SysFont('times', int(12 * f)),
    'name': pygame.font.SysFont('arial narrow', int(16 * f)),
    'special': pygame.font.SysFont('Rockwell Extra Bold', int(16 * f))
}

f = 1.8
BigFonts = {
    'cost': pygame.font.SysFont("times", int(20 * f), bold=True),
    'cost inner': pygame.font.SysFont("times", int(20 * f), bold=False),
    'attack': pygame.font.SysFont("times", int(20 * f)),
    'health': pygame.font.SysFont("times", int(20 * f)),
    'handicap': pygame.font.SysFont('times', int(12 * f)),
    'name': pygame.font.SysFont('arial narrow', int(16 * f)),
    'special': pygame.font.SysFont('Times New Roman', int(25 * f))
}


def chamfer(x, y, side, cut_h, x_dir, y_dir):
    # Returns a set of points that make a chamfered corner
    # x_dir, y_dir should be given as 1 or -1
    points = [
        (x,y),
        (x + side*x_dir, y),
        (x + side * x_dir, y + cut_h * y_dir),
        (x + cut_h * x_dir, y + side * y_dir),
        (x, y + side*y_dir)
        ]
    return points


def setup_custom_logger(name, filename=False):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    if filename:
        handler = logging.FileHandler(filename)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

# stream_logger = setup_custom_logger(__name__)
# logger = setup_custom_logger(__name__, filename='_event_log')
gameplay_logger = setup_custom_logger(__name__, filename='_gameplay_log')



# Draw Card Templates
def draw_card_templates():
    # Board Template
    w, h = 90, 150
    f = 1.25
    board_template = pygame.Surface([w, h])
    board_template.fill((0, 0, 0))
    board_template.set_colorkey((0, 0, 0))
    # Attack Box
    pygame.draw.polygon(board_template, (200, 100, 100), chamfer(0, h, f * 24, f * 16, 1, -1))
    pygame.draw.polygon(board_template, (100, 50, 50), chamfer(0, h, f * 24, f * 16, 1, -1), 2)
    # Health Box
    pygame.draw.polygon(board_template, (100, 150, 100), chamfer(w, h, f * 24, f * 16, -1, -1))
    pygame.draw.polygon(board_template, (50, 75, 50), chamfer(w, h, f * 24, f * 16, -1, -1), 2)

    # Hand Template
    w, h = 90, 150
    f = 1.25
    hand_template = pygame.Surface([w, h])
    hand_template.fill((0, 0, 0))
    hand_template.set_colorkey((0, 0, 0))
    # Cost Box
    pygame.draw.polygon(hand_template, Colors['Mana'], chamfer(0, 0, f * 24, f * 16, 1, 1))
    pygame.draw.polygon(hand_template, (75, 75, 125), chamfer(0, 0, f * 24, f * 16, 1, 1), 2)
    # Attack Box
    pygame.draw.polygon(hand_template, (200, 100, 100), chamfer(0, h, f * 24, f * 16, 1, -1))
    pygame.draw.polygon(hand_template, (100, 50, 50), chamfer(0, h, f * 24, f * 16, 1, -1), 2)
    # Health Box
    pygame.draw.polygon(hand_template, (100, 150, 100), chamfer(w, h, f * 24, f * 16, -1, -1))
    pygame.draw.polygon(hand_template, (50, 75, 50), chamfer(w, h, f * 24, f * 16, -1, -1), 2)

    # Hand Spell
    w, h = 90, 150
    f = 1.25
    hand_spell = pygame.Surface([w, h])
    hand_spell.fill((0, 0, 0))
    hand_spell.set_colorkey((0, 0, 0))
    # Cost Box
    pygame.draw.polygon(hand_spell, (150, 150, 255), chamfer(0, 0, f * 24, f * 16, 1, 1))
    pygame.draw.polygon(hand_spell, (75, 75, 125), chamfer(0, 0, f * 24, f * 16, 1, 1), 2)

    # Big Minion Template
    w, h = 190, 260
    f = 1.8
    big_template = pygame.Surface([w, h])
    big_template.fill((0, 0, 0))
    big_template.set_colorkey((0, 0, 0))
    # Cost Box
    pygame.draw.polygon(big_template, (150, 150, 255), chamfer(0, 0, f * 24, f * 16, 1, 1))
    pygame.draw.polygon(big_template, (75, 75, 125), chamfer(0, 0, f * 24, f * 16, 1, 1), 2)
    # Attack Box
    pygame.draw.polygon(big_template, (200, 100, 100), chamfer(0, h, f * 24, f * 16, 1, -1))
    pygame.draw.polygon(big_template, (100, 50, 50), chamfer(0, h, f * 24, f * 16, 1, -1), 2)
    # Health Box
    pygame.draw.polygon(big_template, (100, 150, 100), chamfer(w, h, f * 24, f * 16, -1, -1))
    pygame.draw.polygon(big_template, (50, 75, 50), chamfer(w, h, f * 24, f * 16, -1, -1), 2)
    # Handicap Box
    pygame.draw.polygon(big_template, (50, 50, 100), [(35, 25), (35, 35),
                                                   (40, 40), (50, 40),
                                                   (55, 35), (55, 25),
                                                   (50, 20), (40, 20)])
    pygame.draw.polygon(big_template, (25, 25, 50), [(35, 25), (35, 35),
                                                  (40, 40), (50, 40),
                                                  (55, 35), (55, 25),
                                                  (50, 20), (40, 20)], 2)

    # Big Structure Template
    w, h = 190, 260
    f = 1.8
    big_structure_template = pygame.Surface([w, h])
    big_structure_template.fill((0, 0, 0))
    big_structure_template.set_colorkey((0, 0, 0))
    # Cost Box
    pygame.draw.polygon(big_structure_template, (150, 150, 255), chamfer(0, 0, f * 24, f * 16, 1, 1))
    pygame.draw.polygon(big_structure_template, (75, 75, 125), chamfer(0, 0, f * 24, f * 16, 1, 1), 2)
    # Health Box
    pygame.draw.polygon(big_structure_template, (100, 150, 100), chamfer(w, h, f * 24, f * 16, -1, -1))
    pygame.draw.polygon(big_structure_template, (50, 75, 50), chamfer(w, h, f * 24, f * 16, -1, -1), 2)
    # Handicap Box
    pygame.draw.polygon(big_structure_template, (50, 50, 100), [(35, 25), (35, 35),
                                                   (40, 40), (50, 40),
                                                   (55, 35), (55, 25),
                                                   (50, 20), (40, 20)])
    pygame.draw.polygon(big_structure_template, (25, 25, 50), [(35, 25), (35, 35),
                                                  (40, 40), (50, 40),
                                                  (55, 35), (55, 25),
                                                  (50, 20), (40, 20)], 2)

    # Big Spell
    w, h = 190, 260
    f = 1.8
    big_spell = pygame.Surface([w, h])
    big_spell.fill((0, 0, 0))
    big_spell.set_colorkey((0, 0, 0))
    # Cost Box
    pygame.draw.polygon(big_spell, (150, 150, 255), chamfer(0, 0, f * 24, f * 16, 1, 1))
    pygame.draw.polygon(big_spell, (75, 75, 125), chamfer(0, 0, f * 24, f * 16, 1, 1), 2)
    # Handicap Box
    pygame.draw.polygon(big_spell, (50, 50, 100), [(35, 25), (35, 35),
                                                   (40, 40), (50, 40),
                                                   (55, 35), (55, 25),
                                                   (50, 20), (40, 20)])
    pygame.draw.polygon(big_spell, (25, 25, 50), [(35, 25), (35, 35),
                                                  (40, 40), (50, 40),
                                                  (55, 35), (55, 25),
                                                  (50, 20), (40, 20)], 2)

    return {
            'hand': hand_template,
            'board': board_template,
            'big': big_template,
            'big structure': big_structure_template,
            'big spell': big_spell,
            'hand spell': hand_spell}
CardTemplates = draw_card_templates()


class LoopCounter:
    def __init__(self):
        self.count = 0

    def __call__(self, value):
        if self.count >= value:
            self.count = 0
            return True
        else:
            self.count += 1
            return False
