from misli import misli
# from misli.objects.base_object import BaseObject


class Component():
    def __init__(self, base_object_id):

        misli.add_component(self)
        self._children = []

    # def diff_children(self, children_ids):
    #     current_ids = set(map(lambda c: c.id, self._children))
    #     new_ids = set(children_ids)

    #     children_added = list(new_ids - current_ids)
    #     children_removed = list(current_ids - new_ids)

    #     return children_added, children_removed
