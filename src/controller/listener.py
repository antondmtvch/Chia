import enum
import typing
import asyncio
import datetime
import multiprocessing

from src.controller.logger import logger, Color


class Command(str, enum.Enum):
    PAUSE = 'PAUSE'
    RESUME = 'RESUME'

    @classmethod
    def values(cls):
        return list(cls)


class CommandsQueue:
    def __init__(self):
        self._queue = multiprocessing.Queue()

    @property
    def queue(self):
        return self._queue

    @property
    def size(self):
        return self.queue.qsize()

    def put(self, value: typing.Dict[str, typing.Any]):
        self.queue.put(value)

    def get(self):
        if self.size != 0:
            return self.queue.get()


class CommandsListener:
    def __init__(self, host: str, port: int,
                 queue: CommandsQueue):
        self.queue = queue
        self.host = host
        self.port = port

    async def listen(self):
        server = await asyncio.start_server(
            self._handle,
            self.host,
            self.port
        )
        logger.info(
            Color.GREEN.format('%s listen on %s:%s') % (
                self.__class__.__name__,
                self.host,
                self.port
            )
        )
        await server.serve_forever()

    async def _handle(self, reader, writer):
        while True:
            command = await self._receive(reader)
            if not command:
                continue
            if command not in Command.values():
                writer.write(b'Unknown command')
                continue
            self.queue.put({
                'date': datetime.datetime.utcnow().isoformat(),
                'command': command
            })
            writer.write(b'Command put in queue')
            logger.info(
                f'{Color.BLUE.format("@@@ Received command:")} %s' % command
            )

    @staticmethod
    async def _receive(reader) -> typing.Optional[str]:
        command = await reader.read(1024)
        return command.decode().upper().strip()
