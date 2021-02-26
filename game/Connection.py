import json
from Constants import *


class Connection:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def communicate(self, command, object=None, await_resp=True):
        message = command + ("" if object is None else (" " + json.dumps(object))) + "\n"
        self.writer.write(message.encode())
        await self.writer.drain()
        # print("sent: "+message)
        resp = await self.reader.read(CHUNK)
        resp = resp.decode()
        if not object is None and resp == "ok" or not await_resp:
            return True
        try:
            return json.loads(resp)
        except:
            await self.send_status("400")
            raise Exception("Failed to communicate: " + command)

    async def send_status(self, message):
        self.writer.write(message.encode() + b'\n')
        await self.writer.drain()

    def close(self):
        self.writer.close()
