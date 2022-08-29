from typing import Callable
from PySide6.QtCore import QObject
from fusion.entity_library.change import Change
from fusion.gui.view_library.view_state import ViewState
from fusion.gui import channels


def bind_and_apply_state(qobject: QObject,
                         state: ViewState,
                         on_state_change: Callable):

    subscription = channels.state_changes_per_TLA_by_view_id.subscribe(
        on_state_change, index_val=state.view_id)
    qobject.destroyed.connect(lambda: subscription.unsubscribe())

    # fusion.call_delayed(on_state_change, args=[Change.CREATE(state)])
    on_state_change(Change.CREATE(state))
