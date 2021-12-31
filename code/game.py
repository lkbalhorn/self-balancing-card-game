from card_effects import *
from card import *
from game_menus import *
from globals import *
from gameboard import *
import math
import json
import functools
import sys
from card import card_manager


class GameRouter:
    """Creates an API for the game that should be general for all turn-based games."""
    def __init__(self, get_options, check_option, choose_option):
        # Attributes stored by this function
        self.players = []  # List of ID strings
        self.history = []
        self.trial_moves = []  # Dict of lists, where keys are player ID strings
        # how to do simultaneous actions, like drafting?

        self.get_options = get_options  # Function
        self.check_option = check_option
        self.choose_option = choose_option


# Create server object for both online and local play
class Game:
    def __init__(self):
        self.players = []

        self.game_actions = []
        self.player_actions = []
        self.basic_actions = []
        self.conditional_actions = []
        self.reactions = []
        self.next_layer = []
        self.primary_action = None
        self.last_card_played = None
        self.rule_cards = rule_cards

        self.id = id(self)
        self.web_players = []
        self.players_by_id = {}
        self.is_local = False
        self.local_window = None
        self.inbox = []
        self.outbox = []

        self.active_card = None
        self.active_player = None

        self.hover_delay = 0
        self.turn = 0
        self.turns_remaining = 13
        self.result = False

        self.last_player_action = None
        gameplay_logger.info('New Game Created')

    def encode(self, hide_from_player=False):
        # Prepares Game object and downstream objects for JSON serializaiton.
        simple_dict = {
            'player_ids': [p.id for p in self.players],
            'active_player_id': self.active_player.id,
            'turns_remaining': self.turns_remaining,
            'result': self.result,
            'player_data': [p.encode(hide_from_player=hide_from_player) for p in self.players]
        }
        return simple_dict

    def decode(self, simple_dict):
        for attr in ['player_ids', 'active_player_id', 'turns_remaining', 'result']:
            self.__dict__[attr] = simple_dict[attr]
        self.players = [Player().decode(dataset) for dataset in simple_dict['player_data']]

        for p in self.players:
            if p is Player:  # not None or False
                for l in p.locations:
                    l.player = p
                    for c in l.contents:
                        c.location = l
                        c.player = p

    def cards(self):
        return [card
                for p in self.players
                for l in p.locations
                for card in l
                if card.is_card]

    def cards_in_play(self):
        return [c for c in self.cards() if c.location.type in c.active_locations] + self.rule_cards

    def setup_game(self, player_ids=False):
        random.seed()

        for i in range(2):
            self.players.append(Player())
            if player_ids:
                self.players[i].id = player_ids[i]  # ID matches ID of webplayer
        self.players_by_id = {p.id: p for p in self.players}
        for i in range(2):
            self.players[i-1].opponent = self.players[i]

        # Create objects that hold cards
        for p in self.players:
            for name in p.location_names:
                new = Location(name, p)
                p.__dict__[name] = new
                p.locations.append(new)
            p.hero = Hero(p)

        for p in self.players:
            for j in range(-half_board_size, half_board_size + 1):
                space = Space(status='open', player=p, location=p.spaceboard, column=j, alpha=0, type='space',
                               check_highlight=False, w=90, h=90)
                p.spaceboard.append(space)
                space.location = p.spaceboard
        gameplay_logger.info('Game Setup Complete')

    def deal_cards(self, decks):
        # Refresh card list
        card_manager.get_changes()

        # Set up game objects
        for i, p in enumerate(self.players):
            # p.deck = decks[i]
            new_deck = decks[i]
            card_names = new_deck.card_names if hasattr(new_deck, 'card_names') else new_deck
            for name in card_names:
                new = card_manager.load_card(name, p)
                p.deck.append(new)
                new.location = p.deck
            p.deck.player = p
            p.locations.append(p.deck)
            p.deck.shuffle()

        bonus = random.random()  # 0 to 1

        for p in self.players:
            p.handicap = sum([i.handicap for i in p.deck])
        self.players.sort(key=lambda x: x.handicap)
        self.players[0].start_cards = math.floor(average_cards + bonus +
                                                 (150 - self.players[0].handicap) / scale)
        self.players[1].start_cards = math.floor(average_cards + bonus + second_bonus +
                                                 (150 - self.players[1].handicap) / scale)

        for p in self.players:
            print(p.handicap)
            print(p.start_cards)
            if p.start_cards < 0:
                p.negative_cards = p.start_cards
            elif p.start_cards > 9:
                self.game_actions.append(DrawCards(p, p, 9))
            else:
                self.game_actions.append(DrawCards(p, p, p.start_cards))

        self.active_player = self.players[0]  # Will switch before first turn
        self.game_actions.extend(
            NextTurn(self.active_player.opponent, self.active_player, turn=self.turn).safe_resolve())
        self.game_actions.extend([StartGame(self.players[0], self.players[1])])
        self.active_player = self.active_player.opponent

        self.take_snapshot()
        self.resolve_actions([])
        self.take_snapshot()

    def single_loop(self, player_actions):
        object_dict = self.get_object_dict()
        decoded_actions = [Action().decode(i, object_dict) for i in player_actions]
        self.resolve_actions(decoded_actions)

    def resolve_actions(self, player_actions):
        basic_actions, reactions, next_layer = [], [], []
        self.primary_action = None

        # Take Snapshot
        self.take_snapshot()

        while player_actions or self.game_actions or reactions or next_layer:

            # Determine Primary Action
            if self.game_actions:
                self.primary_action = None
                basic_actions = [i for i in self.game_actions]
                self.game_actions = []
            elif player_actions:
                self.primary_action = player_actions[0]
                player_actions = player_actions[1:]
            elif reactions:
                self.primary_action = reactions[0]
                reactions = reactions[1:]
            elif next_layer:
                self.primary_action = None
                reactions = [i for i in next_layer]
                next_layer = []

            # Perform Primary Action
            if self.primary_action:
                basic_actions = self.primary_action.safe_resolve()

            # Full Process for Resolving Basic Actions
            basic_actions = self.resolve_interrupts(basic_actions)
            basic_actions = self.resolve_coactions(basic_actions)
            conditional_actions = [i for i in basic_actions if i.type == 'ConditionalAction']
            basic_actions = [i for i in basic_actions if i.type != 'ConditionalAction']
            next_layer.extend(self.get_reactions(basic_actions))
            self.resolve_basic_actions(basic_actions)
            basic_actions = []
            self.resolve_conditional_actions(conditional_actions)

            # Update Auras
            for c in self.cards_in_play():
                if hasattr(c, 'aura'):
                    c.aura()

            # Take Snapshot
            self.take_snapshot()

    def resolve_basic_actions(self, basic_actions):
        # Resolve Basic Actions
        for b in basic_actions:
            b.safe_resolve()

            # Check for special flags
            if b.__class__.__name__ == 'EndTurn':
                self.active_player = self.active_player.opponent
                self.turn += 0.5

    def get_reactions(self, basic_actions):
        next_layer = []
        reaction_cards = [c for c in self.cards_in_play() if hasattr(c, 'reaction')]
        for b in basic_actions:
            for r in reaction_cards:
                new = r.get_reaction(b)
                if new:
                    next_layer.append(new)
        return next_layer

    def resolve_conditional_actions(self, conditional_actions):
        next_layer = []
        while conditional_actions:
            current_action = conditional_actions[0]
            conditional_actions = conditional_actions[1:]
            basic_actions = current_action.safe_resolve()

            # Full Process for Resolving Basic Actions, minus nested conditional actions
            basic_actions = self.resolve_interrupts(basic_actions)
            basic_actions = self.resolve_coactions(basic_actions)
            next_layer.extend(self.get_reactions(basic_actions))
            self.resolve_basic_actions(basic_actions)
        return next_layer

    def resolve_coactions(self, basic_actions):
        for b in basic_actions:
            if b.type == 'CoAction':  # Included in list of basic actions though it's actually a co-action.  Change?
                if not b.is_resolved:
                    new_basic_actions = b.safe_resolve()
                    new_basic_actions = self.resolve_interrupts(new_basic_actions)
                    basic_actions.extend(new_basic_actions)
                    b.is_resolved = True
            if len(basic_actions) > 1000:
                raise Exception('CoAction Limit Reached')
        return basic_actions

    def resolve_interrupts(self, basic_actions):
        modified_basic_actions = []

        # Check for interrupts
        for _ in range(1000):
            interrupt_cards = [c for c in self.cards_in_play() if hasattr(c, 'interrupt')]
            interrupt_cards.sort(key=lambda x: x.priority)
            interrupts = []
            for i in interrupt_cards:
                for b in basic_actions:
                    if i.id not in b.past_interrupts:
                        new = i.get_interrupt(b)
                        if new:
                            interrupts.append(new)
                            b.past_interrupts.append(i.id)
                if interrupts:
                    for j in interrupts:
                        modified_basic_actions.extend(j.safe_resolve())
                    basic_actions = [i for i in modified_basic_actions]
                    modified_basic_actions = []
                    break
            else:
                return basic_actions
        raise Exception('Interrupt Limit Reached')

    def take_snapshot(self):
        self.update_status()
        for p in self.players:
            p.snapshots.append(Snapshot(self, player=p).encode())

    def update_status(self):
        for p in self.players:
            if p.is_active:
                for c in p.hand:
                    if c.cost <= p.mana:
                        c.status = 'available'
                    else:
                        c.status = 'idle'
                for c in p.board + [p.hero]:
                    if c.is_new and 'Charge' not in c.special:
                        c.status = 'idle'
                    elif c.is_tapped:
                        c.status = 'idle'
                    elif c.attack and c.attack > 0:
                        c.status = 'available'
                for c in p.tableau:
                    if hasattr(c, 'ability') and c.player.mana >= c.ability_cost and not c.is_tapped:
                        c.status = 'available'
                    else:
                        c.status = 'idle'
            else:
                for c in (p.hand + (p.board + p.tableau) + [p.hero]):
                    c.status = 'idle'

    def get_object_dict(self):
        new_dict = {}
        for p in self.players:
            for l in p.locations:
                for sprite in l:
                    if sprite is None:
                        print(l)
                        raise
                    new_dict[sprite.id] = sprite
                new_dict[l.id] = l
            new_dict[p.id] = p
            new_dict[p.hero.id] = p.hero
        return new_dict


class Snapshot:
    def __init__(self, game=None, player=False, primary_action=False, basic_actions=[]):
        self.id = id(self)
        self.game = game
        self.player = player
        self.primary_action = primary_action
        self.basic_actions = basic_actions

        self.turn = 0
        self.active_player = False
        self.players = False
        self.objects = {}
        self.start_time = 0
        self.finish_time = 0
        self.delay = 0.5
        self.key_traits = ['player', 'turn', 'active_player', 'players', 'delay']

        if game:
            self.players = game.players
            self.active_player = game.active_player
            self.turn = game.turn
            self.primary_action = game.primary_action
            self.basic_actions = game.basic_actions

            # Get all game objects by ID number
            self.objects = game.get_object_dict()

            # Redact Hidden Cards
            for i, obj in self.objects.items():
                if obj.is_card and obj.is_hidden and obj.player != self.player and obj.location.type == 'hand':
                    self.objects[i] = obj.conceal()

        # Since snapshots are now encoded immediately, creating a deep copy is no longer necessary.

    def encode(self):
        simple_dict = {}
        for attr in self.key_traits:
            value = self.__dict__[attr]
            if hasattr(value, 'id'):
                simple_dict[attr] = 'ID' + value.id
            elif type(value) is list:
                simple_dict[attr] = [('ID' + i.id) for i in self.__dict__[attr]]
            else:
                simple_dict[attr] = value

        simple_dict['objects'] = {}
        for ID, s in self.objects.items():
            new = {}
            new['id'] = s.id
            new['class_name'] = s.__class__.__name__
            for attr in s.key_traits:
                value = s.__dict__[attr]
                if hasattr(value, 'id'):
                    new[attr] = 'ID' + value.id
                elif type(value) is list:
                    try:
                        new[attr] = [('ID' + i.id) for i in value]
                    except AttributeError:
                        new[attr] = [i for i in value]
                else:
                    new[attr] = value
            simple_dict['objects'][s.id] = new
        simple_dict['primary_action'] = self.primary_action.encode() if self.primary_action else None
        simple_dict['basic_actions'] = [i.encode() for i in self.basic_actions]

        return simple_dict

    def decode(self, simple_dict, object_dict):
        # Create objects not present in client
        for ID, s in simple_dict['objects'].items():
            if ID not in object_dict:  # Object is present on server but not in client
                # Create object locally with correct ID
                class_name = s['class_name']
                subclass = functools.reduce(getattr, class_name.split("."), sys.modules[__name__])
                print(subclass)
                new = subclass()
                new.id = ID
                object_dict[ID] = new  # temporarily holds object for reference. Object still needs location.

        # Update snapshot attributes
        for attr in self.key_traits:
            value = simple_dict[attr]
            if type(value) is str and value[:2] == 'ID':
                self.__dict__[attr] = object_dict[value[2:]]  # If not in dict, something else is wrong
            elif type(value) is list:
                self.__dict__[attr] =[object_dict[id[2:]] for id in value]  # Must be list of game objects
            else:
                self.__dict__[attr] = value

        # Update attributes of object list, including replacing ID markers with the objects they refer to
        for ID in simple_dict['objects']:
            data = simple_dict['objects'][ID]
            target = object_dict[ID]

            for attr in target.key_traits:
                try:
                    value = data[attr]
                    if type(value) is str and str(value[:2]) == 'ID':
                        target.__dict__[attr] = object_dict[value[2:]]  # Replace ID reference with object
                    elif type(value) is list:
                        if not value:
                            target.__dict__[attr] = []
                        elif type(value[0]) is str and (value[0][:2]) == 'ID':
                            target.__dict__[attr] = [object_dict[id[2:]] for id in value]  # Must be list of game objects
                        else:
                            target.__dict__[attr] = [i for i in value]
                    else:
                        target.__dict__[attr] = value
                except KeyError:
                    print('KeyError for target %s attribute %s' % (target.__repr__(), attr))
        self.primary_action = Action().decode(simple_dict['primary_action'], object_dict=object_dict)
        # self.summarize()
        return self

    def __repr__(self):
        name = '\n Snapshot Contents:\n'
        for p in self.players:
            name += (p.__repr__() + '\n')
            for l in p.locations:
                name += ('    ' + l.__repr__() + '\n')
                for s in l.contents:
                    name += ('        ' + s.__repr__() + '\n')
        return name

    def summarize(self, *args):
        name = '\n Snapshot Contents:\n'
        for p in self.players:
            name += (p.__repr__() + '%s\n' % str({key: value for key, value in p.__dict__.items()
                                                  if key in args and key in p.__dict__}))
            for l in p.locations:
                name += ('    ' + l.__repr__() + '%s\n' % str({key: value for key, value in l.__dict__.items()
                                                               if key in args and key in l.__dict__}))
                for s in l.contents:
                    name += ('        ' + s.__repr__() + '%s\n' % str({key: value for key, value in s.__dict__.items()
                                                                       if key in args and key in s.__dict__}))
        print(name) # Part of Summarize routine, doesn't need to be deleted