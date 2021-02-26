from Connection import *
from .Player import Player
import asyncio

class RemotePlayer(Player, Connection):
    def __init__(self, game, reader, writer):
        Connection.__init__(self, reader, writer)
        self.username = None
        self.server_game = game # idk python inheritance too hard for me

    async def connect(self):
        data = await self.communicate("player "+self.server_game.name)
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