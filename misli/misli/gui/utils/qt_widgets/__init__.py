from typing import Callable
from PySide6.QtCore import QObject
import misli
from misli.entity_library.change import Change
from misli.gui.view_library.view_state import ViewState


def bind_and_apply_state(qobject: QObject,
                         state: ViewState,
                         on_state_change: Callable):

    subscription = misli.gui.channels.state_changes_by_id.subscribe(
        on_state_change, index_val=state.id)
    qobject.destroyed.connect(lambda: subscription.unsubscribe())

    # misli.call_delayed(on_state_change, args=[Change.CREATE(state)])
    on_state_change(Change.CREATE(state))
