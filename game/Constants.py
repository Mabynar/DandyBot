import sys
import os
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir,'bots'))

MAPS_DIR = Path(os.path.join(os.path.dirname(__file__), "game/maps"))

UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"
TAKE = "take"
PASS = "pass"

LEVEL = "level"
PORTAL = "portal"
KEY = "key"
DOOR = "door"
PLAYER = "player"
GOLD = "gold"
WALL = "wall"
EMPTY = "empty"

BOT_TILE = 2128

CHUNK = 1024