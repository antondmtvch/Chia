import os

PLOTTER_RUN_CMD = 'sh %s' % os.path.join(os.getcwd(), 'boot-plotter.sh')
MAX_PARALLEL_PROCESSES = 3

# Command listener
LISTENER_ADDR = ('localhost', 8888)
BUF_SIZE = 1024
