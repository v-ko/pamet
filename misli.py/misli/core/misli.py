from collections import defaultdict
from misli.objects import Page, Note
from misli import logging
log = logging.getLogger(__name__)


class Misli():
    def __init__(self, state_manager=None):
        self._repo = None
        self._components_lib = None
        self._components = {}
        self._components_for_update = set()
        self._pages_for_saving = set()
        self._components_for_base_object = defaultdict(list)
        self._base_object_for_component = {}
        self._desktop_app = None

    def desktop_app(self):
        if not self._desktop_app:
            raise Exception('No desktop_app object set')

        return self._desktop_app

    def set_desktop_app(self, app):
        self._desktop_app = app
        self._add_component(app)

    def create_component(self, obj_class, parent_id):
        ComponentClass = self.components_lib.get(obj_class)
        component = ComponentClass(parent_id)
        self._add_component(component)

        if parent_id:
            self.component(parent_id).add_child(component.id)

        return component

    def remove_component(self, component_id):
        component = self.component(component_id)

        if component.parent_id:
            parent = self.component(component.parent_id)
            parent.remove_child(component_id)

        # Deregister component
        if component in self._base_object_for_component:
            base_object = self._base_object_for_component[component]
            self._components_for_base_object[base_object].remove(component)
            del self._base_object_for_component[component]

        del component

    def create_component_for_note(
            self, page_id, note_id, obj_class, parent_id):

        component = self.create_component(obj_class, parent_id)
        note = self.page(page_id).note(note_id)
        component.set_props(**note.state())

        self.register_component_with_base_object(component, note)
        return component

    def create_components_for_page(self, page_id, parent_id):
        page = self.page(page_id)
        page_component = self.create_component(
            obj_class=page.obj_class, parent_id=parent_id)

        page_component.set_props(**page.state())
        self.register_component_with_base_object(page_component, page)

        for note in page.notes():
            self.create_component_for_note(
                page.id, note.id, note.obj_class, page_component.id)

        return page_component

    def _add_component(self, component):
        self._components[component.id] = component

    def register_component_with_base_object(self, component, base_object):
        self._components_for_base_object[base_object.id].append(component)
        self._base_object_for_component[component.id] = base_object

    def base_object_for_component(self, component_id):
        return self._base_object_for_component[component_id]

    def components_for_base_object(self, base_object_id):
        return self._components_for_base_object[base_object_id]

    def component(self, id):
        return self._components[id]

    def set_repo(self, repo):
        log.info('Setting repo to %s' % repo.path)
        self._repo = repo

    @property
    def components_lib(self):
        return self._components_lib

    def set_components_lib(self, lib):
        self._components_lib = lib

    def page(self, page_id):
        return self._repo.page(page_id)

    def pages(self):
        return self._repo.pages()

    def call_delayed(self, callback, delay):
        raise NotImplementedError()

    def update_component(self, component_id: int):
        self._components_for_update.add(component_id)
        self.call_delayed(self._update_components, 0)

    def _update_components(self):
        for component_id in self._components_for_update:
            self.component(component_id).update()

        self._components_for_update.clear()

    def _save_page(self, page):
        self._pages_for_saving.add(page)
        self.call_delayed(self._save_pages, 0)

    def _save_pages(self):
        for page in self._pages_for_saving:
            self._repo.save_page(page)

    def update_page(self, page_id, **page_state):
        page = self.page(page_id)

        if page_state:
            page.set_state(**page_state)
        self._save_page(page)

        page_components = self.components_for_base_object(page_id)
        for pc in page_components:
            pc.set_props(**page.state())
            self.update_component(pc.id)

        # push change?

    def create_page(self, id, obj_class, **page_state):
        if not page_state:
            page_state = {}
        page_state['id'] = id
        page_state['obj_class'] = obj_class

        page = Page(**page_state)
        self._repo.load_page(page)
        self._repo.save_page(page)
        return page

    def delete_page(self, page_id):
        page = self.page(page_id)
        self._repo.delete_page(page)

    def update_note(self, note_id, page_id, **note_state):
        page = self.page(page_id)
        note = page.note(note_id)

        note.set_state(**note_state)
        self._save_page(page)

        note_components = self.components_for_base_object(note_id)
        for nc in note_components:
            nc.set_props(**note.state())

            # Hacky cache clearing
            nc.data = {}

            self.update_component(nc.id)

        # push change?

    def create_note(self, page_id, **note_state):
        page = self.page(page_id)
        note = Note(**note_state)

        page.add_note(note)

        self._repo.save_page(page)

        return note

    def delete_note(self, note_id, page_id):
        page = self.page(page_id)
        note = page.note(note_id)

        page.remove_note(note)
        self.save_page(page)
