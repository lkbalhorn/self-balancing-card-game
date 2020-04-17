# Game object for SBCCG
from card_effects import *
from card import *
from CardStats import SaveData
from pygame.locals import *
# from space import *
from LkGUI import *
import time
from TestRules import test_rules
from player_pc import *
from multiplayer import *
import pygame
import math, random
import settings
from gameboard import *
import asyncio
from aiohttp import web
import _pickle
from extras import *


# Define Game Object
class Game():
    def __init__(self):
        self.Players = []
        self.Decks = []
        self.Hands = []
        self.Boards = []
        self.Spaceboards = []
        self.Discards = []
        self.Heros = []
        self.Exile = []
        self.EmblemBoards = []
        self.player_actions = []
        self.basic_actions = []
        self.interrupts = []
        self.card_actions = []
        self.reactions = []
        self.actions_from_interrupt = []
        self.standard_reactions = standard_reactions
        self.starting_actions = []

        self.id = id(self)
        self.web_players = []

        self.snapshots = []
        self.new_snapshot = False
        self.min_refresh_rate = 30
        self.refresh_counter = 0
        self.active_card = False
        self.active_player = False
        self.active_hover = False
        self.change = 0
        self.delay = 0
        self.hover_delay = 0
        self.turn = 0
        self.turns_remaining = 13
        self.window = False

        self.targets = []

        self.last_card = False
        self.last_snapshot = 0
        self.animations = []  # Persist after snapshot is gone
        self.old_background, self.new_background = ('Huangshan_Valley.jpg', 'Huangshan_Valley.jpg')
        self.snapshots = []
        self.single_player = False

        self.widget_manager = False

        self.csv_written = False

        self.is_running = False

        self.winner = False
        self.loser = False
        
    def cards(self):
        return (
            flat(self.Decks) + 
            flat(self.Discards) + 
            flat(self.Boards) + 
            flat(self.Hands) +
            flat(self.EmblemBoards)
        )

    def view(self):
        return (
            flat(self.Boards) +
            flat(self.Hands) +
            self.widgets() +
            flat(self.Spaceboards) +
            self.Heros +
            flat(self.EmblemBoards)
        )

    def widgets(self):
        return self.widget_manager.contents

    def setup_window(self, window):
        self.window = window
        self.window.carry_on = True

    def setup_game(self):
        print('Setup Game')

        self.clock = pygame.time.Clock()

        self.change = 0
        self.hover_delay = 0
        self.turn = 0
        self.turns_remaining = 13

        self.targets = []

        # self.last_card = 'Start Background'
        self.last_snapshot = 0
        self.old_background, self.new_background = ('Huangshan_Valley.jpg', 'Huangshan_Valley.jpg')
        self.snapshots = []

        # create 2 players
        P1 = Player(1)
        P2 = Player(2)
        P2.opponent = P1
        P1.opponent = P2
        self.Players = [P1, P2]

        # Create objects that hold cards
        for p in self.Players:
            p.Hand = Hand(p)
            self.Hands.append(p.Hand)
            p.Deck = Deck(p)
            self.Decks.append(p.Deck)
            p.Board = Board(p)
            self.Boards.append(p.Board)
            p.Spaceboard = SpaceBoard(p)
            self.Spaceboards.append(p.Spaceboard)
            p.Discard = Deck(p)
            self.Discards.append(p.Discard)
            p.Discard.type = 'Discard'
            p.EmblemBoard = EmblemBoard(p)
            self.EmblemBoards.append(p.EmblemBoard)
            p.EmblemBoard.type = 'EmblemBoard'

        # Create Spaceboard on the board
        nboard = 5
        width = 85
        height = 150
        for p in self.Players:
            for j in range(math.ceil(-nboard / 2), math.ceil(nboard / 2)):
                x = Sprite(w=width, h=height, status='open')
                x.type = 'Space'
                p.Spaceboard.append(x)
                x.Spaceboard = p.Spaceboard
                x.location = x.Spaceboard
                x.Player = p
                x.column = j
                x.alpha = 0

        random.seed()  # Seed random numbers

        # Create Heros
        for p in self.Players:
            p.hero = Hero(p)
            # p.hero = Ellipse(color=(0, 0, 0), w=2000, h=1500, max_w=self.window.xc)
            p.hero.name = 'Hero'
            p.hero.Player = p
            p.hero.location = p.Board
            self.Heros.append(p.hero)

        # Create Widgets
        self.widget_manager = WidgetManager()

        self.is_running = True

        self.take_snapshot()


    def setup_decks(self, decklists):
        print('Setup Decks')
        # This is the portion of setup that only happens at the server
        for i, p in enumerate(self.Players):
            p.decklist = decklists[i]
            p.Deck.name = p.decklist[1]
            for c in p.decklist[6:]:
                x = load_card(c, p, card_dictionary)
                if x:
                    x.location = p.Deck
                    p.Deck.append(x)
            p.Deck.shuffle()

        # Total handicaps
        for p in self.Players:
            p.handicap = 0
            for c in flat(p.Deck, p.Board):
                p.handicap += c.handicap
            p.bonus = []
            p.bonus_mana = 0
            p.bonus_cards = 0
            p.base_handicap = p.handicap

        # Set Constants
        card_value = 20
        second_player_bonus = 30
        random_add = random.random() * 20

        # Determine lower handicap to go first
        player_order = sorted(self.Players, key=lambda p: p.handicap)
        player_order[1].handicap -= second_player_bonus
        low_player = player_order[0]
        high_player = player_order[1]
        low_player.start_text = ['You Go First', '', '']
        high_player.start_text = ['You Go Second', '', '']

        # Determine Starting Hands
        for p in self.Players:
            p.handicap -= random_add  # Adds an average value of 0.5 cards for random rounding
            p.start_cards = 3 + math.floor((150 - p.handicap) / card_value)  # Rounds Down, average of 5 cards
            if p.start_cards < 0:
                p.start_cards = 0
            self.basic_actions.append(DrawCards(p, p, p.start_cards))
            p.start_text[1] = '+' + str(p.start_cards) + ' Cards'
            if len(p.Deck) > 20 + p.start_cards:
                for c in p.Deck[20 + p.start_cards:]:
                    self.basic_actions.append(DiscardFromDeck(p, c))

        # Player with lower handicap goes first,
        self.active_player = low_player.make_active(self.turn)  # Appears to not be drawing a card - work on this

        # Start first turn
        self.active_player.update_mana(self.turn, self.active_player, 'turn start')
        self.basic_actions.append(StartGame(self.active_player, self.active_player))
        for p in self.web_players:
            p.snapshots = []
        self.take_snapshot()
        self.change = 10

    def single_loop(self, inputs, source_id=False):
        # Sanity Checks
        if not self.active_player:
            return False

        # Get inputs
        events, hovered_object_ids, pos = inputs
        sprite_ids = {s.id: s for s in self.view()}
        hovered_objects = [sprite_ids[id] for id in hovered_object_ids if id in sprite_ids]

        # Manage other inputs
        self.check_surrender()

        # Process inputs if they are from the active player
        if source_id == self.active_player.web_player_id or self.single_player:
            self.manage_targets(events, hovered_objects)
            self.check_next_turn(events, hovered_objects)
            # Convert Targets into Player Actions
            player_actions = self.get_player_actions()
            # Resolve actions and return snapshots
            self.resolve_actions(player_actions)  # creates new snapshots

            # Prep snapshots for two players
            if self.refresh_counter >= self.min_refresh_rate:
                self.take_snapshot()
                self.refresh_counter = 0
            elif 4 in inputs[0] or 5 in inputs[0] or 6 in inputs[0]:
                self.take_snapshot()
                self.refresh_counter = 0
            else:
                self.refresh_counter += 1

        # Report Done
        return True


    def manage_targets(self, events, hovered_objects):
        for event in events:
            # Convert type to integer if needed
            if hasattr(event, 'type'):
                event = event.type

            # Check for mouse click and interactions
            if event == pygame.MOUSEBUTTONDOWN:
                for c in hovered_objects:
                    # Only selecting and deselecting an Active Card happens on mouse button down
                    if c.status == 'available' and not self.active_card:
                        # Activate
                        c.status = 'active'
                        self.active_card = c
                        break
                    elif c.status == 'active':
                        # Deactivate
                        c.status = 'available'
                        if self.turn < 1:
                            self.active_player.targets = []
                        else:
                            self.active_card.targets = []
                        self.active_card = False
                    elif c.status == 'available' and not c.is_target and not self.active_card.legal_target(c):
                        # Deactivate the active card
                        self.active_card.status = 'available'
                        self.active_card = False
                        self.active_player.targets = []

            if event == pygame.MOUSEBUTTONUP:
                for c in hovered_objects:
                    # Ignore friendly Hero object if it's not the only object clicked
                    if c == self.active_player.hero and len(hovered_objects) > 1:
                        pass

                    # Choosing Mulligan Targets
                    elif self.turn < 1 and not c.is_target and hasattr(c.location, 'type') and c.location.type == 'Hand':
                        c.is_target = True
                        self.active_player.targets.append(c)

                    # Choosing Targets
                    elif (self.active_card
                          and not c.is_target
                          and self.active_card.legal_target(c)):
                        c.is_target = True
                        self.active_card.targets.append(c)

                    # Deselecting targets
                    elif c.is_target:
                        c.is_target = False
                        if c in self.active_player.targets:
                            self.active_player.targets.remove(c)
                        if self.active_card:
                            if c in self.active_card.targets:
                                self.active_card.targets.remove(c)

    def manage_delays(self, events):
        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.hover_delay = -200
                # self.change = 10  # Refresh screen this loop
            if event.type == pygame.MOUSEBUTTONUP:
                # self.change = 10  # Refresh screen this loop
                pass
            if event.type == VIDEORESIZE:
                self.change = 10

    def check_next_turn(self, events, hovered_objects):
        # Widget Interactions
        for event in events:
            # Convert type to integer if needed
            if hasattr(event, 'type'):
                event = event.type
            if event == pygame.MOUSEBUTTONUP:
                for c in hovered_objects:
                    if c.name == 'Next Turn' and self.turn >= 1:
                        # Start the next turn
                        self.turn += 0.5
                        self.active_player = (self.active_player.opponent.make_active(self.turn))

                        self.basic_actions.append(DrawCards(self.active_player, self.active_player, amount=1))
                        self.active_player.update_mana(self.turn, self.active_player, 'new turn')
                        for b in self.Boards:
                            b.update_status('new turn')
                        self.active_card = False

                        self.turns_remaining = 14 - self.turn

                        # Use message board if near end of game
                        if self.turns_remaining <= 3 and divmod(self.turns_remaining, 1)[1] <= 0.1:
                            self.widget_manager.message_board.alpha = 255
                            self.widget_manager.message_board.fade_timer = 20
                            # self.take_snapshot(delay=60)
                            # self.widget_manager.message_board.alpha = 0

                    elif c.name == 'Next Turn':
                        # Move to the next turn while in mulligan phase
                        for t in self.active_player.targets:
                            t.is_target = False
                        self.active_player.redraw(self.active_player.targets)
                        self.active_player.targets = []
                        self.active_player = (self.active_player.opponent.
                                         make_active(self.turn))
                        self.turn += 0.5
                        self.active_player.update_mana(self.turn, self.active_player, 'new turn')
                        for b in self.Boards:
                            b.update_status('new turn')

    def check_surrender(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_1]:
            self.Players[0].surrender = True
        if keys[pygame.K_2]:
            self.Players[1].surrender = True

    def manage_hover(self, hovered_objects, snapshot):
        snapshot = self.new_snapshot
        view = snapshot.view()
        # Hover Interactions
        if not pygame.mouse.get_pressed()[0]:
            if self.active_hover and self.active_hover.id not in hovered_objects:
                self.active_hover = False
            hover_checks = [c for c in view if c.id in hovered_objects if c.is_card and c.name != 'Hero']
            for s in hover_checks:
                    if s in flat(snapshot.Hands) or s.type == 'Emblem':
                        self.active_hover = s
                    else:
                        # Wait to zoom in on card
                        (x, y) = pygame.mouse.get_rel()
                        if x ^ 2 + y ^ 2 < 1:
                            self.hover_delay += 1
                        elif x ^ 2 + y ^ 2 > 10:
                            self.hover_delay = 0
                        else:
                            self.hover_delay -= 3
                        if self.hover_delay >= 30:
                            self.active_hover = s
                            self.hover_delay = 0

    def get_player_actions(self):
        # Convert Targets into Player Actions
        player_actions = []
        if self.active_card and len(self.active_card.targets) > 0:
            resolved = False
            if self.active_card.location.type == 'Hand' and self.active_card.targets_ready(self.view()):
                # Play Card
                player_actions.append(PlayCard(self.active_player, self.active_card, self.active_player.targets))
                resolved = True

                self.last_card = self.active_card
                self.old_background, self.new_background = (self.new_background, self.active_card.filename)

            elif self.active_card.location.type == 'Board' and self.active_card.targets_ready(self.view()):
                # Move, or...
                if self.active_card.targets[0].type == 'Space':
                    self.active_card.move_anywhere(self.active_card.targets[0])
                    if 'Agility' not in self.active_card.special:
                        self.active_card.status = 'tapped'
                # Attack
                else:
                    player_actions.append(Attack(self.active_player, self.active_card, self.active_player.targets))
                resolved = True
            if resolved:  # Meaning one of the reactions happened
                for c in self.active_card.targets:
                    c.is_target = False
                    self.active_card.targets = []
                self.active_card = False
                self.hover_delay = -10000  # Disables hover immediately after performing an action
                self.active_hover = False

            return player_actions

    def resolve_actions(self, player_actions):

        # Action Resolution Flow:
        # 1. Either Card Actions or Player Actions
        # 2. Check for Interrupts and perform
        # 3. Check for reactions
        # 4. Perform basic actions
        # One pass per loop

        basic_actions, card_actions, actions_from_interrupt, reactions, interrupts = [],[],[],[],[]

        while (player_actions or basic_actions or card_actions or actions_from_interrupt or reactions or interrupts
                or self.basic_actions):

            if actions_from_interrupt:
                basic_actions, actions_from_interrupt = actions_from_interrupt, []
            else:
                if reactions and not card_actions:
                    card_actions = reactions
                    reactions = []

                if card_actions:
                    # Sort, and resolve sequentially in sorted order
                    card_actions.sort(key=lambda c: c.priority)
                    for c in card_actions:
                        new_basic_actions = c.resolve()
                        basic_actions = basic_actions + new_basic_actions
                        card_actions = []

                elif player_actions:
                    # Resolve one player action from queue
                    basic_actions, card_actions = player_actions[0].resolve()
                    player_actions.remove(player_actions[0])

            # Basic actions resolve simultaneously, triggering reactions
            if self.basic_actions:  # Actions from elsewhere
                basic_actions = [i for i in self.basic_actions]
                self.basic_actions = []

            if basic_actions:

                # Check if there are interrupts
                interrupt_cards = [c for c in self.cards() if hasattr(c, 'interrupt')]
                for b in basic_actions:
                    for i in interrupt_cards:
                        new = i.get_interrupt(b)
                        if new:
                            interrupts.append(new)

                # Sort and resolve interrupts immediately (work out animation pauses later)
                interrupts.sort(key=lambda c: c.priority)
                for c in interrupts:
                    if c.source.get_interrupt(c.trigger) and c.trigger in basic_actions:  # Checks that interrupt still applies
                        actions_from_interrupt = c.resolve(basic_actions)  # Many interrupts affect multiple basic actions
                interrupts = []

                reaction_cards = [c for c in self.cards() if hasattr(c, 'reaction')]

                # Record reactions for all basic actions
                for b in basic_actions:
                    for r in reaction_cards:
                        new = r.get_reaction(b)
                        if new:
                            reactions.append(new)
                    for r in self.standard_reactions:
                        new = r.get_reaction(b)
                        if new:
                            reactions.append(new)

                # Resolve all basic actions simultaneously
                for b in basic_actions:
                    try:
                        b.resolve()
                    except AttributeError:
                        print(b.source, b.target)
                        raise
                    except TypeError:
                        print(b.source, b.target)
                        raise
                basic_actions = []
                # self.change = 10

            # Check Deaths
            for b in self.Boards:
                new_card_actions = b.check_death()
                reactions = reactions + new_card_actions

            # Update Auras and Upkeeps
            for c in self.cards():
                if hasattr(c, 'Aura'):
                    c.Aura()
                if hasattr(c, 'Upkeep'):
                    c.Upkeep()

            # Prepare to Export Snapshots

            # Take Snapshot
            self.take_snapshot()

    def take_snapshot(self, delay=0):
        self.widget_manager.update_values(self.turn, self.Players)
        self.routine_updates()
        legal_targets = [i.id for i in self.view() if self.active_card.legal_target(i)] if self.active_card else []
        local_snapshot = Snapshot(self, Player=self.active_player, active_hover=self.active_hover, delay=delay, last_card=self.last_card,
                                  winner=self.winner, loser=self.loser, legal_targets=legal_targets)
        local_snapshot.sign = 1
        local_snapshot.update_highlights(local_snapshot.view(), self.active_player, self.active_card)
        self.snapshots.append(local_snapshot)
        for i, p in enumerate(self.web_players):
            # self.snapshots.append(Snapshot(self, Player=self.active_player, active_hover=self.active_hover))
            new_snapshot = Snapshot(self, Player=self.Players[i], active_hover=self.active_hover,
                                    last_card=self.last_card,
                                    active_player=self.active_player, delay=delay,
                                    winner=self.winner, loser=self.loser, legal_targets=legal_targets)
            new_snapshot.update_highlights(new_snapshot.view(), self.active_player, self.active_card)
            p.snapshots.append(new_snapshot)
        self.last_card = False

    def routine_updates(self):
        # Update Card Statuses
        if self.turn >= 1:
            for p in self.Players:
                p.Hand.update_status()
                p.Board.update_status()
        else:
            for p in self.Players:
                p.Hand.update_status('mulligan')
                p.Board.update_status('mulligan')

        if self.active_card and not self.active_card.Player.is_active:
            self.active_card = False

        # Redundant checks to prevent occasional errors
        for b in self.Spaceboards:
            b.update_status()
        if not self.active_card and self.turn >= 1:
            for c in self.cards():
                c.is_target = False
                c.targets = []
                if c.status == 'active':
                    c.status = 'available'
            self.active_player.targets = []
        if self.active_card:
            for c in self.cards():
                if c == self.active_card:
                    c.status = 'active'
                    break

        # Check victory
        for p in self.Players:
            if p.hero.health <= 0 or p.surrender or (self.turns_remaining <= 0 and p.hero.health < p.opponent.hero.health):
                self.winner = p.opponent
                self.loser = p
                self.winner.result = 'win'
                self.loser.result = 'loss'

                if self.csv_written == 0:
                    self.change = 10
                    SaveData(self.winner, self.loser)
                    self.csv_written = 1

    def play_snapshots(self):
        if self.snapshots and not self.new_snapshot:  # First call
            self.new_snapshot = self.snapshots[0]
            self.snapshots = self.snapshots[1:]
            self.change = 10

        while self.snapshots and self.new_snapshot.delay <= 0:
            self.new_snapshot = self.snapshots[0]
            self.snapshots = self.snapshots[1:]
            self.change = 10
            if self.new_snapshot.last_card:
                self.animations.append(self.new_snapshot.last_card)
                self.new_snapshot.last_card.vanish_timer = 150
        self.new_snapshot.delay -= 1
        self.new_snapshot.active_hover = self.active_hover


    def update_positions(self):
        self.new_snapshot.update_positions(self.window)
        self.window.manage_spring_animations(self.new_snapshot.view() + self.animations, change=self.change + 10)

    def visual_updates(self, window):
        self.manage_animations()
        if self.change >= 1 and self.new_snapshot:

            self.new_snapshot.widget_manager.next_turn.text = self.new_snapshot.next_turn_text
            if self.new_snapshot.result:
                self.new_snapshot.widget_manager.message_board.text = self.new_snapshot.result
            elif self.new_snapshot.widget_manager.message_board.alpha > 0:
                self.new_snapshot.widget_manager.message_board.fade_timer -= 1
                if self.new_snapshot.widget_manager.message_board.fade_timer <= 0:
                    self.new_snapshot.widget_manager.message_board.alpha -= 50



            traits = ['text', 'attack', 'health', 'cost', 'status', 'color', 'is_target', 'size', 'alpha',
                      'over_tint', 'over_alpha']
            self.window.compare_traits(self.new_snapshot.view(), traits)

            items_to_update = [i for i in self.new_snapshot.view() + self.animations
                               if i.update or i.id not in self.window.sprite_images]
            window.redraw_images(items_to_update)

            self.old_background, self.new_background = ('Huangshan_Valley.jpg', 'Huangshan_Valley.jpg')
            window.quick_background(self.old_background, new_background_filename=self.new_background, fade=0)
            window.draw_sprites(self.new_snapshot.view() + self.animations)
            pygame.display.flip()

            self.change -= 1
            self.delay -= 1

    def get_snapshots(self, source):
        self.snapshots = self.snapshots + source.snapshots
        source.snapshots = []

    async def single_player_loop(self, loop, client_game=False):
        if not client_game:
            client_game = self
        client_game.get_snapshots(self)
        client_game.play_snapshots()
        self.single_player = True
        while client_game.window.carry_on:
            # sleep = loop.create_task(asyncio.sleep(1 / settings.GAME_SPEED))
            # await asyncio.sleep(0.00001)  # Triggers previous
            client_game.update_positions()
            inputs = client_game.window.get_inputs(client_game.new_snapshot.view())

            self.single_loop(inputs)
            client_game.get_snapshots(self)

            events, hovered_object_ids, pos = inputs
            client_game.manage_hover(hovered_object_ids, client_game.new_snapshot)
            client_game.window.upkeep(events)
            client_game.manage_delays(events)

            client_game.play_snapshots()
            client_game.update_positions()

            # client_game.window.manage_spring_animations(client_game.new_snapshot.view(), client_game.change)
            client_game.new_snapshot.active_hover = client_game.active_hover
            client_game.visual_updates(client_game.window)
            await asyncio.sleep(1 / settings.GAME_SPEED)

    def manage_animations(self):
        for i in self.animations:
            if i.vanish_timer <= 0:
                self.animations.remove(i)
            else:
                i.vanish_timer -= 1

def main():  # Runs game without using launcher
    # Choose two initial decks semi-randomly
    Decks, window = quick_setup_game()
    for d in deck_dictionary:
        if deck_dictionary[d][1] == 'Test':
            Decks = [d, d]
    play_game(Decks, window)


def quick_setup_game():
    # Choose two initial decks semi-randomly
    Decks = []
    for key in deck_dictionary:
        Decks.append(key)
        if len(Decks) == 2:
            break

    window = Window(1000, 800, 'SBCCG P1 View', 'Huangshan_Valley.jpg')
    return Decks, window


def play_game(Decks, window):
    deck_dictionary = import_decks()
    decklists = [deck_dictionary[id] for id in Decks]
    game = Game()
    game.setup_game()
    game.setup_decks(decklists)

    client_game = Game()  # Imitates the way a remote client plays the game by separating game data
    client_game.setup_window(window)
    # game.setup_window(window)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(game.single_player_loop(loop, client_game))


if __name__ == "__main__":
    main()