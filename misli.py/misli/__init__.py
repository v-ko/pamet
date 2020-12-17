import logging


def get_logger(name):
    log = logging.getLogger(__name__)
    return log


from .misli import *

ORGANISATION_NAME = 'p10'
DESKTOP_APP_NAME = 'misli'
DESKTOP_APP_VERSION = '4.0.0'
