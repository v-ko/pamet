from misli.gui.page_component import PageComponent
from misli.gui.map_page.viewport import Viewport


class MapPageComponent(PageComponent):
    def __init__(self, page_id):
        super(MapPageComponent, self).__init__(page_id)

        self.viewport = Viewport(self)
