from Constants import *

class Player:
    def __init__(self, game, name, tile):
        self.game = game
        self.name = name
        self.tile = tile
        self.x, self.y = 0, 0
        self.gold = 0
        self.keys = 0

    def act(self, cmd):
        if cmd == PASS: return
        dx, dy = 0, 0
        if cmd == TAKE:
            self.take()
        elif cmd == UP:
            dy -= 1
        elif cmd == DOWN:
            dy += 1
        elif cmd == LEFT:
            dx -= 1
        elif cmd == RIGHT:
            dx += 1
        self.move(dx, dy)

    def move(self, dx, dy):
        if dx or dy:
            x, y = self.x + dx, self.y + dy
            game = self.game
            game.remove_player(self)
            if not game.check(WALL, x, y) and not game.check(PLAYER, x, y) and ((not game.check(DOOR, x, y)) | self.keys):
                self.x, self.y = x, y
            game.add_player(self, self.x, self.y)

    def take(self):
        gold = self.game.check(GOLD, self.x, self.y)
        if gold:
            self.gold += gold
            self.game.take_item(self.x, self.y)
        key = self.game.check(KEY, self.x, self.y)
        if key:
            self.keys += 1
            self.game.take_item(self.x, self.y)
        portal = self.game.check(PORTAL, self.x, self.y)
        if portal:
            portals = [];
            for i in range(self.game.cols):
                for j in range(self.game.rows):
                    if (self.game.map[i][j] == '?') and (not (i == self.x & j == self.y)):
                        portals.append((j,i));
            self.x, self.y = random.choice(portals);

    def newlevel(self):
        self.gold = 0
        self.keys = 0