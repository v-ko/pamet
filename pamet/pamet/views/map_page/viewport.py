import misli
from misli.basic_classes import Point2D, Rectangle


class Viewport(object):
    def __init__(self, _map_page_view_state):
        self._map_page_view_state = _map_page_view_state

    def __repr__(self):
        info = (self.center(), self.eye_height)
        return '<Viewport center=%s eyeHeight=%s>' % info

    def center(self) -> Point2D:
        return self._map_page_view_state.viewport_center

    @property
    def eye_height(self) -> float:
        return self._map_page_view_state.viewport_height

    def height_scale_factor(self):
        return misli.line_spacing_in_pixels / self.eye_height

    def project_rect(self, rect: Rectangle) -> Rectangle:
        top_left = self.project_point(rect.top_left())
        bottom_right = self.project_point(rect.bottom_right())
        return Rectangle.from_points(top_left, bottom_right)

    def project_point(self, point: Point2D) -> Point2D:
        return Point2D(self.project_x(point.x()), self.project_y(point.y()))

    def project_x(self, x_on_page: float) -> float:
        x_on_page -= self.center().x()
        x_on_page *= self.height_scale_factor()
        return x_on_page + self._map_page_view_state.geometry.width() / 2

    def project_y(self, y_on_page: float) -> float:
        y_on_page -= self.center().y()
        y_on_page *= self.height_scale_factor()
        return y_on_page + self._map_page_view_state.geometry.height() / 2

    def unproject_point(self, point) -> Point2D:
        return Point2D(self.unproject_x(point.x()), self.unproject_y(point.y()))

    def unproject_rect(self, rect: Rectangle) -> Rectangle:
        top_left = self.unproject_point(rect.top_left())
        bottom_right = self.unproject_point(rect.bottom_right())
        return Rectangle.from_points(top_left, bottom_right)

    def unproject_x(self, x_on_screen: float) -> float:
        x_on_screen -= self._map_page_view_state.geometry.width() / 2
        x_on_screen /= self.height_scale_factor()
        return x_on_screen + self.center().x()

    def unproject_y(self, y_on_screen: float) -> float:
        y_on_screen -= self._map_page_view_state.geometry.height() / 2
        y_on_screen /= self.height_scale_factor()
        return y_on_screen + self.center().y()
