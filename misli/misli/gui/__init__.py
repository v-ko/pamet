"""The misli.gui module provides basic functionality for handling GUI state
and updates. The main parts of the misli based GUI app are Views, their
respective View Models, and Actions (alternatively called usecases).

View classes are widgets (in Qt) or e.g. React components in web apps.
Though they are allowed to have a local state - all properties that can be
changed by other classes or functions should be in their View Model.

Each instance of a view and their view model get registered (automatically)
    upon creation in misli.gui. And the only proper way to change a View
    Model is via misli.update_view_model(new_model). That method chaches
    the updated models and in that way unneeded GUI renderings are avoided
    in the midst of complex user actions. After all action logic is executed -
    the updated view models are pushed to the views (by invoking their
    View.handle_model_update virtual method).

Actions are simple functions that should carry the bulk of the GUI
interaction logic. They should be decorated with misli.gui.actions_lib.action
in order to have proper logging and reproducability of the user
interactions. E.g. if we want to change the background of a View, we'll
create an action like:

@action('change_background')
def change_background(view_id, background_color):
    view_model = misli.gui.view_model(view_id)
    view_model.background_color = background_color
    misli.update_view_model(view_model)

After calling this action - the View.handle_model_update will be invoked
with the new model. This allows for complex GUI logic that is reproducible
and enforces the avoidance of endless nested callbacks.

TODO: Example on a simple View + View Model
"""

from .misli_gui import *
from .actions_library import action
from .view_library import register_view_type
from .view_library.view import View
from .view_library.view_state import ViewState, register_view_state_type
