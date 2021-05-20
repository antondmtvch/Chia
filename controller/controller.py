import sys
import time
import enum
import typing
import asyncio
import settings
import threading
import subprocess

from logger import logger, Color
from listener import CommandsListener, Command, CommandsQueue


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


class Process:
    def __init__(self, cmd: str):
        self._phase = None
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
        self._phase = PlottingPhase.FIRST

    @property
    def is_running(self):
        return hasattr(self, 'instance')

    @property
    def phase(self):
        return self._phase

    @phase.setter
    def phase(self, value):
        self._phase = value
        logger.info(
            f"{Color.YELLOW.format('PID:')} {self.pid} "
            f"{Color.YELLOW.format('Start phase:')} "
            f"{self.phase.decode()[-3::]} "
        )

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
            proc.pid: proc.phase.decode()
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
        self.queue = CommandsQueue()
        self.pause_spawn = False
        self._init()

    def _init(self) -> None:
        self.listener = CommandsListener(
            *settings.LISTENER_ADDR,
            queue=self.queue)
        self.loop = asyncio.get_event_loop()

        def start_listener():
            try:
                self.loop.run_until_complete(
                    self.listener.listen())
            except KeyboardInterrupt:
                self.loop.close()
                logger.info(
                    Color.GREEN.format('Down %s') % self.listener.__class__.__name__
                )

        t = threading.Thread(target=start_listener)
        t.start()
        time.sleep(2)

        self.pool.clear()
        self.pool.add(Process(settings.PLOTTER_RUN_CMD))

    @property
    def pool(self):
        return self._pool

    def killall(self) -> None:
        for process in self.pool.running:
            process.kill()
            logger.info(f'{Color.RED.format("Kill process:")} {process.pid}')

    def spawn_available(self) -> bool:
        if self.pause_spawn:
            return False
        if self.pool.awaiting:
            if not self.pool.running:
                return True
            if self.pool.running and self.pool.running_is_available():
                in_allowed_phases = [
                    True if proc.phase in {
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

        running, awaiting = awaiting, Process(settings.PLOTTER_RUN_CMD)

        thread = threading.Thread(
            target=control_process_phase,
            args=(running, self.pool)
        )
        thread.start()

        self.pool.add(running)
        self.pool.add(awaiting)

        logger.info(
            f'{Color.GREEN.format("Run PID:")} {running.pid} '
            f'{Color.GREEN.format("Running total:")} {self.pool.running_total()} '
            f'{Color.GREEN.format("Awaiting total:")} {self.pool.awaiting_total()} '
            f'{Color.GREEN.format("Running pool:")} {self.pool.running_phases()}'
        )

    def spawn_processes(self) -> None:
        while True:
            self.handle_user_commands()
            if not self.spawn_available():
                continue
            self.spawn()

    def handle_user_commands(self):
        while self.queue.size != 0:
            command = self.queue.get().get('command')
            if command == Command.PAUSE:
                self.pause_spawn = True
            if command == Command.RESUME:
                self.pause_spawn = False
            logger.info(
                f"{Color.BLUE.format('@@@ Handle user command:')} {command}"
            )


def control_process_phase(process: Process, pool: ProcessPool) -> None:
    def parse_phase_and_update_process() -> None:
        line = stdout.readline().upper()
        phase = None
        if PlottingPhase.SECOND in line:
            phase = PlottingPhase.SECOND
        elif PlottingPhase.THIRD in line:
            phase = PlottingPhase.THIRD
        elif PlottingPhase.FOUR in line:
            phase = PlottingPhase.FOUR
        if not phase:
            return
        process.phase = phase
        logger.info(
            f'{Color.YELLOW.format("Running pool:")} {pool.running_phases()}'
        )

    stdout = process.stdout
    while True:
        code = process.instance.poll()
        if code is not None:
            break
        parse_phase_and_update_process()

    if code == 0:
        logger.info(
            f'{Color.GREEN.format("Finished PID:")} {process.pid} '
            f'{Color.GREEN.format("Status code:")} {code} '
            f'{Color.GREEN.format("Total time:")} {(time.time() - process.start_time) / 3600} hours')
    else:
        logger.error(
            f'{Color.RED.format("Failed PID: %s")} {process.pid} '
            f'{Color.RED.format("Status code:")} {code} ')
    pool.running.remove(process)


def run():
    controller = ProcessController()
    try:
        controller.spawn_processes()
    except KeyboardInterrupt:
        controller.killall()
        sys.exit(0)
