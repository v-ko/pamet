from misli.objects.base_object import BaseObject
from misli.core.primitives import Rectangle


class Note(BaseObject):
    def __init__(self, **state):
        obj_type = state.pop('obj_type', 'Note')
        page_id = state.pop('page_id', '')
        BaseObject.__init__(self, obj_type=obj_type, page_id=page_id, **state)

    def rect(self):
        return Rectangle(self.x, self.y, self.width, self.height)
