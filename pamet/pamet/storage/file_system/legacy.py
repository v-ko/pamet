import json

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from misli import entity_library

from misli.basic_classes import Point2D
from misli.helpers import get_new_id
from misli.logging import get_logger
from pamet.model import Page
from pamet.model.arrow import Arrow
from pamet.model.image_note import ImageNote
from pamet.model.script_note import ScriptNote
from pamet.model.text_note import TextNote

log = get_logger(__name__)

TIME_FORMAT = '%d.%m.%Y %H:%M:%S'
ONE_V3_COORD_UNIT_TO_V4 = 20

INTERNAL_ANCHOR_PREFIX = 'this_note_points_to:'
EXTERNAL_ANCHOR_PREFIX = 'define_web_page_note:'
IMAGE_NOTE_PREFIX = 'define_picture_note:'
SYSTEM_CALL_NOTE_PREFIX = 'define_system_call_note:'

