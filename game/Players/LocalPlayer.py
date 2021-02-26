from .Player import Player

class LocalPlayer(Player):
    def __init__(self, game, name, tile, script):
        super().__init__(game, name, tile)
        self.script = script

    async def do_action(self):
        self.act(self.script(self.game.check, self.x, self.y))