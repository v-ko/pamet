from dataclasses import field

from fusion.libs.state import view_state_type, ViewState
from fusion.view import View


@view_state_type
class WindowViewState(ViewState):
    title: str = ''
    current_tab_id: str = ''
    tab_states: list = field(default_factory=list)
    command_view_state: View = None

    def __repr__(self) -> str:
        return (f'<WindowViewState title={self.title} {self.current_tab_id=}'
                f' {len(self.tab_states)=}>')
