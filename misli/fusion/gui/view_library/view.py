from __future__ import annotations

import fusion
from .view_state import ViewState

log = fusion.get_logger(__name__)


class View:
    """This base View class should be inherited by all view implementations in
    a Misli app. It registers every instance in fusion.gui on class construction
     and provides access to a copy of the last applied view model via
     displayed_model(). There's also convenience methods to retrieve the child
     views.
     You can check out the developer documentation for the GUI architecture
     of Misli based apps, but overall we have a tree of views, where each one
     has a view model. View models get updated only via fusion.update_view_model
      and those updates get rendered asynchronously (i.e. if a user action
      changes several views - those changes will be cached and then pushed
      as a batch of updates to the Views).
      Each view that wants to receive updates should implement the
      handle_model_update(self, previous_state, new_model) method. And if the view
      manages it's children it will implement the handle_child_changes method,
       which is invoked by fusion.gui on each relevant view update with three
    arguments: children_added, chidren_removed and children_updated.
    """
    def __init__(self,
                 initial_state: ViewState = None):
        """Registers the View instance in fusion.gui, so that model and child
        updates are received accordingly.

        Args:
            parent (str): The parent id. Can be none if this view is a root
            initial_state (Entity): The view model should be an Entity subclass
        """
        if not initial_state:
            initial_state = ViewState()
        self._view_id = initial_state.view_id

    def __repr__(self):
        return '<%s view_id=%s>' % (type(self).__name__, self.view_id)

    @property
    def view_id(self):
        return self._view_id

    def state(self) -> ViewState:
        if fusion.gui.view_state_exists(self._view_id):
            self_state = fusion.gui.view_state(self._view_id)
        else:
            self_state = fusion.gui.get_state_backup(self._view_id)
        return self_state
