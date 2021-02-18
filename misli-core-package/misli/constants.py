import os
from misli_debug import LoggingLevels

log_lvl_name = os.environ.get('MISLI_LOGGING_LEVEL', LoggingLevels.ERROR.name)
LOGGING_LEVEL = LoggingLevels[log_lvl_name].value
