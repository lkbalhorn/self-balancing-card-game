import asyncio
import json
import os
from card import *
# import globals


class Client:
    def __init__(self, host):
        self.host = host
        # self.server = '10.30.1.143'
        self.server = '127.00.00.01'
        self.port = '5555'
        self.id = str(id(self))
        self.screen_name = 'Player 1'
        self.active = False
        self.connected = False
        self.connection_id = False
        self.active_requests = 0
        self.low_priority_request_limit = 1000 # System max is 512
        self.message_number = 0
        self.loop_counter = 0
        self.inbox = []
        self.outbox = []
        self.status = ''
        self.status_message = 'Connecting...'
        self.requested_status = 'online'  # Either online, searching, or in_game
        self.actual_status = 'offline'
        self.game_id = False

    def manage_connection(self, loop):
        if self.active:
            # Connects to server if not connected, and otherwise updates screen name changes
            if self.active_requests < self.low_priority_request_limit:
                if not self.connected:
                    loop.create_task(self.join_room(loop))
                if self.connected:  # Consider only sending data if something has changed
                    loop.create_task(self.update_player_data(loop))

                    if self.loop_counter > 60:
                        loop.create_task(self.update_card_data(loop))
                        self.loop_counter = 0
                    else:
                        self.loop_counter += 1

    async def join_room(self, loop):  # aka request connection
        # Joins room.  This co-routine allows awaiting a reply
        try:
            message = self.prepare_message('request connection')
            reply = await self.message_server(message, loop, await_reply=True)
            if reply:
                if reply['type'] == 'bad player id':
                    pass
                else:
                    self.connection_id = reply['connection_id']
                    print('Connected as %s' % self.connection_id)
                    self.connected = True
        except OSError as e:
            self.status_message = e
            self.connected = False
        except ConnectionRefusedError as e:
            self.status_message = e
            self.connected = False
        except TimeoutError as e:
            self.status_message = e
            self.connected = False

    async def update_player_data(self, loop):
        # Updates screen name (and potentially other routine data in the future).  Co-routine to allow awaiting.
        message = self.prepare_message('update player data')
        reply = await self.message_server(message, loop, await_reply=True)
        if reply:
            if 'actual_status' in reply:
                self.actual_status = reply['actual_status']
            if 'game_id' in reply:
                self.game_id = reply['game_id']
            if 'data' in reply:
                self.inbox = self.inbox + reply['data']

    async def send_outbox(self, loop):
        # print('outbox', self.outbox)
        message = self.prepare_message('send outbox', data=list(self.outbox))
        await self.message_server(message, loop)
        self.outbox = []

    def prepare_message(self, type, **kwargs):
        decklist = self.host.chosen_values['Decks'][0].card_names if self.host else []
        new = {'type': type,
               'message_number': self.message_number,
               'connection_id': self.connection_id,
               'screen_name': self.screen_name,
               'requested_status': self.requested_status,
               'client_id': self.id,
               'decklist': decklist,
               'data': list(self.outbox)}
        self.outbox = []
        for kwarg in kwargs:
            new[kwarg] = kwargs[kwarg]
        self.message_number += 1
        return new

    async def message_server(self, message, loop, await_reply=False, buffer=-1, server=False):
        # print('sending message', message)
        self.active_requests += 1
        open_connection = False
        reply_message = False
        if not server:
            server = self.server
        print(server)
        # Check legal ip address
        if len(server.split('.')) < 4:
            return False

        try:
            ws = await asyncio.wait_for(asyncio.open_connection(server, self.port, loop=loop), timeout=10)
            reader, writer = ws
            open_connection = True

            writer.write(json.dumps(message).encode('utf8'))
            if await_reply:
                # print('Awaiting Reply...')
                data = await reader.read(buffer)
                reply_message = json.loads(data.decode('utf8'))
                if reply_message['type'] == 'bad connection id':
                    self.connected = False
                    self.connection_id = ''
                    self.status = 'Bad Connection ID'
            if self.connected:
                self.status = 'Connected'
        except OSError as e:
            self.status_message = e
            self.connected = False
        except ConnectionRefusedError as e:
            self.status_message = e
            self.connected = False
        except TimeoutError as e:
            self.status_message = e
            self.connected = False
        finally:
            if open_connection:
                writer.close()
        self.active_requests -= 1
        # print('Received Reply:', reply_message)
        return reply_message

    async def terminate(self, loop, server=False):
        if self.connected:
            print('leaving room')
            message = self.prepare_message('leave room')
            await self.message_server(message, loop, server=server)

    def request_updates(self, loop):
        if self.connected:
            loop.create_task(self.request_data(loop))

    async def update_card_data(self, loop):
        message = self.prepare_message('update card data')
        reply = await self.message_server(message, loop, server=self.server, await_reply=True)
        if reply:
            global card_dictionary
            card_dictionary = reply['data']
            save_card_data(card_dictionary)
        else:
            self.connected = False
            self.status_message = 'No Reply from Server'

    async def request_data(self, loop):
        message = self.prepare_message('request room data')
        reply = await self.message_server(message, loop, server=self.server, await_reply=True)
        if reply:
            if reply.type == 'added to game':
                # Switch to game protocol
                self.game_id = reply.game_id
            else:
                self.players = [i for i in reply if hasattr(i, 'id')]  # List of WebPlayer objects expected

            for p in self.players:
                if hasattr(p, 'id'):
                    if p.id == self.connection_id:
                        self.local_player = p
                        p.text = p.text + ' (You)'
                        break

    async def update_search(self, loop, new_status):
        message = self.prepare_message('update_search', status=new_status)
        await self.message_server(message, loop)

    async def make_challenge(self, loop, opponent_id, action):
        if self.autoplay:
            await asyncio.sleep(0.5)
        message = self.prepare_message('challenge', opponent_id=opponent_id)
        await self.message_server(message, loop)



async def main_loop(client, loop):
    while True:
        delay = loop.create_task(asyncio.sleep(1))
        client.manage_connection(loop)
        await delay



def main():  # Sets up asynchronous main loop
    client = Client(None)
    client.active = True
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_loop(client, loop))

if __name__ == "__main__":
    main()