from player_pc import *
import asyncio
import aiohttp
from DeckChooser import *
import socket
import _pickle as pickle
from gameboard import WebPlayer
from game_async import *
import random
import settings


class MatchFinder():
    def __init__(self, window):
        self.window = window
        window.carry_on = True
        self.server = '127.00.00.01'
        self.port = 8888
        self.change = 3
        self.labels = []
        self.options = []
        self.actions = []
        self.players = []  # From WebPlayer class, inherit from Sprite
        self.challenges = []
        self.challenge_icons = []
        self.screen_name = 'Choose'
        self.deck = [i for i in deck_dictionary][0]
        self.ws = False
        self.connected = False
        self.connection_id = False
        self.local_player = False
        self.game_id = False
        self.game = False
        self.autoplay = False

    def setup_screen(self):
        self.change = 3
        for name in ['Name', 'Server', 'Deck']:
            new = Sprite(color=Colors['Green'], w=100, h=50, text=name, name=name, type='portal')
            self.labels.append(new)
        for name in ['Name', 'Server', 'Deck']:
            new = TextBox(color=Colors['Green'], w=300, h=50, text='Choose', name=name, type='portal')
            self.options.append(new)
            if name == 'Server':
                new.text = self.server
            if name == 'Name':
                new.text = 'Player_1'

    def view(self):
        return self.players + self.labels + self.options + self.actions


    def manage_connection(self, loop):
        if not self.connected:
            self.join_room(loop)
        if self.connected and self.change > 0:
            self.send_local_data(loop)

    def request_updates(self, loop):
        if self.connected:
            self.request_data(loop)

    def join_room(self, loop):
        try:
            self.connected = True
            self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop)
            reader, writer = self.ws

            writer.write(pickle.dumps('request connection as %s' % self.screen_name))
            data = reader.read(100)
            message = pickle.loads(data)
            # Expects 'Connected with id 0000000000000
            self.connection_id = message.split(' ')[3]
            print('Connected as %s' % self.connection_id)
            writer.close()

        except ConnectionRefusedError:
            self.connected = False

    def request_data(self, loop):
        try:
            self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop)
            reader, writer = self.ws
        except ConnectionRefusedError:
            print('Connection Refused')
            return
        except OSError:
            print('OSError')
            return

        writer.write(pickle.dumps('request room data %s' % self.connection_id))
        data = reader.read(-1)
        message = pickle.loads(data)

        if 'added to game' in message:
            # Switch to game protocol
            self.game_id = message.split(' ')[3]

        else:
            self.players = pickle.loads(data)  # List of WebPlayer objects expected

        for p in self.players:
            if p.id == self.connection_id:
                self.local_player = p
                p.text = p.text + ' (You)'
                break

        writer.close()


    def send_local_data(self, loop):
        self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop)
        reader, writer = self.ws
        message = 'update room data %s %s' % (self.connection_id, self.screen_name)
        writer.write(pickle.dumps(message))
        writer.close()

    def make_challenge(self, loop, opponent_id, action):
        self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop)
        reader, writer = self.ws
        if self.autoplay:
            asyncio.sleep(0.5)

        message = '%s challenge %s %s' % (action, self.connection_id, opponent_id)
        writer.write(pickle.dumps(message))
        writer.close()

    def terminate(self, loop):
        print('leaving room')
        self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop)
        reader, writer = self.ws
        message = 'leaving room as %s' % self.connection_id
        writer.write(pickle.dumps(message))
        print('message sent')
        reader.read(100)  # Just waiting for confirmation
        writer.close()
        print('writer closed')

    def update_positions(self, loop):
        # Updates positions of objects so that they can be clicked on
        # Align and Distribute Objects
        align(self.labels, 0, 200, skew=0)
        distribute(self.labels, 1, low=200, spacing=10)
        align(self.options, 0, 320, skew=0)
        distribute(self.options, 1, low=200, spacing=10)
        align(self.players, 0, 200, skew=0)
        distribute(self.players, 1, low=400, spacing=10)

    def game_server_io(self, loop, inputs, game):
        try:
            self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop)
            reader, writer = self.ws
        except ConnectionRefusedError:
            return
        except OSError:
            return

        events, hovered_object_ids, pos = inputs
        event_types = [i.type for i in events]
        message = ('game_inputs', self.connection_id, (event_types, hovered_object_ids, pos))
        writer.write(pickle.dumps(message))

        try:
            data = reader.read(-1)  # -1 yields whole stream
            message = pickle.loads(data)
        except EOFError:
            return

        if 'snapshots' in message:
            game.snapshots = game.snapshots + message[1]  # Expects tuple of label and list
        else:
            # print(message)
            pass
        writer.close()

    def manage_inputs(self, loop):
        # Part 1 - Check Inputs ------------------------------------------------------------------------- Check Inputs
        pos = pygame.mouse.get_pos()
        events = pygame.event.get()
        trigger = False

        # Close or Resize the Window
        upkeep =  self.window.upkeep(events)
        if upkeep:
            self.change = 3

        if self.autoplay:
            opponents = [i for i in self.players if i != self.local_player]
            for p in opponents:
                self.make_challenge(loop, p.id, 'accept')

        for event in events:
            if event.type == pygame.KEYDOWN:
                self.change = 3
            if event.type == pygame.MOUSEBUTTONDOWN:  # For button click animation
                self.change = 3
            if event.type == pygame.MOUSEBUTTONUP:
                self.change = 3
                # Get a list of clicked sprites under cursor
                clicked_items = [c for c in self.view() if c.collide(pos)]
                current_players = [i.id for i in self.players]
                challenges_given = [i for i in self.local_player.challenges_given] if self.local_player else []
                challenges_received = [i for i in self.local_player.challenges_received]if self.local_player else []
                for c in clicked_items:
                    if c in self.options:
                        if c.name in ['Name', 'Server']:
                            c.toggle()
                        elif c.name == 'Deck':
                            new_ID = run_deck_chooser(self.window)
                            if new_ID is not None:
                                self.deck = deck_dictionary[new_ID]
                                c.text = deck_dictionary[new_ID][1]
                    elif c.id in current_players:
                        print('player')
                        # Make or accept a challenge
                        if c.id in challenges_given:
                            # Withdraw Challenge
                            print('withdraw challenge')
                            self.make_challenge(loop, c.id, 'withdraw')
                        elif c.id in challenges_received:
                            # Accept Challenge
                            print('accept challenge')
                            self.make_challenge(loop, c.id, 'accept')
                        else:
                            # Offer Challenge
                            print('offer challenge')
                            self.make_challenge(loop, c.id, 'offer')

        # Apply Button Press Animation
        for i in self.view():
            if i.collide(pos) and pygame.mouse.get_pressed()[0]:
                i.over_alpha = 100
                i.over_fill = True
                i.over_tint = shade(i.color, shade_fraction=0.25)
                i.highlight = True
            else:
                i.highlight = False

        # Update Text Boxes
        self.screen_name = self.options[0].input_text(events)
        self.server = self.options[1].input_text(events)


    def visual_updates(self):
        if self.change:
            # Re-Color Players
            for p in self.players:
                if p.id in self.local_player.challenges_given:
                    p.color = Colors['Purple']
                elif p.id in self.local_player.challenges_received:
                    p.color = Colors['Blue']
                else:
                    p.color = Colors['Red']

            self.window.quick_background('Huangshan_Valley.jpg')
            self.window.quick_draw(self.view())

            self.change -= 1
            pygame.display.flip()


    def game_setup(self, loop):
        print('starting game setup')
        # Submit Deck Information
        self.ws = asyncio.open_connection('127.0.0.1', 5555, loop=loop) # Nothing else should run during this
        print('connected')
        reader, writer = self.ws
        writer.write(pickle.dumps(('decklist', self.connection_id, deck_dictionary[self.deck])))
        print('sent')
        writer.close()

        game = Game()
        print(game)
        game.setup_window(self.window)
        game.setup_game()
        game.change = 10

        return game







def go_online(window):
    match_finder = MatchFinder(window)
    match_finder.setup_screen()

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(main_loop(match_finder, event_loop))



def main_loop(match_finder, loop):
    try:
        while match_finder.window.carry_on:
            match_finder.update_positions(loop)
            match_finder.manage_inputs(loop)
            match_finder.visual_updates()
            match_finder.manage_connection(loop)
            match_finder.request_updates(loop)
            if match_finder.game_id:
                game = match_finder.game_setup(loop)
                while match_finder.window.carry_on:
                    game.update_positions()
                    if game.new_snapshot:
                        inputs = match_finder.window.get_inputs(game.new_snapshot.view())
                    else:
                        inputs = match_finder.window.get_inputs(game.view())  # Place Holder

                    # if 5 in inputs[0] or 6 in inputs[0] or random.randint(0, 10) == 10:
                        # print('task created')
                    match_finder.game_server_io(loop, inputs, game)
                    events, hovered_object_ids, pos = inputs
                    game.manage_hover(hovered_object_ids)
                    game.window.upkeep(events)
                    game.manage_delays(events)
                    asyncio.sleep(0.2 / settings.GAME_SPEED)
                    game.play_snapshots()
                    game.update_positions()
                    if game.new_snapshot:
                        game.window.manage_spring_animations(game.new_snapshot.view(), game.change)

                    # game.read_snapshot(game.new_snapshot)
                    game.visual_updates(game.window, from_snapshot=True)
                    asyncio.sleep(0.8 / settings.GAME_SPEED)
                # asyncio.sleep(1 / 1000)
            asyncio.sleep(1. / 30)
    finally:
        match_finder.terminate(loop)


def main():  # Sets up asynchronous main loop
    window = Window(1000, 800, 'SBCCG P1 View', 'Huangshan_Valley.jpg')
    match_finder = MatchFinder(window)
    match_finder.autoplay = True
    match_finder.setup_screen()
    loop = False
    main_loop(match_finder, loop)

if __name__ == "__main__":
    main()