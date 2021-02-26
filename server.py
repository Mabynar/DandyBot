import sys
import time
import json
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'game'))
from pathlib import Path
from game import LocalGame
from Players import RemotePlayer
from threading import Thread
from Constants import *
import asyncio

PLAYER_TILE = 2138
TICKRATE = 75
CHALLENGES = Path(os.path.join(os.path.dirname(__file__),'game/challenges'))


class ServerGame(LocalGame):
    def __init__(self, name, challenge, tick_rate):
        super().__init__(challenge)
        self.name = name
        self.tick_rate = tick_rate
        self.running = False
        self.loop = asyncio.new_event_loop()
        self.remote_players = []
        #asyncio.set_event_loop(self.loop)

    async def connect_player(self, reader, writer):
        player = RemotePlayer.RemotePlayer(self, reader, writer)
        await player.connect()
        self.remote_players.append(player)
        self.load_player(player)

    def stop(self):
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            t = time.time()
            status = await self.play()
            if status:
                if status == "new map":
                    for p in self.remote_players:
                        await p.communicate("map", self.get_map())
                dt = int((time.time() - t) * 1000)
                #print(f"tick, dt/d = {dt}/{self.tick_rate}")
                await asyncio.sleep(int(max(self.tick_rate - dt, 0))/1000)
            else:
                for p in self.remote_players:
                    await p.communicate("game_over", None, None)
                self.stop()


class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.games = {}

    def create_game(self):
        chal_path = CHALLENGES.joinpath("original.json")
        chal = json.loads(chal_path.read_text())
        name = str(len(self.games))
        print("new game: "+name)
        self.games[name] = ServerGame(name, chal, TICKRATE)
        return self.games[name]

    async def resp(self, writer, msg):
        writer.write(msg.encode() + b'\n')
        await writer.drain()

    async def listener(self, reader, writer):
        while True:
            data = await reader.read(CHUNK)
            message = data.decode()
            if not message:
                await asyncio.sleep(0.01)
                continue
            print("got: "+message)
            if message.startswith("get"):
                await self.resp(writer, self.get(message.split()[1]))
            elif message.startswith("ping"):
                await self.resp(writer, "pong")
            elif message.startswith("rooms"):
                rooms = list(self.games.keys())
                await self.resp(writer, "rooms "+json.dumps(rooms))
            elif message.startswith("connect"):
                split = message.split(" ")
                if len(split) < 2: # create new room
                    game = self.create_game()
                else:
                    game = self.games.get(split[1])
                    if game is None:
                        await self.resp(writer, "404")
                        break
                await game.connect_player(reader, writer)
            elif message.startswith("start"):
                split = message.split(" ")
                if len(split) < 2:
                    await self.resp(writer, "400")
                    break
                game = self.games.get(split[1])
                if game is None:
                    await self.resp(writer, "404")
                else:
                    await game.start()
                break

    async def handler(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"{addr} connected")
        await self.listener(reader, writer)

    def get(self, what):
        if what == "challenge":
            return "the trial"
        else:
            return None

    async def serve(self):
        server = await asyncio.start_server(
            self.handler, self.ip, self.port)

        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

server = Server('127.0.0.1', 8989)
asyncio.run(server.serve())
