from menus import *
from globals import *
from game import *
from game_screen import *
from card import card_manager
from gameboard import DeckManager


class MainMenu(Menu):
    def __init__(self, window):
        super().__init__(window)
        title_filename = 'main title 4.jpg'
        background_filename = 'Island in a Bottle TEMP cropped.jpg'
        game_background_filename = 'Huangshan_Valley.jpg'
        self.dm = DeckManager('deck_data.txt')
        self.deck_chooser = DeckChooser('Deck Chooser', self, 'main', background_filename)
        self.game_screen = GameScreen('Game Screen', self, 'main', game_background_filename)
        self.deck_builder = DeckBuilder('Deck Builder', self, 'main', background_filename)
        self.game_lobby = GameLobby('Play',                 self, 'main', background_filename)

        main = Page('main',                 self, 'main', title_filename)
        practice = Page('Practice',         self, 'main', background_filename)

        self.set_page('main')

        main_right = Group('main_right', main, [], 0, 1, -25, 1, 1, 1, high=-25, spacing=10)
        practice_right = Group('practice_right', practice, [], 0, 1, -25, 1, 1, 1, high=-25, spacing=10)

        for i, name in enumerate(['Play', 'Practice', 'Deck Builder', 'Stats', 'Exit']):
            new = Sprite(color=Colors['Wood'], w=100+i*75, h=75, text=name, name=name, type='link', dest=name,
                         filename='light_wood.jpg', fontsize=80, alignment='right')
            main_right.sprites.append(new)

        for i, name in enumerate(['Choose Player 1 Deck', 'Choose Player 2 Deck', 'Start Game', 'Back']):
            new = Sprite(color=Colors['Wood'], w=480-80*i, h=75, text=name, name=name, type='choice', dest='Deck Chooser',
                         filename='light_wood.jpg', fontsize=80, alignment='right')
            practice_right.sprites.append(new)

        # Add Back Button
        back_button = Sprite(color=Colors['Wood'], w=80, h=50, x=20, y=20, text='Back', name='Back', type='Back',
                             filename='light_wood.jpg', fontsize=80, alignment='right')
        for p in self.pages:
            if p in ['Game Screen', 'Play']:
                Group('back_button', self.pages[p], [back_button], 1, 0, 30, 0, 0, 1, low=-100, spacing=10)

    def special_inputs(self, events, hovered_ids, pos, mouse):
        hovered_items = [i for i in self.current_page.view() if i.id in hovered_ids]
        for e in events:
            if e.type == pygame.MOUSEBUTTONUP:  # Unclick
                for h in hovered_items:
                    if h.name in ['Choose Player 1 Deck', 'deck_choice']:
                        self.set_page(self.deck_chooser.name, come_back=True)
                        self.deck_chooser.active_position = 0  # First deck being chosen
                    elif h.name in ['Choose Player 2 Deck']:
                        self.set_page(self.deck_chooser.name, come_back=True)
                        self.deck_chooser.active_position = 1  # First deck being chosen
                    elif h.name == 'Start Game':
                        game = Game()
                        game.setup_game()
                        game.deal_cards(self.dm.chosen_decks)
                        game.is_local = True
                        self.set_page(self.game_screen.name, come_back=True)
                        self.game_screen.local_game = game
                    elif h.name == 'Exit':
                        self.window.carry_on = False


        # Update Sprite Text for Choices
        for h in self.current_page.view():
            if h.name in ['Choose Player 1 Deck', 'deck_choice']:
                h.text = self.dm.chosen_decks[0].name
            elif h.name in ['Choose Player 2 Deck']:
                h.text = self.dm.chosen_decks[1].name


class DeckChooser(Page):
    def __init__(self, name, host, parent, background, groups=[]):
        super().__init__(name, host, parent, background, groups=[])
        self.active_position = 0
        self.mode = 'recent'
        self.all_decks = []

        self.strong_label = Sprite(name='Strong', text='Strong', w=200, h=80, color=Colors['Wood'],
                              filename='light_wood.jpg', fontsize=80)
        self.recent_label = Sprite(name='Recent', text='Recent', w=200, h=80, color=Colors['Wood'],
                              filename='light_wood.jpg', fontsize=80, status='active')
        self.favorites_label = Sprite(name='Favorites', text='Favorites', w=200, h=80, color=Colors['Wood'],
                              filename='light_wood.jpg', fontsize=80)
        self.tab_headings = Group('tag_headings', self, [self.strong_label, self.recent_label, self.favorites_label],
                                1, 0, 50, 0, 0, 0, low=50, spacing=10)
        back_button = Sprite(color=Colors['Wood'], w=150, h=75, x=20, y=20, text='Return', name='Back', type='Back',
                             filename='light_wood.jpg', fontsize=80, alignment='right')
        deck_chooser_right = Group('deck_chooser_right', self, [back_button], 1, 1, -25, 1, 0, 1, high=-25, spacing=10)

        self.update_decks()

        # Create up to 5 rows for deck icons, to be referenced by index
        for row in range(6):
            new = Group('deck_row', self, [], 1, 0, 150*row + 200, 0, 0, 0, low=50, spacing=10)

    def enter(self, source):
        self.parent = source
        self.update_decks()

    def update_decks(self):
        self.all_decks = [Deck(data=value) for key, value in self.host.dm.decks.items()]

    def special_inputs(self, events, hovered_ids, pos, mouse):
        hovered_sprites = [i for i in self.view() if i.id in hovered_ids]

        for e in events:
            if e.type == pygame.MOUSEBUTTONUP:  # Unclick
                for h in hovered_sprites:
                    if h in self.tab_headings.sprites:
                        # Toggle active page
                        for i in self.tab_headings.sprites:
                            i.status = False
                        h.status = 'active'
                    elif h.type == 'deck':
                        self.host.dm.select_deck(h.deck_list_id, position=self.active_position)
                        self.host.set_page(self.parent)

    def update_positions(self, window):
        if self.strong_label.status == 'active':
            self.all_decks.sort(key=lambda x: x.strength, reverse=True)
        elif self.recent_label.status == 'active':
            self.all_decks.sort(key=lambda x: x.last_access, reverse=True)
        elif self.favorites_label.status == 'active':
            self.all_decks.sort(key=lambda x: x.n_games, reverse=True)
        for row in range(0, 6):
            self.groups[row + 2].sprites = self.all_decks[row*4:row*4 + 4]
        for g in self.groups:
            g.align(window)


class DeckBuilder(Page):
    def __init__(self, name, host, parent, background, groups=[]):
        super().__init__(name, host, parent, background, groups=[])

        self.current_mode = 'idle'
        self.loop_counter = 0
        self.decks = self.host.dm.decks
        self.set = 2  # Cards at or below set 2 are visible in the DeckBuilder

        # Create Card Objects
        cards = []
        for name, data in card_manager.data.items():
            try:
                c = card_manager.load_card(data['name'], None)
                c.location = 'collection'

                if c.include:
                    cards.append(c)
                    c.location = 'collection'
                    c.size = 'big'
                    c.resize()
                    c.is_static = True
                    c.check_highlight = True
            except AttributeError:
                pass

        # Sort Cards by Color
        card_colors = set([c.color_name for c in cards])
        self.color_groups = {color: [] for color in card_colors}
        self.color_list = [i for i in card_colors]
        self.color_list.sort()
        self.color_list.remove('Neutral')
        self.color_list = self.color_list + ['Neutral']
        for g in self.color_list:
            self.color_groups[g] = [c for c in cards if c.color_name == g]
        # self.sort_color_groups()

        # Set up card pages
        self.top_row = Group('top_row', self, [], 1, 0.5, -50, 1, 0, 0.5, center=-60, spacing=10)
        self.bottom_row = Group('bottom_row', self, [], 1, 0.5, 50, 0, 0, 0.5, center=-60, spacing=10)
        self.x_page = 0
        self.y_page = 0

        # Create Buttons
        self.left_buttons = Group('left_buttons', self, [], 0, 0, 30, 0, 1, 0, low=50, spacing=10)
        for name in ['New Deck', 'Load Deck', 'Save Deck', 'Clear Deck', 'Cancel Changes', 'Delete Deck', 'Back']:
            new = Sprite(name=name, text=name, w=150, h=80, color=Colors['Wood'])
            self.left_buttons.sprites.append(new)

        # Create Card List
        # self.card_list = Group('card_list', self, [], 0, 1, -25, 1, 1, 0, low=100, spacing=1)

        # Create Deck Summary Area ------------------------------------------------------
        self.deck_background = Sprite(layer=-5, w=300, h=750, name='DeckBackground')
        self.deck_background_group = Group('deck_background', self, [self.deck_background],
                                           0, 1, -5, 1, 1, 0, low=5, spacing=1)

        # self.deck_image = Deck(data=self.decks[0])
        # self.deck_summary = Group('deck_summary', self, [self.deck_image],
        #                                0, 1, -5, 1, 1, 0, low=5, spacing=1)
        # self.deck_image.w = 300
        # self.deck_image.h = 100

        # Create sublabels for deck summary
        self.stats_label = Sprite(w=300, h=45, text='Stats', font_size=30)
        self.star_label = Sprite(w=300, h=45, text='Head Start', font_size=30)
        self.deck_label = Sprite(w=300, h=45, text='Deck', font_size=30)

    def sort_display_cards(self):
        #
        # Sort Cards by Mana Cost first, Name second
        for key in self.color_groups:
            self.color_groups[key].sort(key=lambda x: x.name)
            self.color_groups[key].sort(key=lambda x: x.cost)

    def special_inputs(self, events, hovered_ids, pos, mouse):
        hovered_sprites = [i for i in self.view() if i.id in hovered_ids]
        # self.decks[0].is_text_box = True

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pg.K_UP and self.y_page > 0:
                    self.y_page -= 1
                elif e.key == pg.K_DOWN and self.y_page < len(self.color_list) - 1:
                    self.y_page += 1
                elif e.key == pg.K_LEFT and self.x_page > 0:
                    self.x_page -= 1
                elif e.key == pg.K_RIGHT:
                    self.x_page += 1
                max_x_pages = len(self.color_groups[self.color_list[self.y_page]][::10]) - 1
                if self.x_page > max_x_pages:
                    self.x_page = max_x_pages
            if e.type == pygame.MOUSEBUTTONUP:  # Unclick
                for c in hovered_sprites:
                    if c.name == 'New Deck':
                        # First save current deck
                        new = Deck(player=None)
                        self.decks[0] = new
                        self.update_deck_summary()
                    elif c.name == 'Load Deck':
                        self.host.set_page(self.host.deck_chooser.name, come_back=True)
                        self.host.deck_chooser.active_position = 0  # First deck being chosen
                    # elif self.decks[0]:
                    if False:
                        if c.name == 'Save Deck':
                            self.decks[0].save()
                            self.host.pages['Deck Chooser'].update_decks()
                            deck_dictionary = import_decks()
                        elif c.name == 'Clear Deck':
                            if self.decks[0]:
                                self.decks[0].card_names = []
                        elif c.name == 'Cancel Changes':
                            # Reload current deck
                            self.host.dm.load()
                        elif c.name == 'Delete Deck':
                            self.host.chosen_values['Decks'][0].save(delete=True)
                            self.host.chosen_values['Decks'][0] = get_recent_decks()[-1]
                            self.host.pages['Deck Chooser'].update_decks()
                            self.update_deck_summary()
                            deck_dictionary = import_decks()
                        elif c.is_card and self.decks[0]:
                            if c.size == 'big':
                                self.decks[0].card_names.append(c.name)
                            elif c.size == 'summary':
                                if c.name in self.decks[0].card_names:
                                    self.decks[0].card_names.remove(c.name)

    def enter(self, _):
        card_manager.get_changes()

    def update_deck_summary(self):
        pass

    def update_cards(self):
        if card_manager.get_changes():
            for group, contents in self.color_groups.items():
                for c in contents:
                    data = card_manager.data[c.name]
                    for name, value in data.items():
                        setattr(c, name, value)
            self.sort_display_cards()

    def update_positions(self, window):
        if self.loop_counter == 60:
            self.update_cards()
            self.loop_counter = 0
        else:
            self.loop_counter += 1

        display_cards = self.color_groups[self.color_list[self.y_page]][self.x_page*10:self.x_page*10 + 10]
        self.top_row.sprites = display_cards[:5]
        self.bottom_row.sprites = display_cards[5:]

        if False:
            if self.decks[0]:
                # Make card sprites in deck contents match card names
                stats_cards = ['AttackStat', 'HealthStat']
                for c in self.decks[0].contents:
                    if c.name not in self.decks[0].card_names and c.name not in stats_cards:
                        self.decks[0].contents.remove(c)
                current_names = [c.name for c in self.decks[0].contents]

                for name in self.decks[0].card_names + stats_cards:
                    if name not in current_names:
                        new = card_manager.load_card(name)
                        new.size = 'summary'
                        new.is_static = True
                        new.resize()
                        self.decks[0].contents.append(new)

        for g in self.groups:
            g.align(window)


class DeckSummary(Sprite):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_text_box = True


class GameLobby(Page):
    def __init__(self, name, host, parent, background, groups=[]):
        super().__init__(name, host, parent, background, groups=[])

        play_left = Group('play_left', self, [], 0, 0.5, -175, 0, 1, 0.5, low=-100, spacing=10)
        play_right = Group('play_right', self, [], 0, 0.5, 25, 0, 1, 0.5, low=-100, spacing=10)

        for name in ['Name', 'Server', 'Deck']:
            new = Sprite(color=Colors['Dark_Wood'], w=150, h=50, text=name, name=name, type='label', dest=name,
                         check_highlight=False)
            play_left.sprites.append(new)
        self.status_button = Sprite(color=Colors['Wood'], w=500, h=50, name='status_button', text='Not Connected')
        play_left.sprites.append(self.status_button)
        self.play_button = Sprite(color=Colors['Wood'], w=500, h=50, name='play_button', text='Play', is_toggle=True)
        play_left.sprites.append(self.play_button)

        self.name_choice = Sprite(color=Colors['Wood'], w=300, h=50, name='name_choice',
                                  text=self.host.screen_name, is_text_box=True)
        self.server_choice = Sprite(color=Colors['Wood'], w=300, h=50, name='server_choice',
                                    text=self.host.server, is_text_box=True)
        deck_choice = Sprite(color=Colors['Wood'], w=300, h=50, name='deck_choice',
                             text=self.host.dm.chosen_decks[0].name)
        play_right.sprites = [self.name_choice, self.server_choice, deck_choice]

    def special_inputs(self, events, hovered_ids, pos, mouse):
        pass
        # hovered_sprites = [i for i in self.current_page.view() if i.id in hovered_ids]

    def enter(self, source):
        # Connect to Server
        self.host.client.active = True

    def exit(self, destination):
        if destination.__class__.__name__ == 'GameScreen':
            pass
        else:
            # Disconnect from server
            self.host.client.active = False
            self.host.client.connected = False

    def manage_connection(self, loop):
        if self.host.client.actual_status == 'in_game':
            self.host.set_page('Game Screen')
        self.host.client.screen_name = self.name_choice.text
        self.host.client.server = self.server_choice.text

        if self.play_button.toggle_active:
            self.host.client.requested_status = 'searching'
        else:
            self.host.client.requested_status = 'online'

    def update_positions(self, window):
        for g in self.groups:
            g.align(window)

        if self.play_button.toggle_active:
            self.play_button.text = 'Searching for Opponent...'
        else:
            self.play_button.text = 'Play'

        if self.host.client.connected:
            self.status_button.text = 'Connection Successful'
        else:
            self.status_button.text = str(self.host.client.status_message)
