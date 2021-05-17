import sys
import time
import enum
import typing
import logging
import threading
import subprocess

from plotting import settings

logging.basicConfig(
    format='%(name)s | %(levelname)s | %(asctime)s | %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class Color:
    GREEN = '\x1b[32;1m{0}\x1b[0m'
    RED = '\x1b[31;1m{0}\x1b[0m'
    YELLOW = '\x1b[33;1m{0}\x1b[0m'


class ProcessException(Exception):
    pass


class PoolException(Exception):
    pass


class PoolOverflowingException(PoolException):
    pass


class PlottingPhase(bytes, enum.Enum):
    FIRST = b'STARTING PHASE 1/4'
    SECOND = b'STARTING PHASE 2/4'
    THIRD = b'STARTING PHASE 3/4'
    FOUR = b'STARTING PHASE 4/4'


class ProgressStatus:
    _current: PlottingPhase

    def __init__(self):
        self._current = PlottingPhase.FIRST

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value):
        self._current = value


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
        self.status = ProgressStatus()

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
        return cls.running_total() < cls.max_parallel_processes

    @classmethod
    def running_total(cls) -> int:
        return len(cls.running)

    @classmethod
    def awaiting_total(cls) -> int:
        return len(cls.awaiting)

    @classmethod
    def running_phases(cls):
        return {
            proc.pid: proc.status.current.decode()
            for proc in cls.running
        }

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
        attrs['_pool'] = ProcessPool()
        return super().__new__(mcs, name, bases, attrs)


class ProcessController(metaclass=ControllerMeta):
    _pool: ProcessPool

    def __init__(self):
        self._init_pool()

    def _init_pool(self) -> None:
        self.pool.clear()
        self.pool.add(Process(settings.CMD))

    @property
    def pool(self):
        return self._pool

    def killall(self) -> None:
        for process in self.pool.running:
            process.kill()
            logger.info(f'{Color.RED.format("Kill process:")} {process.pid}')

    def spawn_available(self) -> bool:
        if self.pool.awaiting:
            if not self.pool.running:
                return True
            if self.pool.running and self.pool.running_is_available():
                in_allowed_phases = [
                    True if proc.status.current in {
                        PlottingPhase.SECOND,
                        PlottingPhase.THIRD,
                        PlottingPhase.FOUR
                    }
                    else False
                    for proc in self.pool.running
                ]
                if all(in_allowed_phases):
                    return True
                return False
        return False

    def spawn(self):
        awaiting = self.pool.awaiting.pop()
        awaiting.run()

        running, awaiting = awaiting, Process(settings.CMD)

        thread = threading.Thread(
            target=check_phase, args=(running, self.pool)
        )
        thread.start()

        self.pool.add(running)
        self.pool.add(awaiting)

        logger.info(
            f'{Color.GREEN.format("Run PID:")} {running.pid} '
            f'{Color.GREEN.format("Running total:")} {self.pool.running_total()} '
            f'{Color.GREEN.format("Awaiting total:")} {self.pool.awaiting_total()} '
            f'{Color.GREEN.format("Running phases:")} {self.pool.running_phases()} '
        )

    def spawn_processes(self) -> None:
        while True:
            if not self.spawn_available():
                continue
            self.spawn()


def check_phase(process: Process, pool: ProcessPool) -> None:
    def parse_phase_and_update_process_status() -> None:
        line = stdout.readline().upper()
        status = None
        if PlottingPhase.SECOND in line:
            status = PlottingPhase.SECOND
        elif PlottingPhase.THIRD in line:
            status = PlottingPhase.THIRD
        elif PlottingPhase.FOUR in line:
            status = PlottingPhase.FOUR
        if not status:
            return
        process.status.current = status
        logger.info(
            f"{Color.YELLOW.format('PID:')} {process.pid} "
            f"{Color.YELLOW.format('Run phase:')} {status.decode()}"
        )

    stdout = process.stdout
    while True:
        code = process.instance.poll()
        if code is not None:
            break
        parse_phase_and_update_process_status()

    if code == 0:
        logger.info(
            f'{Color.GREEN.format("Finished process:")} {process.pid} '
            f'{Color.GREEN.format("Status code:")} {code} '
            f'{Color.GREEN.format("Total time:")} {(time.time() - process.start_time) / 3600} hours')
    else:
        logger.error(
            f'{Color.RED.format("ERROR:")} {process.pid} '
            f'{Color.RED.format("Status code:")} {code} ')
    pool.running.remove(process)


def main():
    controller = ProcessController()
    try:
        controller.spawn_processes()
    except KeyboardInterrupt:
        controller.killall()
        sys.exit(0)
