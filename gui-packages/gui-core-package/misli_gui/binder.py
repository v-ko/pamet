from collections import defaultdict

import misli
import misli_gui
log = misli.get_logger(__name__)


class Binder:
    def __init__(self):
        # self.channel = channel

        self._component_ids_by_entity_id = defaultdict(list)
        self._entity_id_by_component_id = {}

        # misli.subscribe(channel, handler)

    @log.traced
    def map_component_to_entity(self, component, entity):
        self._component_ids_by_entity_id[entity.gid()].append(component.id)
        self._entity_id_by_component_id[component.id] = entity.gid()

    @log.traced
    def unmap_component_from_entity(self, component_id, entity_gid):
        if component_id not in self._entity_id_by_component_id:
            raise Exception('Cannot unregister component that is not '
                            'registered ' % component_id)

        self._component_ids_by_entity_id[entity_gid].remove(component_id)
        del self._entity_id_by_component_id[component_id]

    @log.traced
    def components_mapped_to_entity(self, entity_gid):
        component_ids = self._component_ids_by_entity_id[entity_gid]
        components = []
        for component_id in component_ids:
            component = misli_gui.component(component_id)
            if not component:
                self.unmap_component_from_entity(component_id, entity_gid)
                continue

            components.append(component)

        return components

    # def entity_gid_for_component(self, component_id):
    #     if component_id not in self._entity_id_by_component_id:
    #         return None
    #
    #     return self._entity_id_by_component_id[component_id]

    # def handle_changes(self, changes):
    #     raise NotImplementedError

    # def update_components_for_entity(self, entity, new_state):
    #     for component_id in self.components_mapped_to_entity(entity.id):
    #         component = get_component(component_id)

    #         if not component:
    #             log.critical('Could not find component with id %s' %
    #                          component_id)
    #             raise Exception

    #     self.handle_changes()
