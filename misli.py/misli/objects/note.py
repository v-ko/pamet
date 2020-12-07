from misli.objects.base_object import BaseObject
from misli.core.primitives import Rectangle, Color
from misli.constants import DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH
from misli.constants import DEFAULT_BG_COLOR, DEFAULT_COLOR


class Note(BaseObject):
    def __init__(self, **state):
        BaseObject.__init__(self)

        self.obj_type = state.pop('obj_type', 'Note')
        self.obj_class = state.pop('obj_class', '')
        self.page_id = state.pop('page_id', '')
        self.x = state.pop('x', 0)
        self.y = state.pop('y', 0)
        self.width = state.pop('width', DEFAULT_NOTE_WIDTH)
        self.height = state.pop('height', DEFAULT_NOTE_HEIGHT)
        self.color = state.pop('color', DEFAULT_COLOR)
        self.background_color = state.pop('background_color', DEFAULT_BG_COLOR)

        keys = ['page_id', 'x', 'y', 'width', 'height', 'background_color',
                'color', 'obj_class', 'text']
        self.add_state_keys(keys + list(state.keys()))
        self.set_state(**state)

    def rect(self):
        return Rectangle(self.x, self.y, self.width, self.height)

    def get_color(self):
        return Color(*self._color)

    def get_background_color(self):
        return Color(*self._background_color)
