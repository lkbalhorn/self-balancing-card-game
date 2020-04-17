import asyncio
import json


class Client:
    def __init__(self):
        self.server = '127.00.00.01'
        self.screen_name = 'Player 1'
        self.connected = False
        self.connection_id = False
        self.active_requests = 0
        self.message_number = 0
        self.inbox = []
        self.outbox = []

    def manage_connection(self, loop):
        # Connects to server if not connected, and otherwise updates screen name changes
        if not self.connected:
            loop.create_task(self.join_room(loop))
        if self.connected and self.change > 0:
            loop.create_task(self.send_local_data(loop))

    async def join_room(self, loop):
        # Joins room.  This co-routine allows awaiting a reply
        message = self.prepare_message('request connection')
        # message = 'request connection as %s' % self.screen_name
        reply = await self.message_server(message, loop, await_reply=True)
        if reply:
            self.connection_id = reply['connection_id']
            print('Connected as %s' % self.connection_id)
            self.connected = True

    async def send_local_data(self, loop):
        # Updates screen name (and potentially other routine data in the future).  Co-routine to allow awaiting.
        message = self.prepare_message('update room data')
        await self.message_server(message, loop)

    def prepare_message(self, type, **kwargs):
        new = {'type': type,
               'message_number': self.message_number,
               'connection_id': self.connection_id,
               'screen_name': self.screen_name}
        for kwarg in kwargs:
            new[kwarg] = kwargs[kwarg]
        self.message_number += 1
        return new

    async def message_server(self, message, loop, await_reply=False, buffer=-1, server=False):
        print('sending message', message)
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

            writer.write(json.dumps(message))
            if await_reply:
                data = await reader.read(buffer)
                reply_message = json.loads(data)
                if reply_message.type == 'bad connection id':
                    self.connected = False
                    self.connection_id = ''
                    self.status_box.text = 'Bad Connection ID'
            if self.connected:
                self.status_box.text = 'Connected'
        except Exception as e:
            self.status_box.text = e.__repr__()
        finally:
            if open_connection:
                writer.close()
        self.active_requests -= 1
        return reply_message

    async def terminate(self, loop, server=False):
        if self.connected:
            print('leaving room')
            message = self.prepare_message('leave room')
            await self.message_server(message, loop, server=server)

    def request_updates(self, loop):
        if self.connected:
            loop.create_task(self.request_data(loop))

    async def request_data(self, loop):
        message = self.prepare_message('request room data')
        reply = await self.message_server(message, loop, await_reply=True)
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

    async def make_challenge(self, loop, opponent_id, action):
        if self.autoplay:
            await asyncio.sleep(0.5)
        message = self.prepare_message('challenge', opponent_id=opponent_id)
        await self.message_server(message, loop)



async def test_loop(client, loop):
    while True:
        delay = loop.create_task(asyncio.sleep(1/10))
        client.manage_connection(loop)
        await delay



def main():  # Sets up asynchronous main loop
    client = Client()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_loop(client, loop))

if __name__ == "__main__":
    main()