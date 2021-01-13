import misli
from misli.constants import INITIAL_EYE_Z
from misli.core.primitives import Point, Rectangle


class Viewport(object):
    def __init__(self, _map_page_component):
        self._map_page_component = _map_page_component

        self._center = Point(0, 0)
        self.eyeHeight = INITIAL_EYE_Z

    def __repr__(self):
        info = (self.center(), self.eyeHeight)
        return '<Viewport center=%s eyeHeight=%s>' % info

    def center(self):
        return self._center

    def set_center(self, new_center):
        if type(new_center) != Point:
            raise ValueError

        self._center = new_center

    def height_scale_factor(self):
        return misli.line_spacing_in_pixels / self.eyeHeight

    def project_rect(self, rect):
        top_left = self.project_point(rect.top_left())
        bottom_right = self.project_point(rect.bottom_right())
        return Rectangle.from_points(top_left, bottom_right)

    def project_point(self, point):
        return Point(self.project_x(point.x()), self.project_y(point.y()))

    def project_x(self, x_on_page):
        x_on_page -= self.center().x()
        x_on_page *= self.height_scale_factor()
        return x_on_page + self._map_page_component.width() / 2

    def project_y(self, y_on_page):
        y_on_page -= self.center().y()
        y_on_page *= self.height_scale_factor()
        return y_on_page + self._map_page_component.height() / 2

    def unproject_point(self, point):
        return Point(self.unproject_x(point.x()), self.unproject_y(point.y()))

    def unproject_rect(self, rect):
        top_left = self.unproject_point(rect.top_left())
        bottom_right = self.unproject_point(rect.bottom_right())
        return Rectangle.from_points(top_left, bottom_right)

    def unproject_x(self, x_on_screen):
        x_on_screen -= self._map_page_component.width() / 2
        x_on_screen /= self.height_scale_factor()
        return x_on_screen + self.center().x()

    def unproject_y(self, y_on_screen):
        y_on_screen -= self._map_page_component.height() / 2
        y_on_screen /= self.height_scale_factor()
        return y_on_screen + self.center().y()
