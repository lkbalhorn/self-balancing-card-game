import pygame, random
from card_effects import *
import time
from globals import *
from sprite import *
import csv
import json
from card import card_manager


class Player(Sprite):
    # This class represents the two players playing this game
    def __init__(self):
        super().__init__()

        self.deck = None
        self.hand = None
        self.board = None
        self.discard = None
        self.spaceboard = None
        self.tableau = None
        self.exile = None
        self.hero = False
        self.location_names = ['hand', 'board', 'spaceboard', 'discard', 'tableau', 'deck', 'exile']
        self.locations = []
        for name in self.location_names:
            self.__dict__[name] = Location(type=name, player=self)
        self.key_traits = self.location_names + ['mana', 'income', 'targets', 'handicap',
                                                 'start_cards', 'negative_cards',
                                                 'opponent', 'is_active', 'result', 'surrender', 'result',
                                                 'locations', 'hero']

        self.mana = 0
        self.income = 0
        # self.health = starting_health
        # self.stock = starting_lives
        self.targets = []
        self.handicap = 0
        self.start_cards = 0
        self.negative_cards = 0

        self.opponent = None
        self.is_active = False
        self.result = None # win loss or None
        self.surrender = False

        self.snapshots = []
        self.deck_size = 0
        self.discard_size = 0

        self.web_player_id = id(self)
        self.screen_name = ''
        self.host = "127.0.0.1"
        self.port = 5000

    def encode(self, hide_from_player=False):
        # Prepares Player object and downstream objects for JSON serialization.
        self.locations = [self.__getattribute__(name) for name in self.location_names]
        simple_dict = {
            'mana': self.mana,
            'income': self.income,
            'health': self.health,
            'locations': [l.encode() for l in self.locations],
            'hero': self.hero.encode()
        }
        return simple_dict

    def decode(self, simple_dict):
        for attr in ['mana', 'income', 'health']:
            self.__dict__[attr] = simple_dict[attr]
        self.locations = [Location().decode(dataset) for dataset in simple_dict['locations']]
        self.hero = Hero().decode(simple_dict['hero'])
        return self

    def cards(self):
        return [c
                for i in self.locations
                for c in i.contents
                if c.is_card
                ]

    def cards_in_play(self):
        return [c for c in self.cards() if c.location.type in c.active_locations]

    def __repr__(self):
        return 'P' + str(self.id)[-4:]


class Location(Sprite):
    def __init__(self, type=False, player=False):
        super().__init__()
        self.type = type
        self.player = player
        self.contents = []
        self.w = 80
        self.h = 80
        self.card_names = []
        self.key_traits = ['type', 'player', 'contents', 'card_names']

    def cards(self):
        return [i for i in self.contents if i.is_card]

    def spaces(self):
        return [i for i in self.contents if i.type == 'space']

    def encode(self, hide_from_player=False):
        # Prepares Location object and downstream objects for JSON serialization.
        simple_dict = {
            'type': self.type,
            'sprites': [c.encode(hide_from_player=hide_from_player) for c in self.contents],
            'player_id': self.player.id if self.player else False
        }
        return simple_dict

    def decode(self, simple_dict):
        for attr in ['type']:
            self.__dict__[attr] = simple_dict[attr]
        if self.type == 'spaceboard':
            self.contents = [Space().decode(dataset) for dataset in simple_dict['sprites']]
        else:
            self.contents = [Card().decode(dataset) for dataset in simple_dict['sprites']]
        return self

    def __len__(self):
        return len(self.contents)

    def __bool__(self):
        return True

    def __getitem__(self, position):
        return self.contents[position]

    def __repr__(self):
        return '%s(%s)' % (self.type, self.player)

    def __add__(self, other):
        if hasattr(other, 'contents'):
            return self.contents + other.contents
        else:
            return self.contents + other

    def append(self, item):
        if item.__class__ == 'list':
            self.contents = self.contents + item
        else:
            self.contents.append(item)

    def remove(self, item):
        self.contents.remove(item)

    def shuffle(self):
        random.shuffle(self.contents)


class Space(Sprite):
    def __init__(self, **kwargs):
        super().__init__()
        self.player = None
        self.column = 0
        self.check_highlight = False
        self.location = None
        self.key_traits = ['location', 'type', 'column', 'status', 'player', 'alpha', 'check_highlight']

        for k in kwargs:
            self.__dict__[k] = kwargs[k]

    def has_adjacent_card(self):
        if -1 <= self.column <= 1:
            return True
        for s in self.location.contents + self.location.player.opponent.spaceboard.contents:
            if s.status == 'full':
                if abs(s.column - self.column) <= 1:
                    return True
        return False

    def __repr__(self):
        return '%s %s(%s, %d)' % (self.status, self.__class__.__name__, self.player, self.column)

    def encode(self, hide_from_player=False):
        # Prepares Location object and downstream objects for JSON serialization.
        simple_dict = {
            'type': self.type,
            'column': self.column,
            'status': self.status,
            'player_id': self.player.id if self.player else False,
            'location_id': self.location.id if self.location else False
        }
        return simple_dict

    def decode(self, simple_dict):
        for attr in ['type', 'column', 'status']:
            self.__dict__[attr] = simple_dict[attr]
        return self


class Deck(Location):
    # This is a deck for icons and record keeping, not in-game use.  Consider re-naming.
    def __init__(self, player=False, data=False):
        super().__init__('deck', player=player)
        self.contents = []
        self.player = player
        self.name = 'Empty Deck'
        self.text = 'Empty Deck'

        self.id = id(self)  # Used for saving deck data.  Will be same as id unless overwritten.
        self.wins = 0
        self.losses = 0
        self.n_games = 0
        self.strength = 50
        self.last_access = time.time()
        self.template_filename = 'deck_icon_background.png'
        self.card_names = []
        self.extra_card_names = []

        self.average_mana = 0
        self.total_handicap = 0
        self.n_start_cards = 0
        self.n_deck_cards = 0
        self.show_card_count = False
        self.image_traits.extend(['average_mana', 'n_start_cards', 'n_deck_cards', 'show_card_count'])

        self.attack = 0
        self.health = 10
        self.armor = 0
        self.mana = 0

        self.saved_attributes = ['id', 'name', 'wins', 'losses', 'strength', 'last_access', 'card_names', 'extra_card_names',
                             'attack', 'health', 'armor', 'mana']

        self.h = 75
        self.w = 200
        self.fontsize = 80
        self.font_color = (200, 200, 255)

        if data:
            if data is list:
                pass
                # self.id = data[0]
                # self.name = data[1]
                # self.text = data[1]
                # self.wins = data[2]
                # self.losses = data[3]
                # self.strength = data[4]
                # self.last_access = data[5]
                # self.card_names = data[6:]
            else:
                for name in self.saved_attributes:
                    if name in data:
                        self.__setattr__(name, data[name])
                self.text = self.name
                self.card_names = [i for i in self.card_names if i is not None]
        self.n_games = self.wins + self.losses

    def update_text(self):
        star_cards = [c for c in self.contents if 'Star' in c.special]
        deck_cards = [c for c in self.contents if 'Star' not in c.special]

        self.n_deck_cards = sum([c.quantity for c in deck_cards])
        if self.n_deck_cards > 0:
            self.average_mana = sum(c.cost * c.quantity for c in deck_cards) / self.n_deck_cards
        else:
            self.average_mana = 0
        self.total_handicap = sum(c.handicap * c.quantity for c in self.contents)
        self.n_start_cards = 5 - (self.total_handicap - 150) / 20


    def draw_image(self, artwork=False, template=False, extras=[]):
        # Update Text
        self.update_text()

        # Create image surface
        new_image = pygame.Surface([self.w, self.h])

        # Fill Box
        if self.color:
            new_image.fill(self.color)
        if self.alpha < 255:
            new_image.set_alpha(self.alpha)

        # Add template
        if template:
            scaled_art = pygame.transform.scale(template, (self.w, self.h))
            new_image.blit(scaled_art, (0, 0))

        # Add Artwork
        if artwork:
            scaled_art = pygame.transform.scale(artwork, (self.w, self.h))
            if self.colorkey:
                scaled_art.set_colorkey(self.colorkey)
            new_image.blit(scaled_art, (0, 0))

        # Draw Text - Name
        buffer = 0
        self.name = self.text
        wrap_text_2(new_image, self.name, buffer, buffer, self.w - buffer, self.h / 2 - buffer,
                    alignment=self.alignment, fontsize=self.fontsize, font_color=self.font_color)

        # Draw Text - Average Mana
        wrap_text_2(new_image, '%.1f' % self.average_mana, 10 + buffer, 0.65 * self.h + buffer, self.w - buffer, self.h - buffer,
                    alignment='left', fontsize=30, font_color=Colors['Dark Blue'])

        # Draw Text - Start Cards
        wrap_text_2(new_image, '%.1f' % self.n_start_cards, 10 + self.w/3 + buffer, 0.65 * self.h + buffer, self.w - buffer, self.h - buffer,
                    alignment='left', fontsize=30, font_color=Colors['Dark Blue'])

        # Draw Text - Card Count
        if self.show_card_count:
            wrap_text_2(new_image, '%d/30' % self.n_deck_cards, 10 + 2 * self.w / 3 + buffer, 0.65 * self.h + buffer,
                        self.w - buffer, self.h - buffer,
                        alignment='right', fontsize=30, font_color=Colors['Light Blue'])

        return new_image, template

    def save(self, delete=False):
        deck_dictionary = import_decks()
        if delete:
            if self.id in deck_dictionary:
                del deck_dictionary[self.id]
        else:
            data = self.to_dict()
            deck_dictionary[self.id] = data
        with open('../data/Decklist.txt', 'w') as outfile:
            json.dump(deck_dictionary, outfile)

    def to_dict(self):
        return {attr: self.__getattribute__(attr) for attr in self.saved_attributes}


class SpaceBoard(Location):
    def __init__(self, player):
        super().__init__(player)
        self.type = 'Spaceboard'

    def random_open_space(self):
        empty_spaces = [i for i in self.contents if i.status == 'open']
        if empty_spaces:
            random.shuffle(empty_spaces)
            return empty_spaces[0]
        else:
            return False

    def update_status(self):
        # This is here as redundancy to prevent occasional errors.
        full_spaces = [c.space for c in self.player.Board]
        for s in self.contents:
            s.status = 'full' if s in full_spaces else 'open'


class Hero(Card):
    def __init__(self, player=False):
        super().__init__(player=player)
        self.color = (50, 50, 50)
        if player:
            self.filename = ('knight_by_eksrey_d9vvynu.jpg' if int(self.player.id) % 2 == 1 else
                             'human_ranger_by_rhineville_d2qtoat.jpg')
        self.center_x = 10
        self.center_y = 10
        self.rx = 10
        self.ry = 10
        self.w = 0
        self.h = 0
        self.attack = 0
        self.health = starting_health
        self.stock = starting_lives
        self.max_health = starting_health
        # self.text = str(self.health)
        self.name = 'Hero'
        self.size = 'small'
        self.player = player
        if player:
            self.location = player.board
        self.resize()

        self.key_traits.append('stock')

    # def draw_image(self, artwork=False, template=False):
        # self.text = str(self.health)
    #     return Sprite.draw_image(self, artwork, template)

    # def resize(self):
    #     self.w, self.h = 150, 210


class DeckList:
    def __init__(self):
        self.id = None
        self.name = 'New Deck'
        self.cards = {}  # Dict of str: int

        self.last_accessed = time.time()
        self.last_modified = time.time()
        self.wins = 0
        self.losses = 0

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items()}

    def from_dict(self, data):
        for key in self.__dict__:
            try:
                setattr(self, key, data[key])
            except KeyError:
                # Keep default value
                pass

    def add_card(self, name):
        if name in self.cards:
            self.cards[name] += 1
        else:
            self.cards[name] = 1

    def remove_card(self, name):
        if name in self.cards:
            if self.cards[name] > 1:
                self.cards[name] -= 1
            else:
                self.cards.pop(name, 0)


class DeckManager:
    def __init__(self, _path):
        self.path = _path
        self.decks = {'default': DeckList()}
        self.main_deck = 'default'
        self.second_deck = 'default'

    def to_dict(self):
        """Converts data to json-serializable format"""
        new = {}
        for key, value in self.__dict__.values():
            if key in ['path', 'decks']:
                continue
            else:
                new[key] = value
        new['decks'] = {name: deck.to_dict() for name, deck in self.decks.items()}
        return new

    def from_dict(self, data):
        """Loads data from json-serializable format"""
        for key, value in data.items():
            if key in ['path', 'decks']:
                continue
            else:
                self.__setattr__(key, value)
        self.decks = {name: DeckList().from_dict(data) for name, data in data['decks'].items()}

    def load(self):
        try:
            with open(self.path, 'r') as infile:
                raw_data = json.load(infile)
            self.from_file(raw_data)
            return self
        except OSError:
            # File doesn't exist - keep defaults
            return self

    def save(self):
        with open(self.path, 'w') as outfile:
            json.dump(self.to_dict(), outfile)

    def select_deck(self, deck_id):
        self.second_deck = self.main_deck
        self.main_deck = deck_id

    def new_deck(self):
        new = DeckList()
        for i in range(1000):
            if str(i) not in self.decks:
                new.id = str(i)
                self.decks[new.id] = new
                self.select_deck(new.id)
                return True
        return False

    def delete_deck(self, deck_id):
        self.decks.pop(deck_id)
        self.save()

    # To edit a deck, use methods of the DeckList itself and save DeckManager when complete.


def import_decks():
    with open('../data/Decklist.txt') as infile:
        global deck_dictionary
        deck_dictionary = json.load(infile)
        for key, deck in deck_dictionary.items():
            deck['id'] = str(deck['id'])
            deck['last_access'] = int(deck['last_access'])
            deck['card_names'] = [c for c in deck['card_names'] if c in card_manager.data]
            deck['wins'] = int(deck['wins'])
            deck['losses'] = int(deck['losses'])
            wins, losses = int(deck['wins']), int(deck['losses'])
            deck['n_games'] = wins + losses
            deck['strength'] = (10 + wins - losses) / (20 + wins + losses)

        while len(deck_dictionary) < 2:
            key, deck = Deck().to_dict()
            deck_dictionary[key] = deck

    with open('../data/Decklist.txt') as infile:
        deck_dictionary = json.load(infile)

    return deck_dictionary


deck_dictionary = import_decks()


def get_recent_decks():
    while len(deck_dictionary) < 2:
        new = Deck()
        deck_dictionary[new.id] = new
    deck_times = [(id, deck_dictionary[id]['last_access']) for id in deck_dictionary]
    recent_deck_tuples = sorted(deck_times, key=lambda x: x[1], reverse=True)
    recent_ids = [d[0] for d in recent_deck_tuples]
    recent_decks = [Deck(data=deck_dictionary[d]) for d in recent_ids]
    return recent_decks


def export_decks(deck_dictionary):
    with open('../data/SBCCG_Deck_List.csv', newline='', mode='w') as csvfile:
        writer = csv.writer(csvfile, delimeter=',')
        for key in deck_dictionary:
            writer.writerow([key] + deck_dictionary[key])


def flat(*args):
    # Returns contents of nested lists.
    items = []
    for a in args:
        if hasattr(a, '__len__'):
            for b in a:
                items = items + flat(b)  # Careful of infinite loops
        else:
            items.append(a)
    return items


if __name__ == '__main__':
    test = DeckList()
    test_2 = json.dumps(test.to_dict())
    print(test_2)
    test_3 = DeckList(data=json.loads(test_2))
    print('Done')



