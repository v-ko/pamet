# from misli import misli
# from misli.objects.base_object import BaseObject


# class PageComponent(BaseObject):
#     def __init__(self, page_id):
#         BaseObject.__init__(
#             self,
#             obj_type='PageComponent',
#             _page_id=page_id)

#         self._children = []
#         for note in self.page().notes():
#             NoteComponentClass = misli.components_lib.get(note.obj_type)
#             self._children.append(NoteComponentClass(page_id, note.id))

#         misli.add_component(self)

#     def page(self):
#         page = misli.page(self._page_id)
#         if not page:
#             breakpoint()
#         return page

#     def set_state(self, new_state):
#         raise NotImplementedError
