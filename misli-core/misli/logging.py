import logging
import threading
import functools
from typing import Callable
from collections import defaultdict

from misli.constants import LOGGING_LEVEL


class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


function_call_stack_per_thread = defaultdict(list)
logging.basicConfig(level=LOGGING_LEVEL)


def get_trace_decorator(logger_name: str):
    def trace_decorator(func: Callable):
        # Wrap the function only at DEBUG level
        if LOGGING_LEVEL != logging.DEBUG:
            return func

        name = '.'.join([logger_name, func.__name__])

        # Set color to the func name to have it stand out
        name_str = '%s.%s%s%s' % (
            logger_name, BColors.OKBLUE, func.__name__, BColors.ENDC)
        log = logging.getLogger('TRACE: ')

        @functools.wraps(func)
        def wrapper_func(*args, **kwargs):
            # Keep separate function stacks per thread
            thread_id = threading.get_ident()
            function_call_stack_per_thread[thread_id].append(name)

            # Prep the log string
            stack_depth = len(function_call_stack_per_thread[thread_id])
            indent = ' ' * 4 * (stack_depth - 1)

            args_string = ', '.join([str(a) for a in args])
            kwargs_string = ', '.join(['%s=%s' % (k, v)
                                      for k, v in kwargs.items()])

            log.debug('%sCALL: %s ARGS=*(%s) KWARGS=**{%s}' %
                      (indent, name_str, args_string, kwargs_string),
                      extra={'markup': True})

            result = func(*args, **kwargs)

            popped_name = function_call_stack_per_thread[thread_id].pop()
            if popped_name != name:
                raise Exception('Stack continuity error')

            log.debug('%sEND: %s RETURNED=%s' % (indent, name_str, result))

            return result

        return wrapper_func
    return trace_decorator


class Logger:
    def __init__(self, name: str):
        self.py_logger = logging.getLogger(name)
        self.traced = get_trace_decorator(name)

    def critical(self, *args, **kwargs):
        self.py_logger.critical(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.py_logger.error(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self.py_logger.warning(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.py_logger.info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self.py_logger.debug(*args, **kwargs)


def get_logger(name: str) -> Logger:
    """Get a logger with the given name. This is the preferred way of logging
    for apps using Misli.

    Normally you would provide the file __name__ as the logger name. The logger
     has a trace decorator that reports the calls of decorated functions as
    a stack in order to have a visually distinct output while debugging.
    Otherwise the Logger class is mostly a wrapper around the standard python
    logging module.

    For example:
        from misli import get_logger

        log = get_logger(__name__)
        log.info('Got logger')

        @log.traced
        def traced_func(foo):
            if not foo:
                log.error('foo is empty')
            return True
    """
    return Logger(name)
