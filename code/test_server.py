import asyncio
import json

from aiohttp import web


class Server:
    def __init__(self):
        self.clients = {}
        self.games = {}
        self.chats = {}
        self.challenges = {}

    async def welcome(self, request):
        return web.Response(text='Welcome')

    async def get_lobby(self, request):
        return web.Response(text=json.dumps(self.clients))

    async def get_game_state(self, request):
        # This will need some experimentation
        print(request)


if __name__ == "__main__":
    server = Server()
    app = web.Application()
    app.router.add_get('/', server.welcome)
    app.router.add_get('/lobby', server.get_lobby)
    web.run_app(app)
    # Runs on localhost:8080 by default

