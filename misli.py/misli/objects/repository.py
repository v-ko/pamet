from misli.objects.base_object import BaseObject


class Repository(BaseObject):
    def __init__(self):
        BaseObject.__init__(self, obj_type='Repository')

    def page(self, page_id):
        return NotImplementedError()
