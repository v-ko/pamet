from misli.objects.base_object import BaseObject


class Note(BaseObject):
    def __init__(self, **kwargs):
        obj_type = kwargs.pop('obj_type', 'Note')
        BaseObject.__init__(self, obj_type=obj_type, **kwargs)

    def rect(self):
        return self.x, self.y, self.width, self.height
