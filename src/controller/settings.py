import os

from pathlib import Path

PLOTTER_PATH = os.path.join(Path(__file__).parent.parent, 'boot-plotter.sh')

if not os.path.exists(PLOTTER_PATH):
    raise FileNotFoundError('File %r not found' % PLOTTER_PATH)

PLOTTER_RUN_CMD = f'sh {PLOTTER_PATH}'
MAX_PARALLEL_PROCESSES = 3

# Command listener
LISTENER_ADDR = ('localhost', 8888)
BUF_SIZE = 1024
