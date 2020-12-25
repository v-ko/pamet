import time
import random
import logging
from .misli_logging import set_level, get_logger


def set_reproducible_ids(enabled):
    if enabled:
        random.seed(0)
    else:
        random.seed(time.time())


set_level(logging.DEBUG)


from .misli import *

ORGANISATION_NAME = 'p10'
DESKTOP_APP_NAME = 'misli'
DESKTOP_APP_VERSION = '4.0.0'
