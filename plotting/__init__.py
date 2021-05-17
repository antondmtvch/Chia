import logging

logging.basicConfig(
    format='%(name)s | %(levelname)s | %(asctime)s | %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
