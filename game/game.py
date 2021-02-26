import json
from random import shuffle
import random
import asyncio
from importlib import import_module
from Players import LocalPlayer
from Constants import *

class BaseGame:
    def __init__(self):
        self.players = []
        self.level_index = 0
        self.level = []
        self.map_title = "Map"
        self.map_tiles = None
        self.steps = 0

    def load_player(self, player, x, y):
        self.players.append(player)
        self.add_player(player, x, y)
        shuffle(self.players)

    def load_level(self, tiles):
        self.steps = 0
        self.cols, self.rows = cols, rows = len(tiles[0]), len(tiles)
        self.map = [[tiles[y][x] for x in range(cols)] for y in range(rows)]
        self.has_player = [[None for y in range(rows)] for x in range(cols)]

    def get(self, x, y):
        if x < 0 or y < 0 or x >= self.cols or y >= self.rows:
            return "#"
        return self.map[y][x]

    def remove_player(self, player):
        self.has_player[player.x][player.y] = None

    def add_player(self, player, x, y):
        player.x, player.y = x, y
        self.has_player[x][y] = player

    def take_item(self, x, y):
        self.map[y][x] = " "

    def check(self, cmd, *args):
        if cmd == LEVEL:
            return self.level_index + 1
        x, y = args
        item = self.get(x, y)
        if cmd == WALL:
            return item == "#"
        if cmd == GOLD:
            return int(item) if item.isdigit() else 0
        if cmd == PLAYER:
            return item != "#" and self.has_player[x][y]
        if cmd == PORTAL:
            return item == "?"
        if cmd == KEY:
            return item == "K"
        if cmd == DOOR:
            return item == "D"
        return cmd == EMPTY

    async def play(self):
        for p in self.players:
            await p.do_action()
        self.steps += 1

    def get_map(self):
        return {
            "grid": ["".join(row) for row in self.map],
            "title": self.map_title,
            "tiles": self.map_tiles or self.challenge.get("tiles")
        }

    def fetch(self):
        players = [{
            "name": p.name,
            "tile": p.tile,
            "x": p.x, "y": p.y,
            "gold": p.gold
        } for p in self.players]
        grid = ["".join(row) for row in self.map]
        return grid, players

class LocalGame(BaseGame):
    def __init__(self, challenge, load=True):
        super().__init__()
        self.challenge = challenge
        self.level_index = 0
        self.players = []
        if load: self.load_level()
        # load challenge bots
        for bot in (challenge.get("bots") or []):
            print("load bot: "+bot)
            try:
                script = import_module(bot).script
            except:
                raise Exception(f"Failed to load bot: {bot}")
            else:
                tile = challenge["tiles"][name] if "tiles" in challenge and name in challenge["tiles"] else BOT_TILE
                self.load_player(LocalPlayer.LocalPlayer(self, bot, tile, script))

    def load_player(self, player):
        super().load_player(player, *self.level["start"])

    def load_level(self):
        self.level = self.challenge["levels"][self.level_index]
        name = self.level["map"]
        if type(name) is str: # map from separate file
            # TODO: handle map loading error
            fname = name if name.endswith(".json") else name + ".json"
            map = json.loads(MAPS_DIR.joinpath(fname))
            data = map["grid"]
            self.map_title = map["title"]
            self.map_tiles = map.get("tiles")
        else: # map from chal file
            data = self.challenge["maps"][name]
            self.map_title = str(name + 1)
            self.map_tiles = None

        self.totalgoldtaken = 0
        super().load_level(data)
        for p in self.players:
            p.newlevel()
            self.add_player(p, *self.level["start"])

    def take_item(self, x, y):
        self.totalgoldtaken += self.check("gold", x, y)
        super().take_item(x,y)

    async def play(self):
        await super().play()
        if self.totalgoldtaken >= self.level["gold"]:
            return self.next_level()
        return not self.level.get("steps") or self.steps < self.level["steps"]

    def next_level(self):
        self.level_index += 1
        if self.level_index < len(self.challenge["levels"]):
            self.load_level()
            return "new map"
        return False

    def get_map(self):
        return {
            "map": super().get_map(),
            "start": self.level["start"]
        }
