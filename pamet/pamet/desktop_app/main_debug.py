from misli_debug import set_logging_level, LoggingLevels
set_logging_level(LoggingLevels.DEBUG)
print('at logging level')
import os
print(os.environ['MISLI_LOGGING_LEVEL'])
from pamet.desktop_app.main import main
