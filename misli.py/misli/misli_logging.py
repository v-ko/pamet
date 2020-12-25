import logging
import threading
from collections import defaultdict

function_call_stack_per_thread = defaultdict(list)
logging_level = None


def set_level(level):
    global logging_level
    logging_level = level
    logging.basicConfig(level=logging_level)


def get_logger(name):
    return Logger(name)


class Logger:
    def __init__(self, name):
        self.py_logger = logging.getLogger(name)
        self.traced = self.get_trace_decorator(name)

    def get_trace_decorator(self, logger_name):
        def trace_decorator(func):
            # Wrap the function only if we're traceging
            if logging_level != logging.DEBUG:
                return func

            # Prep the wrapper
            name = '.'.join([logger_name, func.__name__])
            log = logging.getLogger('TRACE: ')

            def wrapper_func(*args, **kwargs):
                thread_id = threading.get_ident()
                function_call_stack_per_thread[thread_id].append(name)

                stack_depth = len(function_call_stack_per_thread[thread_id])
                indent = ' ' * 4 * (stack_depth - 1)

                args_string = ', '.join([str(a) for a in args])
                kwargs_string = ', '.join(['%s=%s' for k, v in kwargs.items()])
                log.debug('%sCALL: %s ARGS=*(%s) KWARGS=**{%s}' %
                          (indent, name, args_string, kwargs_string))

                result = func(*args, **kwargs)

                popped_name = function_call_stack_per_thread[thread_id].pop()
                if popped_name != name:
                    raise Exception('Stack continuity error')

                log.debug('%sEND: %s RETURNED=%s' % (indent, name, result))

                return result

            return wrapper_func
        return trace_decorator

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
