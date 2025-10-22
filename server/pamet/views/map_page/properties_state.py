
from fusion.libs.state import ViewState, view_state_type


@view_state_type
class MapPagePropertiesViewState(ViewState):
    focused_prop: str = ''

    @property
    def page_id(self):
        return self.id
