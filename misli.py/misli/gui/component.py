from misli.objects.base_object import BaseObject


class Component(BaseObject):
    def __init__(self, parent_id):
        BaseObject.__init__(
            self,
            obj_type='Component',
            _parent_id=parent_id)

    def state_from_base_object(self, base_object):
        pass

    # def note(self):
    #     note = misli.page(self._parent_id).note(self._note_id)
    #     return note

    # def set_state(self, new_state):
    #     raise NotImplementedError
