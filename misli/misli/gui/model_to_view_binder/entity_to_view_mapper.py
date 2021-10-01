from collections import defaultdict
from misli import gui


class EntityToViewMapping:
    """A simple class to map an entity to multiple views in order to
    efficiently invoke view updates when an entity gets updated.
    """
    def __init__(self):
        self._view_ids_by_entity_id = defaultdict(list)
        self._entity_id_by_view_id = {}

    def map(self, entity_gid, view_id):
        self._view_ids_by_entity_id[entity_gid].append(view_id)
        self._entity_id_by_view_id[view_id] = entity_gid

    def unmap(self, entity_gid, view_id):
        if view_id not in self._entity_id_by_view_id:
            raise Exception('Cannot unregister component that is not '
                            'registered ' % view_id)

        self._view_ids_by_entity_id[entity_gid].remove(view_id)
        del self._entity_id_by_view_id[view_id]

    def views_for(self, entity_gid):
        component_ids = self._view_ids_by_entity_id[entity_gid]

        components = []
        for component_id in component_ids:
            component = gui.view(component_id)
            if not component:
                self.unmap(entity_gid, component_id)
                continue

            components.append(component)
        return components
