import time

from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt, QPoint, QTimer
from PySide2.QtGui import QPainter, QPicture, QImage, QColor, QBrush

from misli import misli
from misli.gui.constants import MAX_RENDER_TIME
from misli.core.primitives import Point
from misli.gui.map_page.component import MapPageComponent

from misli.core import logging
log = logging.getLogger(__name__)

RENDER_CACHE_PADDING = 1


class MapPageQtComponent(QWidget, MapPageComponent):
    def __init__(self, page_id):
        QWidget.__init__(self)
        MapPageComponent.__init__(self, page_id)

        self.debug_drawing = False

        # Widget config
        pal = self.palette()
        pal.setColor(pal.Window, Qt.white)

        self.setPalette(pal)
        self.setMouseTracking(1)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def set_props(self, **page):
        self.update()

    def render_cache_rect_unprojected(self, display_rect):
        # Project and round down to the pixel grid
        cache_rect = display_rect.toRect()

        cache_rect.moveTo(
            cache_rect.x() - RENDER_CACHE_PADDING,
            cache_rect.y() - RENDER_CACHE_PADDING)
        cache_rect.setWidth(cache_rect.width() + 2 * RENDER_CACHE_PADDING)
        cache_rect.setHeight(cache_rect.height() + 2 * RENDER_CACHE_PADDING)

        return cache_rect

    def render_child(self, child, display_rect):
        painter = QPainter()
        cache_rect = self.render_cache_rect_unprojected(display_rect)

        pcommand_cache = child.data.get('pcommand_cache', None)
        render_img = child.data.get('render_cache', None)
        render_cache_expired = child.data.get('render_cache_expired', True)

        if not pcommand_cache:  # Gets deleted when expired
            # In order to be pixel perfect - relay through QPicture
            # Otherwise QWidget rounds up coordinates.
            # RIP 30 hours of trying other workarounds
            pcommand_cache = QPicture()

            child.render(pcommand_cache, QPoint(0, 0))
            child.data['pcommand_cache'] = pcommand_cache

        if render_cache_expired or not render_img:
            render_img = QImage(cache_rect.size(), QImage.Format_ARGB32)
            child.data['render_cache'] = render_img

        render_img.fill(0)

        if self.debug_drawing:
            render_img.fill(QColor(255, 0, 0, 100))

        painter.begin(render_img)

        # For historical purpuses: drawing on the cache image needs to be
        # done with an offset = display_rect.x() % 1 otherwise there will be
        # visual artefats at the boundaries of adjacent notes.
        # RIP a few more hours of tracing those.

        draw_point_x = display_rect.x() - cache_rect.x()
        draw_point_y = display_rect.y() - cache_rect.y()

        scale_factor = self.viewport.height_scale_factor()

        painter.translate(draw_point_x, draw_point_y)
        painter.scale(scale_factor, scale_factor)

        pcommand_cache.play(painter)
        painter.end()

        child.data['render_cache'] = render_img
        child.data['render_cache_expired'] = False

    def paintEvent(self, event):
        paint_t0 = time.time()

        painter = QPainter()
        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        pen = painter.pen()
        pen.setCosmetic(True)
        painter.setPen(pen)

        unprojected_viewport = self.viewport.unproject_rect(self.rect())

        display_rects = {}  # id: rect
        for child in self.get_children():
            note = misli.base_object_for_component(child.id)
            nt_rect = note.rect()

            if not nt_rect.intersects(unprojected_viewport):
                continue

            display_rects[child.id] = self.viewport.project_rect(nt_rect)

        rendered_notes = 0
        for child in self.get_children():
            if child.id not in display_rects:
                continue

            paint_urgently = False
            if time.time() - paint_t0 > MAX_RENDER_TIME:
                paint_urgently = True
                QTimer.singleShot(0, self.update)

                # log.info('Painted urgently. Queued rerender.',
                #          extra={'page_id': self.id})

            pcommand_cache = child.data.get('pcommand_cache', None)
            render_img = child.data.get('render_cache', None)
            render_cache_expired = child.data.get('render_cache_expired', True)

            if not render_img:
                cache_rect = self.render_cache_rect_unprojected(
                    display_rects[child.id])

                render_img = QImage(cache_rect.size(), QImage.Format_ARGB32)

                render_img.fill(QColor(100, 100, 100, 100))
                child.data['render_cache'] = render_img

            if ((render_cache_expired or not pcommand_cache)
                    and not paint_urgently):
                self.render_child(child, display_rects[child.id])

        # Draw the prerendered components
        # A separate loop in order to apply the render time restriction to the
        # slow component rendering only
        for child in self.get_children():
            if child.id not in display_rects:
                continue

            cache_rect = self.render_cache_rect_unprojected(
                display_rects[child.id])

            render_img = child.data.get('render_cache')

            if self.debug_drawing:
                painter.setPen(Qt.NoPen)
                painter.fillRect(display_rects[child.id],
                                 QBrush(Qt.green, Qt.SolidPattern))

            painter.drawImage(cache_rect, render_img)
            rendered_notes += 1

            # Draw a yellow selection overlay
            if child.id in self.selected_nc_ids:
                painter.fillRect(display_rects[child.id],
                                 QColor(255, 255, 0, 127))

        if self.drag_select.active and self.drag_select.rect:
            painter.fillRect(self.drag_select.rect, QColor(100, 100, 100, 50))
            for nc_id in self.drag_select.nc_ids:
                if nc_id not in display_rects:
                    continue

                painter.fillRect(display_rects[nc_id],
                                 QColor(255, 255, 0, 127))

        # Report latency
        latency = 1000 * (time.time() - paint_t0)
        fps = 1000 / latency
        # print('Paint event latency: %s ms. Notes %s' %
        #       (latency, rendered_notes))

        painter.setPen(Qt.red)
        painter.drawText(10, 10, 'FPS: %s' % int(fps))
        painter.end()

    def mousePressEvent(self, event):
        if event.button() is Qt.LeftButton:
            super().handle_left_mouse_press(Point.from_QPointF(event.pos()))

    def mouseReleaseEvent(self, event):
        if event.button() is Qt.LeftButton:
            super().handle_left_mouse_release(Point.from_QPointF(event.pos()))

    def mouseMoveEvent(self, event):
        super().handle_mouse_move(Point.from_QPointF(event.pos()))

    def mouseDoubleClickEvent(self, event):
        if event.button() is Qt.LeftButton:
            self.handle_left_mouse_double_click(
                Point.from_QPointF(event.pos()))

    def wheelEvent(self, event):
        degrees = event.delta() / 8
        steps = degrees / 15

        self.handle_mouse_scroll(steps)

    def resizeEvent(self, event):
        pass
