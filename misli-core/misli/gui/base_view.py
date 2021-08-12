from __future__ import annotations
from typing import Union

from misli.helpers import get_new_id
from misli import Entity, gui
from misli import get_logger
log = get_logger(__name__)


class View:
    """This base View class should be inherited by all view implementations in
    a Misli app. It registers every instance in misli.gui on class construction
     and provides access to a copy of the last applied view model via
     displayed_model(). There's also convenience methods to retrieve the child
     views.
     You can check out the developer documentation for the GUI architecture
     of Misli based apps, but overall we have a tree of views, where each one
     has a view model. View models get updated only via misli.update_view_model
      and those updates get rendered asynchronously (i.e. if a user action
      changes several views - those changes will be cached and then pushed
      as a batch of updates to the Views).
      Each view that wants to receive updates should implement the
      handle_model_update(self, old_model, new_model) method. And if the view
      manages it's children it will implement the handle_child_changes method,
       which is invoked by misli.gui on each relevant view update with three
    arguments: children_added, chidren_removed and children_updated.
    """
    def __init__(self, parent_id: Union[str, None], initial_model: Entity):
        """Registers the View instance in misli.gui, so that model and child
        updates are received accordingly.

        Args:
            parent_id (str): The parent id. Can be none if this view is a root
            initial_model (Entity): The view model should be an Entity subclass
             and
        """
        self._id = get_new_id()  # Generate the ViewModel.id(==View.id)
        initial_model.id = self.id
        self.parent_id = parent_id

        gui.add_view(self, initial_model)

    def __repr__(self):
        return '<%s id=%s>' % (type(self).__name__, self.id)

    @property
    def id(self):
        return self._id

    @property
    def displayed_model(self):
        model = gui.displayed_view_model(self.id)
        if not model or model.id != self.id:
            raise Exception('Could not retrieve view model for view %s' % self)
        return model

    def handle_model_update(self, old_model, new_model):
        pass

    def handle_child_changes(
            self,
            children_added: list,
            children_removed: list,
            children_updated: list):
        pass

    def child(self, child_id: str):
        return gui.view(child_id)

    def get_children(self):
        return gui.view_children(self.id)
