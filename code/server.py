import os
import asyncio
import json
from aiohttp import web
import socket
from netifaces import interfaces, ifaddresses, AF_INET

import game as gm
import time

from card import *  # For loading Data
from game_screen import WebPlayer


class GameServer:
    def __init__(self):
        self.web_players = {}
        self.games = {}
        self.message_number = 0
        
    def prepare_message(self, type, **kwargs):
        new = {'type': type,
               'message_number': self.message_number}
        for kwarg in kwargs:
            new[kwarg] = kwargs[kwarg]
        self.message_number += 1
        return new

    async def handle_request(self, reader, writer):
        try:
            addr = writer.get_extra_info('peername')
            data = await reader.read(4096)
            message = json.loads(data.decode('utf8'))
        except EOFError:
            # Ignore - probably a disconnect
            print('EOFError')
            return
        except ConnectionResetError:
            print('Connection Reset Error')
            return
        except OSError:
            print('OS Error')
            return
        except json.decoder.JSONDecodeError:
            # Probably empty message
            return
        # print('Received Message:', message)

        reply = self.prepare_message('null')
        try:
            id = message['connection_id']
            screen_name = message['screen_name']
            message_type = message['type']
            requested_status = message['requested_status']
            client_id = message['client_id']
            # print(id, screen_name, message_type)
            if message['type'] == 'request connection':
                if id in self.web_players:
                    new = self.web_players[id]
                    print('web player reconnected')
                else:
                    new = WebPlayer(addr, screen_name, client_id)
                    self.web_players[new.id] = new
                    print('new web player created')
                reply = self.prepare_message('connected', connection_id=new.id)
            elif id not in self.web_players:
                # Recently deleted
                pass

            elif message['type'] == 'update player data':
                if id != 'False':
                    self.web_players[id].screen_name = screen_name
                    self.web_players[id].decklist = message['decklist']
                    if self.web_players[id].actual_status != 'in_game':
                        self.web_players[id].actual_status = requested_status
                    actual_status = self.web_players[id].actual_status

                    # Purge Duplicate Connections
                    duplicate_connections = []
                    current_player = self.web_players[id]
                    for id2, p in self.web_players.items():
                        if p != current_player and p.client_id == current_player.client_id:
                            duplicate_connections.append(id2)
                    for i in duplicate_connections:
                        del self.web_players[i]
                        print('duplicate connection removed')

                    # Check for Opponents
                    if actual_status == 'searching':
                        for id2, p in self.web_players.items():
                            if id2 != id and p.actual_status == 'searching':
                                print('opponent found')
                                players = [p, current_player]
                                for p in players:
                                    p.actual_status = 'in_game'
                                    if players[0].game_id == False and players[1].game_id == False:
                                        game = gm.Game()
                                        player_ids = [p.id for p in players]
                                        game.setup_game(player_ids)
                                        print('game created')
                                        for i, p in enumerate(players):
                                            p.game_id = game.id
                                            game.web_players.append(p)
                                            self.games[game.id] = game
                                            p.opponent = players[i - 1]
                                            game.players[i].web_player_id = p.id
                                            game.players[i].screen_name = p.screen_name
                                        decks = [p.decklist for p in players]
                                        # print(decks)
                                        game.deal_cards(decks)
                                # Players will be notified of this when they request room info
                                break

                    snapshots = []
                    if current_player.actual_status == 'in_game':
                        if current_player.game_id:
                            current_game = self.games[current_player.game_id]
                            if 'data' in message:
                                player_actions = message['data']
                                # if player_actions:
                                    # print('server received player actions', player_actions)
                                current_game.single_loop(player_actions)

                            game_player = current_game.players_by_id[current_player.id]
                            snapshots = [s for s in game_player.snapshots]
                            game_player.snapshots = []

                    reply = self.prepare_message('game_status', actual_status=current_player.actual_status,
                                                 game_id=current_player.game_id, data=snapshots)
            elif message['type'] == 'update card data':
                data = import_card_library()  # No need for global - reloaded when game starts
                reply = self.prepare_message('card_data', data=data)

            elif message['type'] == 'leave room':
                print('deactivating player')
                self.web_players[id].connected = False
                reply = self.prepare_message('leaving successful')
                print('Player Deactivated')

            else:
                print(message)

        except KeyError:
            reply = self.prepare_message('bad player id')
            raise

        finally:
            # print('Returning Reply:', reply)
            writer.write(json.dumps(reply).encode('utf8'))
            await writer.drain()
            writer.close()


if __name__ == "__main__":
    game_server = GameServer()
    loop = asyncio.get_event_loop()
    address = '127.00.00.01'
    coro = asyncio.start_server(game_server.handle_request, '', 5555, loop=loop)
    server = loop.run_until_complete(coro)

    try:
        ip = server.sockets[0].getsockname()
    except Exception as e:
        ip = '127.00.00.01'
    print('Serving on {}'.format(ip))

    # Using netifaces
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr': 'No IP addr'}])]
        print('%s: %s' % (ifaceName, ', '.join(addresses)))

    # Serve requests until Ctrl+C is pressed
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


    """
    Look at aiohttp:
    multipart
    request library
    Restful interfaces - check Wikipedia
    check https://stanford.zoom.us/j/974984604 from Chris
    """


