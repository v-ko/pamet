import logging
import time
import random

logging.basicConfig(level=logging.INFO)


def get_logger(name):
    log = logging.getLogger(__name__)
    return log


def set_reproducible_ids(enabled):
    if enabled:
        random.seed(0)
    else:
        random.seed(time.time())


from .misli import *

ORGANISATION_NAME = 'p10'
DESKTOP_APP_NAME = 'misli'
DESKTOP_APP_VERSION = '4.0.0'
