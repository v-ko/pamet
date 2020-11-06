# from misli import log


class Misli():
    def __init__(self, state_manager=None):
        self._repo = None
        self._components_lib = None
        self._components = {}
        # StateManager.__init__(self)

    def add_component(self, component):
        self._components[component.id] = component

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
