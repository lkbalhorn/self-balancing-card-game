from menus import *
from gameboard import *
from game import *
import time
import json
# from globals import *


class WebPlayer(Sprite):
    def __init__(self, address, screen_name, client_id):
        super().__init__()
        self.address = address
        self.screen_name = screen_name
        self.client_id = client_id
        self.text = screen_name
        self.id = str(id(self))
        self.color = Colors['Red']
        self.w = 300
        self.h = 50
        self.connected = True
        self.active_search = False
        self.challenges_given = []
        self.challenges_received = []
        self.requested_status = 'online'
        self.actual_status = 'online'
        self.game_id = False
        self.decklist = []
        self.snapshots = []

    def __repr__(self):
        return 'WebPlayer(%s, %s)' % (self.address, self.screen_name)


class GameScreen(Page):
    def __init__(self, name, host, parent, background, groups=[], local_game=False):
        super().__init__(name, host, parent, background, groups=[])
        self.player_actions = []
        self.active_player = False
        self.hover_timer = 0
        self.snapshots = []
        self.current_snapshot = None
        self.turn = False
        self.local_game = local_game
        self.local_player = None
        self.legal_targets = []

        self.active_card = False

        self.last_action = None
        self.last_action_card = None

        # Animation Variables
        self.pos_rel_mouse = {}  # Indexed by id number
        self.skew_rel_mouse = {}

        self.w = self.host.window.w  # Probably temporary
        self.h = self.host.window.h

        # def __init__(self, name, page, sprites, align_dim, align_ref, align_pos, align_skew,
        #              dist_dim, dist_ref, low=0, center=0, high=0, spacing=0, fixed_size=False, couple=False):
        self.boards = [Group('lower_board', self, [], 1, 0.5, 25, 0, 0, 0.5, center=0, spacing=10, couple='space'),
                            Group('upper_board', self, [], 1, 0.5, -25, 1, 0, 0.5, center=0, spacing=10, couple='space')]
        self.spaceboards = [Group('lower_spaceboard', self, [], 1, 0.5, 25, 0, 0, 0.5, center=0, spacing=10),
                            Group('upper_spaceboard', self, [], 1, 0.5, -25, 1, 0, 0.5, center=0, spacing=10)]
        self.hands = [Group('lower_hand', self, [], 1, 1, -10, 1, 0, 0.5, high=-100, spacing=-10),
                      Group('upper_hand', self, [], 1, 0, 10, 0, 0, 0.5, high=-100, spacing=-10)]
        self.hero_boards = [Group('lower_hero', self, [], 1, 0.5, 260, 0.5, 0, 0.5, low=-75, spacing=20),
                            Group('upper_hero', self, [], 1, 0.5, -260, 0.5, 0, 0.5, low=-75, spacing=20)]
        self.tableaus = [Group('lower_tableau', self, [], 1, 0.5, 210, 0.5, 0, 0.5, low=140, spacing=10),
                         Group('upper_tableau', self, [], 1, 0.5, -210, 0.5, 0, 0.5, low=140, spacing=10)]
        self.players = []

        self.last_action_display = Group('last_action_display', self, [], 0, 0, 30, 0, 1, 0.5, low=-120, spacing=10)

        # Create icons adjacent to heros
        self.mana_widgets = [Sprite(color=Colors['Light Blue'], w=60, h=60, fontsize=60),
                             Sprite(color=Colors['Light Blue'], w=60, h=60, fontsize=60)]
        self.stock_widgets = [Sprite(color=Colors['Red'], w=60, h=60, fontsize=60),
                             Sprite(color=Colors['Red'], w=60, h=60, fontsize=60)]
        self.filler_widgets = [Sprite(color=Colors['Dark_Wood'], w=60, h=60, fontsize=60),
                             Sprite(color=Colors['Dark_Wood'], w=60, h=60, fontsize=60)]
        self.hero_extras = [Group('lower_hero_extras', self, [self.mana_widgets[0], self.filler_widgets[0],
                                                              self.stock_widgets[0]],
                                  0, 0.5, 100, 0.5, 1, 0.5, low=160, spacing=10),
                            Group('upper_hero_extras', self, [self.mana_widgets[1], self.filler_widgets[1],
                                                              self.stock_widgets[1]],
                                  0, 0.5, 100, 0.5, 1, 0.5, low=-160 - 200, spacing=10)]

        # Create Draw and Discard Icons
        self.draw_icons = [Sprite(color=(0, 0, 0), w=70, h=95, fontsize=80, border=5, border_color=Colors['Outline'],
                                  layer=-1, text='4*', font_color=(200, 200, 200)),
                           Sprite(color=(0, 0, 0), w=70, h=95, fontsize=60, border=5, border_color=Colors['Outline'],
                                  layer=-1, text='4*', font_color=(200, 200, 200))]
        self.discard_icons = [Sprite(color=Colors['Fire'], w=70, h=95, fontsize=60, border=5, border_color=Colors['Outline']),
                           Sprite(color=Colors['Fire'], w=70, h=95, fontsize=60, border=5, border_color=Colors['Outline'])]
        # self.hero_column_2 = [Group('lower_hero_2', self, [self.draw_icons[0], self.discard_icons[0]],
        #                             0, 0.5, 170, 0.5, 1, 0.5, low=160, spacing=10),
        #                       Group('upper_hero_2', self, [self.draw_icons[1], self.discard_icons[1]],
        #                             0, 0.5, 170, 0.5, 1, 0.5, low=-160 - 200, spacing=10),]

        # Create right side menu
        back_button = Sprite(color=Colors['Wood'], w=150, h=75, x=20, y=20, text='Return', name='Back', type='Back',
                             filename='light_wood.jpg', fontsize=80, alignment='right')
        game_screen_right = Group('game_screen_right', self, [back_button], 1, 1, -25, 1, 0, 1, high=-25, spacing=10)

        # Stack Right-Side Widgets
        self.next_turn = Sprite(color=Colors['Wood'], w=80, h=80, fontsize=30, font='times', name='Next Turn')
        self.right_column = Group('right_column', self, [], 0, 1, -100, 0.5, 1, 0.5, center=0, spacing=10)
        self.right_column.sprites = [self.next_turn]

        # Create Center hit Box
        low_table = Sprite(name='low_table', w=self.w, h=int(self.h / 2 - 150), border=5, over_fill=False,
                            check_highlight=False, filename='light_wood.jpg', layer=-5)
        high_table = Sprite(name='high_table', w=self.w, h=int(self.h / 2 - 150), border=5, over_fill=False,
                            check_highlight=False, filename='light_wood.jpg', layer=-5)
        center_box = Sprite(name='Center Box', w=600, h=300, border=20, over_fill=False, alpha=0,
                            check_highlight=False, location='Center Box', type='space')
        self.center_box = Group('table', self, [high_table, center_box, low_table], 0, 0.5, 0, 0.5, 1, 0.5, center=0, spacing=0)

        # Create Center Message Board
        self.main_message = Sprite(w=500, h=200, fill=False, border=False, color=(150, 150, 200), fontsize=100,
                                    font_color=(50, 50, 150))
        self.victory_message = Sprite(w=800, h=400, fill=False, border=False, color=(150, 200, 150), fontsize=300,
                                    font_color=(50, 150, 50), text='Victory!', layer=10)
        self.defeat_message = Sprite(w=800, h=400, fill=False, border=False, color=(200, 150, 150), fontsize=300,
                                    font_color=(150, 50, 50), text='Defeat!', layer=10)
        self.messages = Group('messages', self, [], 0, 0.5, 0, 0.5, 1, 0.5, center=0, spacing=300)


        # Create left side widgets

        self.left_background = Sprite(color=Colors['Wood'], w=100, h=500, border=5)

        self.hourglass_symbol = Sprite(w=80, h=80, filename='hourglass_7.png')
        self.deck_symbols = [Sprite(w=50, h=50, filename='papers-outlines-stack_318-45527.jpg'),
                             Sprite(w=50, h=50, filename='papers-outlines-stack_318-45527.jpg')]
        self.discard_symbols = [Sprite(w=50, h=50, filename='delete-hand-drawn-cross-symbol-outline_318-52032.jpg'),
                                Sprite(w=50, h=50, filename='delete-hand-drawn-cross-symbol-outline_318-52032.jpg')]
        self.handicap_symbols = [Sprite(w=50, h=50, filename='coins 4.jpg'),
                                Sprite(w=50, h=50, filename='coins 4.jpg')]
        self.hourglass = Sprite()
        self.decks = [Sprite(), Sprite()]
        self.discards = [Sprite(), Sprite()]
        self.handicaps = [Sprite(), Sprite()]

        self.left_symbols = [self.handicap_symbols[1], self.discard_symbols[1], self.deck_symbols[1], self.hourglass_symbol,
                             self.deck_symbols[0], self.discard_symbols[0], self.handicap_symbols[0]]
        self.left_values = [self.handicaps[1], self.discards[1], self.decks[1], self.hourglass, self.decks[0], self.discards[0], self.handicaps[0]]

        for s in self.left_symbols:
            s.colorkey = (255, 255, 255)
            s.color = (255, 255, 255)
            s.border_color = (255, 255, 255)
        for s in self.left_values:
            s.w = 50
            s.h = 50
            s.fontsize = 30
            s.color = (255, 255, 255)
            s.border_color = (255, 255, 255)
            s.colorkey = (255, 255, 255)
        self.hourglass.h = 80
        self.hourglass.fontsize = 40
        self.hourglass.w = 80

        self.deck_icons = [Location('DeckIcon'), Location('DeckIcon')]
        self.discard_icons = [Location('Discard'), Location('Discard')]

        # Create Non-Stationary Objects
        self.crosshair = Sprite(w=20, h=20, color=(100, 200, 100), name='crosshair')
        self.skew_rel_mouse[self.crosshair.id] = (-0.5, -0.5)
        Group('misc', self, [self.crosshair], 0, -100, 0, 0, 1, 0.5, center=-100, spacing=0)

    def process_inputs(self, events, hovered_ids, pos, mouse):
        hovered_sprites = [i for i in self.view() if i.id in hovered_ids]
        self.host.navigate(events, hovered_ids)
        self.button_click_animation(events, hovered_ids, pos, mouse)
        self.process_text_boxes(events, hovered_sprites)
        self.host.special_inputs(events, hovered_ids, pos, mouse)
        self.manage_drag(events, hovered_sprites, pos, mouse)
        self.manage_hover(events, hovered_sprites, pos, mouse)
        if self.local_game or self.local_player == self.active_player:
            self.manage_targets(events, hovered_sprites)  # Can alter highlight
            self.get_player_actions()
            self.check_next_turn(events, hovered_sprites)

    def manage_hover(self, events, hovered_sprites, pos, mouse):
        hovered_cards = [i for i in hovered_sprites if i.is_card]
        event_types = [i.type for i in events]
        current_time = time.time()

        if event_types:  # Any mouse actions
            self.hover_timer = 0

        for i in hovered_cards:
            if i.name == 'Hero':
                continue
            if i.location:
                if i.location.type == 'board' or i.location.type == 'tableau':
                    if self.hover_timer == 0:
                        self.hover_timer = current_time
                        continue
                    elif current_time - self.hover_timer < 0.5:
                        continue

                if i.size == 'small' or i.size == 'emblem':
                    i.size = 'big'
                    i.resize()
                    for j in self.view():
                        if j != i and j.is_card:
                            j.size = 'small' if (not j.location or j.location.type != 'tableau') else 'emblem'
                            j.resize()
                    self.hover_timer = 0

        if self.active_card or not hovered_cards:
            for i in self.view():
                if i.is_card:
                    i.size = 'small' if (not i.location or i.location.type != 'tableau') else 'emblem'
                    i.resize()
            self.hover_timer = 0

        if mouse[1]:  # Left button
            self.hover_timer = 0

        for i in self.view():
            if i.is_card:
                i.layer = 3 if i.size == 'big' else 2
                if i.name == 'Hero':
                    i.layer = 1

    def manage_drag(self, events, hovered_sprites, pos, mouse):
        crosshair = False
        for i in self.view():
            i.drag_with_mouse = False
            i.lock_to_object = False
            if i.status == 'active':
                if i.type == 'Minion':
                    if len(self.active_card.targets) == 0:
                        i.drag_with_mouse = True
                    else:
                        i.lock_to_object = self.active_card.targets[0]
                        crosshair = True
                elif i.type == 'Spell':
                    if i.n_hand_targets == 0:
                        i.drag_with_mouse = True
                    else:
                        crosshair = True
        self.crosshair.drag_with_mouse = True if crosshair else False

        event_types = [i.type for i in events]
        if 5 in event_types:  # Click
            for i in hovered_sprites:
                self.pos_rel_mouse[i.id] = (i.x - pos[0], i.y - pos[1])
                self.skew_rel_mouse[i.id] = ((i.x - pos[0]) / i.w, (i.y - pos[1]) / i.h)

    def manage_connection(self, loop):
        # Passing of inputs and snapshots, both for local and online games.
        object_dict = self.get_object_dict()
        if self.local_game:
            # This is modeled to use as much of the same code as possible as online games for debug purposes,
            # Even including steps that are not necessary.

            # "Send" and "Receive" Player Actions
            # Received actions are encoded
            data = [i.encode() for i in self.player_actions]  # To match online game
            data = json.loads(json.dumps(data))
            self.player_actions = []
            # Perform Gameplay
            self.local_game.single_loop(data)  # Single Loop takes encoded actions

            # "Send" and "Receive" Snapshots
            # Snapshots are encoded immediately after being produced
            self.snapshots = self.snapshots + [
                Snapshot().decode(i, object_dict) for i in self.local_game.active_player.snapshots]
            for p in self.local_game.players:
                p.snapshots = []
        else:
            # Send player actions
            self.host.client.outbox.extend([i.encode() for i in self.player_actions])
            self.player_actions = []
            # Get snapshots
            if self.host.client.inbox:
                self.snapshots = self.snapshots + [
                    Snapshot().decode(i, object_dict) for i in self.host.client.inbox]
                self.host.client.inbox = []

    def exit(self, destination):
        # Disconnect from server
        self.host.client.active = False
        self.host.client.connected = False

    def play_snapshots(self, loop):
        if self.snapshots and not self.current_snapshot:  # First call
            self.current_snapshot = self.snapshots[0]
            self.snapshots = self.snapshots[1:]
            self.current_snapshot.finish_time = time.time() + self.current_snapshot.delay

        while self.snapshots:  # Need to add delay stuff - figure out later since it wasn't working before
            if time.time() > self.current_snapshot.finish_time:
                self.current_snapshot = self.snapshots[0]
                self.snapshots = self.snapshots[1:]
                # self.current_snapshot.finish_time = time.time() + self.current_snapshot.delay
                # Last action
                self.last_action = self.current_snapshot.primary_action
                if self.last_action:
                    if self.last_action.active_card:
                        if self.last_action.active_card.name == 'Hero':
                            self.last_action_card = Card()
                            # self.last_action_card.name = 'Hero'
                        else:
                            self.last_action_card = load_card(self.last_action.active_card.name)
                        self.last_action_card.size = 'big'
                        self.last_action_card.status = 'display'
                        self.last_action_card.is_card = False  # To keep it big.  A bit crude but let's see if it works
                        self.last_action_card.layer = 100
                        self.last_action_card.resize()
                        self.last_action_display.sprites = [self.last_action_card]
                        self.last_action_card.is_static = True

        if self.current_snapshot:
            self.turn = self.current_snapshot.turn
            self.active_player = self.current_snapshot.active_player

            # For remote games, you always play the bottom side of the screen
            if not self.local_game:
                if self.current_snapshot.players[0] != self.local_player:
                    self.current_snapshot.players = self.current_snapshot.players[::-1]

            for p in range(2):
                self.hands[p].sprites = [i for i in self.current_snapshot.players[p].hand]
                self.boards[p].sprites = [i for i in self.current_snapshot.players[p].board]
                self.tableaus[p].sprites = [i for i in self.current_snapshot.players[p].tableau]
                self.spaceboards[p].sprites = [i for i in self.current_snapshot.players[p].spaceboard]
                self.hero_boards[p].sprites = [self.current_snapshot.players[p].hero]

            self.next_turn.text = 'End Turn'
            for i, p in enumerate(self.current_snapshot.players):
                self.mana_widgets[i].text = '%d/%d' % (p.mana, p.income)
                self.stock_widgets[i].text = '%d' % p.hero.stock
                # self.filler_widgets[i].text = '%d' % len(p.hand)

            # Special visuals for non-local games
            if not self.local_game:
                self.local_player = self.current_snapshot.player
                if self.local_player == self.active_player:
                    self.next_turn.text = 'End Turn'
                else:
                    self.next_turn.text = "Opponent's Turn"

            # Update Message Board
            if self.current_snapshot.players[0].result is not None:
                if self.current_snapshot.players[0].result == 1:
                    self.messages.sprites = [self.defeat_message, self.victory_message]
                else:
                    self.messages.sprites = [self.victory_message, self.defeat_message]
                if not self.local_game:
                    # Only show message for Player 1
                    self.messages.sprites = self.messages.sprites[:1]

    def manage_targets(self, events, hovered_sprites):
        hovered_sprites.sort(key=lambda x: x.layer, reverse=True)
        for i in self.legal_targets:
            i.highlight = False
        if self.active_card:
            self.legal_targets = [i for i in self.view() if self.active_card.legal_target(i)]

            for i in self.legal_targets:
                i.over_alpha = 80
                i.over_fill = True
                i.highlight = True
                i.over_tint = shade(i.color, shade_fraction=0.25)

        # Check Deactivate
        if self.active_card:
            hovered_legal_targets = [i for i in self.legal_targets if i in hovered_sprites]
            event_types = [i.type for i in events]
            if 5 in event_types :  # Click
                if not hovered_legal_targets:
                    # Deactivate
                    self.active_card.status = 'available'
                    self.purge_targets()
                    gameplay_logger.info('%s Deactivated' % self.active_card.__repr__())
                    self.active_card = False
                    return

        for event in events:
            if event.type == 5:  # Click
                # Check activate or target
                for c in hovered_sprites:
                    if c.status == 'available' and not self.active_card:
                        # Activate
                        c.status = 'active'
                        self.active_card = c
                        gameplay_logger.info('%s Activated' % self.active_card.__repr__())
                        break
                    elif c.status == 'active' and False:
                        # Deactivate
                        c.status = 'available'
                        if self.turn < 1:
                            self.active_player.targets = []
                        else:
                            self.active_card.targets = []
                        gameplay_logger.info('%s Deactivated' % self.active_card.__repr__())
                        self.active_card = False
                    # elif c.status == 'available' and not c.is_target and not self.active_card.legal_target(c):
                    #     # Deactivate the active card
                    #     self.active_card.status = 'available'
                    #     self.active_card = False
                    #     self.active_player.targets = []


            if event.type == 6:  # Unclick
                for c in hovered_sprites:
                    # Ignore friendly Hero object if it's not the only object clicked
                    # if self.active_player and self.active_player.hero and c == self.active_player.hero and len(hovered_sprites) > 1:
                    #     pass

                    # Choosing Mulligan Targets
                    if self.turn < 1 and not c.is_target and hasattr(c.location, 'type') and c.location.type == 'Hand':
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

    def get_player_actions(self):
        # Convert Targets into Player Actions
        if self.active_card and self.active_card.targets_ready(self.view()):
            if self.active_card.location.type == 'hand':
                # Play Card
                self.player_actions.append(PlayCard(self.active_player, self.active_card, active_card=self.active_card))
            elif self.active_card.location.type == 'board':
                # Move, or...
                if self.active_card.targets and self.active_card.targets[0].type == 'space':
                    pass
                    # self.player_actions.append(Move(self.active_player, self.active_card, self.active_player.targets))
                # Attack
                else:
                    self.player_actions.append(Attack(active_card=self.active_card))
            elif self.active_card.location.type == 'tableau':
                self.player_actions.append(UseAbility(active_card=self.active_card))
            # Clear Targets
            self.purge_targets()
            self.active_card.status = 'tapped'
            self.active_card = False


    def purge_targets(self):
        for c in self.active_card.targets:
            c.is_target = False
        self.active_card.targets = []

    def check_next_turn(self, events, hovered_sprites):
        for event in events:
            if event.type == 6:  # Unclick
                if [c for c in hovered_sprites if c.name == 'Next Turn']:
                    if self.local_game:
                        self.player_actions.append(NextTurn(source=self.active_player, turn=self.turn))
                    elif self.local_player == self.active_player:
                        self.player_actions.append(NextTurn(source=self.active_player, turn=self.turn))
                        self.active_player = None

    def update_positions(self, window):

        for g in self.groups:
            if g.name in ['lower_hand', 'upper_hand']:
                # Resize hand to fit
                g.spacing = 0
                g.low = 10 - window.w / 2
                g.high = -120
            if g.name in ['lower_tableau', 'upper_tableau']:
                for s in g.sprites:
                    if s.size != 'big':
                        s.size = 'emblem'
                    s.resize()

            g.align(window)

            # Apply Animations
            for i in g.sprites:
                # Drag Animation
                if i.drag_with_mouse:
                    i.x_target = window.last_pos[0] + self.skew_rel_mouse[i.id][0] * i.w
                    i.y_target = window.last_pos[1] + self.skew_rel_mouse[i.id][1] * i.h
                # Lock to Object
                if i.lock_to_object:
                    i.x_target = i.lock_to_object.x
                    i.y_target = i.lock_to_object.y

                # Spring Animation
                # if not i.is_static:
                i.x, i.y = i.x_target, i.y_target

    def get_object_dict(self):
        new_dict = {}
        if self.current_snapshot:
            for p in self.current_snapshot.players:
                for l in p.locations:
                    for sprite in l:
                        new_dict[sprite.id] = sprite
                    new_dict[l.id] = l
                new_dict[p.id] = p
                new_dict[p.hero.id] = p.hero
        return new_dict


