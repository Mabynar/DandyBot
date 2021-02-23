import sys
import time
import json
sys.path.insert(0, './game')
from pathlib import Path
from game import Game, Player
from threading import Thread
import asyncio
BOT_TILE = 2128
PLAYER_TILE = 2138
CHUNK = 1024
TICKRATE = 100
CHALLENGES = Path('./game/challenges')

class Connection:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def communicate(self, command, object=None):
        message = command + ("" if object is None else (" " + json.dumps(object))) + "\n"
        self.writer.write(message.encode())
        await self.writer.drain()
        print("sent: "+message)
        resp = await self.reader.read(CHUNK)
        resp = resp.decode()
        if not object is None and resp == "ok":
            return True
        try:
            return json.loads(resp)
        except:
            await self.send_status("400")
            raise Exception("Failed to communicate: "+command)

    async def send_status(self, message):
        self.writer.write(message.encode() + b'\n')
        await self.writer.drain()

    def close(self):
        self.writer.close()

class RemotePlayer(Player, Connection):
    def __init__(self, game, reader, writer):
        Connection.__init__(self, reader, writer)
        self.username = None
        self.server_game = game

    async def connect(self):
        data = await self.communicate("player")
        username = data.get("name")
        bot_name = data.get("bot")
        bot_tile = data.get("tile")
        if not username or not bot_name or not bot_tile:
            await self.send_status("400")
            raise Exception("Bad player data")
        self.username = str(username)
        Player.__init__(self, self.server_game, str(bot_name), int(bot_tile))
        await self.send_status("200")
        await self.communicate("map", self.game.get_map())

    async def do_action(self):
        map, players = self.game.fetch()
        state = {
            "x": self.x, "y": self.y,
            "grid": map,
            "players": players,
            "level": self.game.level_index}
        await self.communicate("state", state)
        res = await self.communicate("action")
        self.act(res["action"])


class ServerGame(Game):
    def __init__(self, challenge, tick_rate):
        super().__init__(challenge)
        self.tick_rate = tick_rate
        self.running = False
        self.loop = asyncio.new_event_loop()
        self.remote_players = []
        #asyncio.set_event_loop(self.loop)

    async def connect_player(self, reader, writer):
        player = RemotePlayer(self, reader, writer)
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
                print(f"tick, dt/d = {dt}/{self.tick_rate}")
                #await asyncio.sleep(int(max(self.tick_rate - dt, 0))/1000)
            else:
                for p in self.remote_players:
                    await p.communicate("game_over")
                self.stop()


class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.games = []

    def load_challenge(self, title):
        chal_path = CHALLENGES.joinpath(title)
        return json.loads(chal_path.read_text())

    async def start_game(self, chal_name, reader, writer):
        chal = self.load_challenge(chal_name)
        game = ServerGame(chal, TICKRATE)
        #try:
        await game.connect_player(reader, writer)
        self.games.append(game)
        await game.start()
        #except Exception as e:
        #    print("failed to connect player to solo game")

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
            if message.startswith("get"):
                await self.resp(writer, self.get(message.split()[1]))
            elif message.startswith("ping"):
                await self.resp(writer, "pong")
            elif message.startswith("start"):
                #t = Thread(target=self.start_game, args=("original.json", reader, writer,))
                #t.start()
                await self.start_game("original.json", reader, writer)
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
