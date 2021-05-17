import enum
import socket
import typing
import datetime
import collections

from plotting import logger

logger.__setattr__('name', __name__)


class Event(str, enum.Enum):
    STOP_SPAWN = 'STOP_SPAWN'

    @classmethod
    def values(cls):
        return list(cls)


class EventStatus(str, enum.Enum):
    COMPLETED = 'COMPLETED'
    IN_QUEUE = 'IN_QUEUE'


class EventQueue:
    def __init__(self):
        self._queue = collections.deque()

    def __repr__(self):
        return repr(self.queue)

    @property
    def queue(self):
        return self._queue

    @property
    def size(self):
        return len(self.queue)

    def put(self, value: dict):
        self.queue.append(value)

    def get(self):
        if self.size != 0:
            self.queue.popleft()


class ServerSocket:
    socket: socket.socket

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._init()

    def _init(self) -> None:
        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        self.socket.bind(
            (self.host, self.port)
        )
        logger.info(
            'Bind address %s:%s' % (self.host, self.port)
        )

    def accept_connections(self) -> 'ClientSocket':
        self.socket.listen()
        return ClientSocket(*self.socket.accept())

    def close(self) -> None:
        self.socket.close()


class ClientSocket:
    BUF_SIZE = 1024

    def __init__(self, _socket: socket.socket, addr: typing.Any):
        self.socket = _socket
        self.addr = addr

    def receive(self) -> bytes:
        return self.socket.recv(self.BUF_SIZE)

    def send(self, data: bytes) -> None:
        self.socket.send(data)

    def close(self) -> None:
        self.socket.close()


class EventListener:
    queue: EventQueue
    server_socket: ServerSocket
    client_socket: ClientSocket

    def __init__(self, host: str, port: int):
        self.is_accepts = False
        self.host = host
        self.port = port
        self._init()

    def _init(self) -> None:
        self.queue = EventQueue()
        self.server_socket = ServerSocket(self.host, self.port)
        self.client_socket = self.server_socket.accept_connections()
        self.is_accepts = True

    def _receive_and_handle_events(self) -> None:
        event = self.client_socket.receive()
        event = event.decode()
        if not event:
            return
        if event not in Event.values():
            self.client_socket.send(b'Unknown event')
            return
        self.queue.put({
            'date': datetime.datetime.now().isoformat(),
            'event': event,
            'status': EventStatus.IN_QUEUE
        })

    def listen(self) -> None:
        try:
            self._run_event_loop()
        except Exception as err:
            logger.error(err)
        except KeyboardInterrupt:
            logger.info('Close client socket')
            self.is_accepts = False
        self.close()

    def _run_event_loop(self) -> None:
        while self.is_accepts:
            self._receive_and_handle_events()

    def close(self) -> None:
        self.is_accepts = False
        self.client_socket.close()
        self.server_socket.close()


if __name__ == '__main__':
    el = EventListener('localhost', 8888)
    el.listen()
