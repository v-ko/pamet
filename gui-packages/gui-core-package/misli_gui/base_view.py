from __future__ import annotations

from misli.helpers import get_new_id
from misli import Entity
import misli_gui
from misli import get_logger
log = get_logger(__name__)


class View:
    def __init__(self, parent_id: str, initial_model: Entity):
        self._id = get_new_id()  # Generate the ViewModel.id(==View.id)
        initial_model.id = self.id
        self.parent_id = parent_id

        misli_gui.add_view(self, initial_model)

    def __repr__(self):
        return '<%s id=%s>' % (type(self).__name__, self.id)

    @property
    def id(self):
        return self._id

    @property
    def displayed_model(self):
        model = misli_gui.displayed_view_model(self.id)
        if not model or model.id != self.id:
            raise Exception('Could not retrieve view model for view %s' % self)
        return model

    # def update_cached_model(self, new_model):
    #     self.__displayed_model = new_model

    def handle_model_update(self, old_model, new_model):
        pass

    def handle_child_changes(
            self, children_added, children_removed, children_updated):
        pass

    def child(self, child_id: str):
        return misli_gui.view(child_id)

    def get_children(self):
        return misli_gui.view_children(self.id)
