from __future__ import annotations
from typing import Union, List

import misli.gui
from misli import gui, get_logger
from misli.basic_classes import Point2D

from .view_state import ViewState

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
      handle_model_update(self, previous_state, new_model) method. And if the view
      manages it's children it will implement the handle_child_changes method,
       which is invoked by misli.gui on each relevant view update with three
    arguments: children_added, chidren_removed and children_updated.
    """
    def __init__(self,
                 parent_id: Union[str, None],
                 initial_state: ViewState = None):
        """Registers the View instance in misli.gui, so that model and child
        updates are received accordingly.

        Args:
            parent_id (str): The parent id. Can be none if this view is a root
            initial_state (Entity): The view model should be an Entity subclass
        """
        self.subscribtions = []

        if not initial_state:
            initial_state = ViewState()
        initial_state.parent_id = parent_id
        self.__state = initial_state
        self.__previous_state = None

    def __repr__(self):
        return '<%s id=%s>' % (type(self).__name__, self.id)

    @property
    def id(self):
        return self.__state.id

    @property
    def parent_id(self):
        return self.__state.parent_id

    def state(self) -> ViewState:
        if misli.gui.is_in_action():
            # While executing actions - states changes are buffered
            return misli.gui.view_state(self.id)

        # When not in an action we return the state applied to the view
        # This is equivalent to misli.gui.displayed_state()
        return self.__state.copy()

    def previous_state(self) -> ViewState:
        if not self.__previous_state:
            return None
        return self.__previous_state.copy()

    @log.traced
    def _handle_state_changes(self, changes):
        with gui.lock_actions():
            for change in changes:
                if change.is_update():
                    self.__previous_state = self.__state
                    self.__state = change.last_state()
                    self.on_state_update()

    @log.traced
    def _handle_children_state_changes(self, changes):
        with gui.lock_actions():
            for change in changes:
                if change.is_create():
                    self.on_child_added(change.last_state().view())

                if change.is_update():
                    self.on_child_updated(change.last_state().view())

                elif change.is_delete():
                    self.on_child_removed(
                        gui.removed_view(change.last_state().id))

    # TODO: да стане mount child?
    def on_child_added(self, child):
        gui.util_provider().mount_view(child)

    def on_child_updated(self, child):
        pass

    def on_child_removed(self, child):
        gui.util_provider().unmount_view(child)

    def on_state_update(self):
        pass

    def child(self, child_id: str) -> View:
        return gui.view(child_id)

    def get_children(self) -> List[View]:
        return gui.view_children(self.id)

    def get_parent(self) -> Union[View, None]:
        return misli.gui.view(self.parent_id)

    def map_from_global(self, position: Point2D):
        return gui.util_provider().map_from_global(self, position)

    def map_to_global(self, position: Point2D):
        return gui.util_provider().map_to_global(self, position)

    def mouse_position(self):
        global_pos = gui.util_provider().mouse_position()
        return self.map_from_global(global_pos)

    def get_geometry(self):
        return gui.util_provider().view_geometry(self)

    def set_focus(self):
        gui.util_provider().set_focus(self)
