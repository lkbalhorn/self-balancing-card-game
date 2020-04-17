# Version 1 at https://shakeelosmani.wordpress.com/2015/04/13/python-3-socket-programming-example/
# Version 2 at http://asyncio.readthedocs.io/en/latest/tcp_echo.html

import asyncio

class game:
    def __init__(self):
        self.number = 0

async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    print("Send: %r" % message)
    message = message + str(game.number)
    data = message.encode()
    writer.write(data)
    await writer.drain()

    print("Close the client socket")
    writer.close()

test_game = game()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_echo, '127.0.0.1', 8888, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
