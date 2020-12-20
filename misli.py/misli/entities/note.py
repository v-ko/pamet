from misli import get_logger
from misli.entities.base_entity import BaseEntity
from misli.core.primitives import Point, Rectangle, Color
from misli.constants import DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH
from misli.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR
from misli.constants import MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT
from misli.constants import MAX_NOTE_WIDTH, MAX_NOTE_HEIGHT
from misli.constants import ALIGNMENT_GRID_UNIT
log = get_logger(__name__)


class Note(BaseEntity):
    def __init__(self, **state):
        id = state.pop('id', None)
        obj_type = state.pop('obj_type', 'Note')

        BaseEntity.__init__(self, id=id, obj_type=obj_type)

        self.obj_class = state.pop('obj_class', '')
        self.page_id = state.pop('page_id', '')
        self.x = state.pop('x', 0)
        self.y = state.pop('y', 0)
        self.width = state.pop('width', DEFAULT_NOTE_WIDTH)
        self.height = state.pop('height', DEFAULT_NOTE_HEIGHT)
        self.color = state.pop('color', DEFAULT_COLOR)
        self.background_color = state.pop('background_color', DEFAULT_BG_COLOR)
        self.text = state.pop('text', '')

        keys = ['page_id', 'x', 'y', 'width', 'height', 'background_color',
                'color', 'obj_class', 'text']
        self.add_state_keys(keys)
        self.set_state(**state)

        if state:
            log.warning('Unaccounted for state keys %s' % str(state.keys()))

    def rect(self):
        return Rectangle(self.x, self.y, self.width, self.height)

    def get_color(self):
        return Color(*self.color)

    def get_background_color(self):
        return Color(*self.background_color)

    def set_width(self, width):
        self.width = min(MAX_NOTE_WIDTH, max(width, MIN_NOTE_WIDTH))

    def set_height(self, height):
        self.height = min(MAX_NOTE_HEIGHT, max(height, MIN_NOTE_HEIGHT))

    def size(self):
        return Point(self.width, self.height)

    def set_size(self, new_size: Point):
        grid_unit = ALIGNMENT_GRID_UNIT
        self.set_width(round(new_size.x() / grid_unit) * grid_unit)
        self.set_height(round(new_size.y() / grid_unit) * grid_unit)
