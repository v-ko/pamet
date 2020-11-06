import logging


def set_level(level):
    logging.basicConfig(level=level)


def get_logger(name):
    return logging.getLogger(name)


# class Logger():
#     def __init__(self, name,):

