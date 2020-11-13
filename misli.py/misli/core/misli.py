from collections import defaultdict


class Misli():
    def __init__(self, state_manager=None):
        self._repo = None
        self._components_lib = None
        self._components = {}
        self._components_for_update = set()
        self._components_for_base_object = defaultdict(list)
        self._base_object_for_component = {}

    def _create_component(self, base_object):
        ComponentClass = self.components_lib.get(base_object.obj_type)
        component = ComponentClass(base_object.id)
        component.set_props(**base_object.state())
        self.add_component(component, base_object)
        return component

    def init_components_for_page(self, page_id):
        page = self.page(page_id)
        component = self._create_component(page)

        for note in page.notes():
            child_comp = self._create_component(note)
            component.add_child(child_comp)

        return component

    def add_component(self, component, base_object):
        self._components[component.id] = component
        self._components_for_base_object[base_object.id].append(component)
        self._base_object_for_component[component.id] = base_object

    def base_object_for_component(self, component_id):
        return self._base_object_for_component[component_id]

    def component(self, id):
        return self._components[id]

    def set_repo(self, repo):
        self._repo = repo

    @property
    def components_lib(self):
        return self._components_lib

    def set_components_lib(self, lib):
        self._components_lib = lib

    def page(self, page_id):
        return self._repo.page(page_id)

    def call_delayed(self, callback, delay):
        raise NotImplementedError()

    def update_component(self, component_id: int):
        self._components_for_update.add(component_id)
        self.call_delayed(self._update_components, 0)

    def _update_components(self):
        for component_id in self._components_for_update:
            self.component(component_id).update()

        self._components_for_update.clear()

    # def find_one(self, **kwargs):
    #     for res in self.find(**kwargs):
    #         return res

    #     return None

    # def find_page(self, **kwargs):
    #     kwargs['obj_type'] = 'Page'
    #     return self.find_one(**kwargs)

# init
        # if not state_manager:
        #     state_manager = StateManager()

        # self._state_manager = state_manager

    # def load(self, state, action_type):
    #     self._state_manager.load(state)
    #     log.info('[Milsi][load]', action_type)

    # def update(self, old_state, new_state, action_type):
    #     self.states[old_state._id].update(new_state)
    #     log.info('[Milsi][update]', action_type)

    # def unload(self, state, action_type):
    #     self._state_manager.unload(state)
    #     log.info('[Milsi][unload]', action_type)

    # def update_many(self, state_updates, action_type):
    #     for state_update in state_updates:
    #         self.states[state_update._id].update(state_update)

    #     log.info('[Milsi][update]', action_type)

    # def find(self, **kwargs):
    #     return self._state_manager.find(**kwargs)
