import sys
import time
import asyncio
from game import Game, LocalPlayer
from importlib import import_module, reload

sys.path.insert(0, './bots')

class Singleplayer:
    def __init__(self, challenge, board, user_bot, user_tile, tick_rate):
        self.tick_rate = tick_rate
        self.board = board
        board.set_challenge(challenge)
        self.game = Game(challenge)
        # load player bot
        if user_bot in sys.modules:
             reload(sys.modules[user_bot])
        try:
            script = import_module(user_bot).script
        except:
            raise Exception(f"Failed to load player bot")
        else:
            self.game.load_player(LocalPlayer(self.game, user_bot, user_tile, script))
        self.board.load(self.game.get_map())

    def start(self, updater):
        self.loop = asyncio.get_event_loop()
        self.updater = updater
        updater(0, self.play)

    def stop(self):
        self.updater = None

    def play(self):
        t = time.time()
        cont = self.loop.run_until_complete(self.game.play())
        if cont and self.updater:
            if cont == "new map":
                self.board.load(self.game.get_map())
            map, players = self.game.fetch()
            self.board.update(map, players)
            dt = int((time.time() - t) * 1000)
            print(f"tick, dt/d = {dt}/{self.tick_rate}")
            self.updater(int(max(self.tick_rate - dt, 0)), self.play)
        else:
            self.board.label["text"] += "\n\nGAME OVER!"
