import sys
import json
import signal
import asyncio
import traceback
from contextlib import suppress
from queue import Queue
from threading import Thread
from game import Game
from importlib import import_module, reload

sys.path.insert(0, './bots')

class Multiplayer:
    def __init__(self, board, server, port, username):
        self.queue = Queue()
        self.board = board
        self.server = server
        self.port = port
        self.username = username
        self.loop = loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        loop.create_task(self.connect())
        def run_loop():
            try:
                loop.run_forever()
                loop.run_until_complete(loop.shutdown_asyncgens())
                tasks = asyncio.all_tasks(loop)
                for task in tasks:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        loop.run_until_complete(task)
            finally:
                loop.close()
        self.thread = Thread(target=run_loop)
        self.thread.start()

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.server, self.port)
        except:
            return self.handle_error("Can't connect to server!")
        await self.resp("ping")
        data = await self.reader.readline()
        print(f'Received: {data.decode()!r}')
        if data.decode() == "pong\n":
            self.queue.put(("success", "Connected!"))
            self.queue.put(("switch_tab", "mp_server"))
            await self.listener()
        else:
            self.handle_error("Failed server handshake")

    async def resp(self, message):
        self.writer.write(message.encode())
        await self.writer.drain()
        print("sent: "+message)

    async def listener(self):
        while not self.loop.is_closed():
            data = await self.reader.readline()
            message = data.decode()[:-1]
            if not message:
                await asyncio.sleep(.01)
                continue
            print("got: "+message)
            if message.startswith("player"):
                # server requests player info and sets room name
                self.room = message.split(" ")[1]
                await self.resp(json.dumps({
                    "name": self.username,
                    "bot": self.bot,
                    "tile": self.tile
                }))
                self.queue.put(("switch_tab", "mp_room"))
            elif message.startswith("map"):
                # server sets current map
                try:
                    self.board.load(json.loads(message[4:]))
                    await self.resp("ok")
                except Exception as e:
                    print(e)
                    self.handle_error("Failed to load map")
            elif message.startswith("state"):
                try:
                    data = json.loads(message[6:])
                    self.state = data
                    self.board.update(data["grid"], data["players"])
                    await self.resp("ok")
                except Exception as e:
                    traceback.print_exc()
                    self.handle_error("Failed to update state")
            elif message.startswith("action"):
                try:
                    check = Game.check_against_state(self.state)
                    action = self.script(check, self.state["x"], self.state["y"])
                    await self.resp(json.dumps({"action": action}))
                except Exception as e:
                    traceback.print_exc()
                    self.handle_error("Failed to act: "+str(e))
            elif message.startswith("rooms"):
                rooms = json.loads(message[6:])
                for room in rooms:
                    print("room: "+room)
                    self.queue.put(("add_room", room))
            elif message == "game_over":
                self.board.label["text"] += "\n\nGAME OVER!"
                await self.resp("ok")
            elif message == "200":
                self.queue.put(("success", "server: ok"))
            elif message == "400":
                self.queue.put(("error", "server: bad request"))
            elif message == "404":
                self.queue.put(("error", "server: not found"))
            else:
                self.queue.put(("error", "unhandled server message"))
        print("mp listener stoped")

    def handle_error(self, message):
        self.queue.put(("error", message))

    async def join(self, name):
        try:
            if self.bot in sys.modules:
                 reload(sys.modules[self.bot])
            self.script = import_module(self.bot).script
        except:
            raise Exception(f"Failed to load bot: {bot}")
        command = "connect" + (" " + name if not name is None else "")
        self.writer.write(command.encode())
        await self.writer.drain()

    async def update_rooms(self):
        await self.resp("rooms")

    async def start_game(self):
        await self.resp("start "+self.room)

    ############################## interface ########################################

    def check_rooms(self):
        asyncio.run_coroutine_threadsafe(self.update_rooms(), self.loop)

    def join_room(self, name, player_bot, player_tile):
        self.bot = player_bot
        self.tile = player_tile
        asyncio.run_coroutine_threadsafe(self.join(name), self.loop)

    def play(self):
        asyncio.run_coroutine_threadsafe(self.start_game(), self.loop)

    def disconnect(self):
        if not self.loop.is_closed():
            print("disconnecting mp")
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
