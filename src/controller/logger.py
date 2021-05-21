import logging


class Color:
    GREEN = '\x1b[32;1m{0}\x1b[0m'
    RED = '\x1b[31;1m{0}\x1b[0m'
    YELLOW = '\x1b[33;1m{0}\x1b[0m'
    BLUE = '\033[1;34;1m{0}\033[0m'


def setup_logger():
    logging.basicConfig(
        format='%(name)s | pid: %(process)d | %(levelname)s | %(asctime)s | %(message)s',
        datefmt='%d-%b-%y %H:%M:%S',
        level=logging.INFO,
    )
    _logger = logging.getLogger('controller')
    return _logger


logger = setup_logger()
