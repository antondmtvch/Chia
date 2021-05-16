import sys
import time
import typing
import logging
import threading
import subprocess
import multiprocessing as mp
import multiprocessing.queues as mpq

import settings

logging.basicConfig(
    format='%(name)s | %(levelname)s | %(asctime)s | %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class Color:
    GREEN = '\x1b[32;1m{0}\x1b[0m'
    RED = '\x1b[31;1m{0}\x1b[0m'


class ProcessException(Exception):
    pass


class PoolException(Exception):
    pass


class PoolOverflowingException(PoolException):
    pass


class StdoutQueue(mpq.Queue):
    def __init__(self, *args, **kwargs):
        ctx = mp.get_context()
        super().__init__(*args, **kwargs, ctx=ctx)

    def write(self, msg: bytes) -> None:
        self.put(msg)


class Process:
    def __init__(self, cmd: str):
        self.cmd = cmd

    def _init(self) -> None:
        self.start_time = time.time()
        self.instance = subprocess.Popen(
            self.cmd,
            shell=True,
            stdout=subprocess.PIPE,
        )
        self.stdout = self.instance.stdout
        self.pid = self.instance.pid

    @property
    def is_running(self):
        return hasattr(self, 'instance')

    def kill(self) -> None:
        if not self.is_running:
            raise ProcessException('Process is not running.')
        self.instance.kill()
        delattr(self, 'instance')

    def run(self) -> None:
        if self.is_running:
            raise ProcessException('Process is running.')
        self._init()


class PoolMeta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['running'] = []
        attrs['awaiting'] = []
        attrs['max_parallel_processes'] = settings.MAX_PARALLEL_PROCESSES
        return super().__new__(mcs, name, bases, attrs)


class ProcessPool(metaclass=PoolMeta):
    max_parallel_processes: int
    running: typing.List[Process]
    awaiting: typing.List[Process]

    @classmethod
    def running_is_available(cls) -> bool:
        return cls.running_count() < cls.max_parallel_processes

    @classmethod
    def running_count(cls) -> int:
        return len(cls.running)

    @classmethod
    def awaiting_count(cls) -> int:
        return len(cls.awaiting)

    @classmethod
    def add(cls, process: Process) -> None:
        if process.is_running:
            cls.running.append(process)
        else:
            cls.awaiting.append(process)

    @classmethod
    def clear(cls) -> None:
        for process in cls.running:
            process.kill()
        cls.running, cls.awaiting = [], []


class ControllerMeta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['_queue'] = StdoutQueue()
        attrs['_pool'] = ProcessPool()
        return super().__new__(mcs, name, bases, attrs)


class ProcessController(metaclass=ControllerMeta):
    _pool: ProcessPool
    _queue: StdoutQueue

    def __init__(self):
        self._init_pool()

    def _init_pool(self) -> None:
        self.pool.clear()
        self.pool.add(Process(settings.CMD))

    @property
    def queue(self):
        return self._queue

    @property
    def pool(self):
        return self._pool

    @property
    def running_is_available(self) -> bool:
        if self.pool.awaiting and not self.pool.running:
            return True
        if settings.TRIGGER_PHRASE in self.read_stdout().lower() \
                and self.pool.running_is_available():
            return True
        return False

    def killall(self) -> None:
        for process in self.pool.running:
            process.kill()
            logger.info(f'{Color.RED.format("Kill process:")} {process.pid}')

    def redirect_stdout(self, process: Process) -> int:
        while True:
            code = process.instance.poll()
            if code is not None:
                break
            self.queue.put(process.stdout.readline())
        process.kill()
        return code

    def await_complete(self, process: Process) -> None:
        if not process.is_running:
            raise ProcessException('Process is not running.')
        code = self.redirect_stdout(process)
        if code == 0:
            logger.info(
                f'{Color.GREEN.format("Finished process:")} {process.pid} '
                f'{Color.GREEN.format("Status code:")} {code} '
                f'{Color.GREEN.format("Total time:")} {(time.time() - process.start_time) / 360} hours')
        else:
            logger.error(
                f'{Color.RED.format("ERROR:")} {process.pid} '
                f'{Color.RED.format("Status code:")} {code} ')
        self.pool.running.remove(process)

    def spawn_processes(self) -> None:
        while True:
            if self.running_is_available:
                awaiting = self.pool.awaiting.pop()
                awaiting.run()

                running, awaiting = awaiting, Process(settings.CMD)

                thread = threading.Thread(
                    target=self.await_complete, args=(running,)
                )
                thread.start()

                self.pool.add(running)
                self.pool.add(awaiting)

                logger.info(
                    f'{Color.GREEN.format("Running process:")} {running.pid} '
                    f'{Color.GREEN.format("Running count:")} {self.pool.running_count()} '
                    f'{Color.GREEN.format("Awaiting count:")} {self.pool.awaiting_count()} '
                )

    def read_stdout(self) -> bytes:
        return self.queue.get()


def main():
    controller = ProcessController()
    try:
        controller.spawn_processes()
    except KeyboardInterrupt:
        controller.killall()
        sys.exit(0)
