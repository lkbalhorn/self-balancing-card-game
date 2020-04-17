from player_pc import *
import asyncio
import aiohttp
from DeckChooser import *
import socket
import _pickle as pickle
from gameboard import WebPlayer
from game_async import *
import random
from extras import *


class MatchFinder():
    def __init__(self, window):
        self.window = window
        window.carry_on = True
        self.server = '127.00.00.01'
        # self.server = '128.12.244.4'
        # self.server = '10.30.19.220'
        self.port = 5555
        self.change = 3
        self.labels = []
        self.options = []
        self.actions = []
        self.players = []  # From WebPlayer class, inherit from Sprite
        self.challenges = []
        self.challenge_icons = []
        self.screen_name = 'Choose'
        self.deck = [i for i in deck_dictionary][0]
        ws = False
        self.connected = False
        self.connection_id = False
        self.local_player = False
        self.game_id = False
        self.game = False
        self.autoplay = False
        # self.join_room_busy = False
        # self.send_local_data_busy = False
        self.active_requests = 0
        self.web_sockets = []

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
        self.status_box = TextBox(color=Colors['Green'], w=300, h=75, text='Choose', name=name, type='portal')

    def view(self):
        # (self.players,self.labels, self.options, self.actions, self.window.back_button, self.status_box)
        return self.players + self.labels + self.options + self.actions + [self.window.back_button] + [self.status_box]


    def manage_connection(self, loop):
        # self.manage_connection_busy = True
        if not self.connected:
            loop.create_task(self.join_room(loop))
        if self.connected and self.change > 0:
            loop.create_task(self.send_local_data(loop))


    def request_updates(self, loop):
        if self.connected:
            loop.create_task(self.request_data(loop))

    async def message_server(self, message, loop, await_reply=False, buffer=-1, server=False):
        self.active_requests += 1
        open_connection = False
        reply_message = False
        if not server:
            server = self.server
        # Check legal ip address
        if len(server.split('.')) < 4:
            return False

        try:
            ws = await asyncio.wait_for(asyncio.open_connection(server, self.port, loop=loop), timeout=10)
            self.web_sockets.append(ws)
            reader, writer = ws
            open_connection = True

            writer.write(pickle.dumps(message))
            if await_reply:
                data = await reader.read(buffer)
                reply_message = pickle.loads(data)
                if 'bad connection id' in reply_message:
                    self.connected = False
                    self.connection_id = ''
            self.status_box.text = 'Connected'
        except Exception as e:
            self.status_box.text = e.__repr__()
        finally:
            if open_connection:
                writer.close()
        self.active_requests -= 1
        return reply_message

    async def join_room(self, loop):
        if True:
            message = 'request connection as %s' % self.screen_name
            reply = await self.message_server(message, loop, await_reply=True)
            if reply:
                self.connection_id = reply.split(' ')[3]
                print('Connected as %s' % self.connection_id)
                self.connected = True

    async def request_data(self, loop):
        message = 'request room data %s' % self.connection_id
        reply = await self.message_server(message, loop, await_reply=True)
        if reply:
            if 'added to game' in reply:
                # Switch to game protocol
                self.game_id = reply.split(' ')[3]
            else:
                self.players = [i for i in reply if hasattr(i, 'id')]  # List of WebPlayer objects expected

            for p in self.players:
                if hasattr(p, 'id'):
                    if p.id == self.connection_id:
                        self.local_player = p
                        p.text = p.text + ' (You)'
                        break

    async def send_local_data(self, loop):
        # if not self.send_local_data_busy:
        if True:
            # self.send_local_data_busy = True
            message = 'update room data %s %s' % (self.connection_id, self.screen_name)
            await self.message_server(message, loop)
            # self.manage_connection_busy = False
            # self.send_local_data_busy = False

    async def make_challenge(self, loop, opponent_id, action):
        if self.autoplay:
            await asyncio.sleep(0.5)
        message = '%s challenge %s %s' % (action, self.connection_id, opponent_id)
        await self.message_server(message, loop)

    async def terminate(self, loop, server=False):
        if self.connected:
            print('leaving room')
            message = 'leaving room as %s' % self.connection_id
            await self.message_server(message, loop, server=server)

    def update_positions(self):
        # Updates positions of objects so that they can be clicked on
        # Align and Distribute Objects
        align(self.labels, 0, 200, skew=0)
        distribute(self.labels, 1, low=200, spacing=10)
        align(self.options, 0, 320, skew=0)
        distribute(self.options, 1, low=200, spacing=10)
        align(self.players, 0, 200, skew=0)
        distribute(self.players, 1, low=400, spacing=10)
        self.status_box.x = self.window.w - 350
        self.status_box.y = self.window.h - 100

    async def game_server_io(self, loop, inputs, game):
        if inputs:
            events, hovered_object_ids, pos = inputs
            event_types = [i.type for i in events]
            message = ('game_inputs', self.connection_id, (event_types, hovered_object_ids, pos))
        else:
            message = ('game_inputs', self.connection_id, False)
        reply = await self.message_server(message, loop, await_reply=True)

        if reply and 'snapshots' in reply:
            game.snapshots = game.snapshots + reply[1]  # Expects tuple of label and list

    def manage_inputs(self, loop):
        # Part 1 - Check Inputs ------------------------------------------------------------------------- Check Inputs
        pos = pygame.mouse.get_pos()
        events = pygame.event.get()
        trigger = False

        # Close or Resize the Window
        upkeep =  self.window.upkeep(events)
        if upkeep:
            self.change = 3
            if upkeep == 'quit':
                loop.create_task(self.terminate(loop))

        if self.autoplay:
            opponents = [i for i in self.players if i != self.local_player]
            for p in opponents:
                loop.create_task(self.make_challenge(loop, p.id, 'accept'))

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
                    elif c.name == 'Back':
                        self.window.carry_on = False
                    elif c.id in current_players:
                        print('player')
                        # Make or accept a challenge
                        if c.id in challenges_given:
                            # Withdraw Challenge
                            print('withdraw challenge')
                            loop.create_task(self.make_challenge(loop, c.id, 'withdraw'))
                        elif c.id in challenges_received:
                            # Accept Challenge
                            print('accept challenge')
                            loop.create_task(self.make_challenge(loop, c.id, 'accept'))
                        else:
                            # Offer Challenge
                            print('offer challenge')
                            loop.create_task(self.make_challenge(loop, c.id, 'offer'))

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
        ip_text = self.options[1].input_text(events)
        if not self.options[1].is_active:
            if self.server != ip_text:
                # if self.connected:
                    # loop.create_task(self.terminate(loop, server=str(self.server)))
                self.server = ip_text
                self.status_box.text = 'Changing Servers...'


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


    async def game_setup(self, loop):
        print('starting game setup')
        # Submit Deck Information
        ws = await asyncio.open_connection(self.server, self.port, loop=loop) # Nothing else should run during this
        print('connected')
        reader, writer = ws
        writer.write(pickle.dumps(('decklist', self.connection_id, self.deck)))
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



async def main_loop(match_finder, loop):
    try:
        while match_finder.window.carry_on:
            try:
                match_finder.update_positions()
            except Exception as e:
                pass
            match_finder.manage_inputs(loop)
            match_finder.visual_updates()
            if match_finder.game_id:
                match_finder.window.carry_on = False
            if match_finder.active_requests < 30:
                match_finder.manage_connection(loop)
                if match_finder.connected:
                    match_finder.request_updates(loop)
            await asyncio.sleep(1. / 30)

        if not match_finder.game_id:
            raise KeyboardInterrupt

        # Start Game
        game = await match_finder.game_setup(loop)
        game.window.carry_on = True
        await match_finder.game_server_io(loop, False, game)
        game.play_snapshots()
        game.new_snapshot.update_positions(game.window)
        tick = time.time()
        while game.window.carry_on:
            sleep = loop.create_task(asyncio.sleep(1 / settings.GAME_SPEED))
            await asyncio.sleep(0.00001)  # Triggers previous
            game.update_positions()
            inputs = game.window.get_inputs(game.new_snapshot.view())

            await match_finder.game_server_io(loop, inputs, game)

            events, hovered_object_ids, pos = inputs
            game.manage_hover(hovered_object_ids, game.new_snapshot)
            game.window.upkeep(events)
            game.manage_delays(events)

            game.play_snapshots()
            game.update_positions()

            game.new_snapshot.active_hover = game.active_hover
            game.visual_updates(game.window)

            await sleep
    except KeyboardInterrupt:
        pass
    finally:
        await match_finder.terminate(loop)



def main():  # Sets up asynchronous main loop
    window = Window(1000, 800, 'SBCCG P1 View', 'Huangshan_Valley.jpg')
    match_finder = MatchFinder(window)
    match_finder.autoplay = True
    match_finder.setup_screen()
    match_finder.deck = deck_dictionary['Test'] if 'Test' in deck_dictionary else deck_dictionary[[key for key in deck_dictionary][0]]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_loop(match_finder, loop))
    # loop.close()

    pygame.display.quit()
    pygame.quit()

if __name__ == "__main__":
    main()