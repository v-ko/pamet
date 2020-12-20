import time

from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt, QPoint, QTimer, QRectF
from PySide2.QtGui import QPainter, QPicture, QImage, QColor, QBrush

import misli
from misli.constants import MAX_RENDER_TIME, RESIZE_CIRCLE_RADIUS
from misli.core.primitives import Point, Rectangle
from misli.gui.constants import selection_overlay_color
from misli.gui.map_page.component import MapPageComponent

log = misli.get_logger(__name__)

IMAGE_CACHE_PADDING = 1
MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT = 10


class MapPageQtComponent(QWidget, MapPageComponent):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        MapPageComponent.__init__(self, parent_id)

        self._paint_event_count = 0
        self.debug_drawing = False

        # Widget config
        pal = self.palette()
        pal.setColor(pal.Window, Qt.white)

        self.setPalette(pal)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def add_child(self, child):
        MapPageComponent.add_child(self, child)
        child.setHidden(True)

    def image_cache_rect_unprojected(self, display_rect):
        # Project and round down to the pixel grid
        cache_rect = display_rect.toRect()

        cache_rect.moveTo(
            cache_rect.x() - IMAGE_CACHE_PADDING,
            cache_rect.y() - IMAGE_CACHE_PADDING)
        cache_rect.setWidth(cache_rect.width() + 2 * IMAGE_CACHE_PADDING)
        cache_rect.setHeight(cache_rect.height() + 2 * IMAGE_CACHE_PADDING)

        return cache_rect

    def prep_command_cache_for_child(self, child):
        # In order to be pixel perfect - relay through QPicture
        # Otherwise QWidget rounds up coordinates.
        # RIP 30 hours of trying other workarounds
        pcommand_cache = QPicture()

        child.render(pcommand_cache, QPoint(0, 0))
        child.pcommand_cache = pcommand_cache
        child.should_rebuild_pcommand_cache = False

    def render_image_cache_for_child(self, child, display_rect):
        painter = QPainter()
        cache_rect = self.image_cache_rect_unprojected(display_rect)

        pcommand_cache = child.pcommand_cache
        render_img = child.image_cache
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

        child.image_cache = render_img
        child.shoud_rerender_image_cache = False

    def _visible_display_rects_by_child_id(self):
        viewport_rect = Rectangle(
            self.rect().x(),
            self.rect().y(),
            self.rect().width(),
            self.rect().height())
        unprojected_viewport = self.viewport.unproject_rect(viewport_rect)

        display_rects_by_child_id = {}  # {nc_id: rect}
        for child in self.get_children():
            nt_rect = child.note().rect()

            if not nt_rect.intersects(unprojected_viewport):
                continue

            unprojected_rect = self.viewport.project_rect(nt_rect)
            display_rects_by_child_id[child.id] = QRectF(
                *unprojected_rect.to_list())

        return display_rects_by_child_id

    def paintEvent(self, event):
        self._paint_event_count += 1
        paint_t0 = time.time()

        painter = QPainter()
        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        pen = painter.pen()
        pen.setCosmetic(True)
        painter.setPen(pen)

        # Vars for stats
        image_cache_memory_allocations = 0
        placeholders_drawn = 0
        pc_cache_jobs = 0
        render_to_image_jobs = 0
        notes_reusing_cache = 0
        reused_expired_caches = 0
        non_urgent_count = 0
        # Determine the components inside the viewport
        display_rects_by_child_id = self._visible_display_rects_by_child_id()

        # Render the notes into a painter-commands-cache and an image cache
        # (prep only placeholders if slow)
        # At minimum renders one component into cache and preps placeholders
        for child_id in display_rects_by_child_id:
            child = self.child(child_id)
            paint_urgently = False

            if time.time() - paint_t0 > MAX_RENDER_TIME:
                paint_urgently = True

                if non_urgent_count >= MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT:
                    continue

            if child.should_rebuild_pcommand_cache:
                pc_cache_jobs += 1
                self.prep_command_cache_for_child(child)

            # Allocate the image_cache. Done on resize, but not e.g. translate
            if child.should_reallocate_image_cache:
                image_cache_memory_allocations += 1
                cache_rect = self.image_cache_rect_unprojected(
                    display_rects_by_child_id[child.id])

                render_img = QImage(cache_rect.size(), QImage.Format_ARGB32)
                child.image_cache = render_img
                child.should_reallocate_image_cache = False

            if child.shoud_rerender_image_cache:
                render_to_image_jobs += 1

                self.render_image_cache_for_child(
                    child, display_rects_by_child_id[child.id])

                non_urgent_count += 1

            else:
                notes_reusing_cache += 1

        # Draw the cached images, along with various decorations
        for child in self.get_children():
            if child.id not in display_rects_by_child_id:
                continue

            render_img = child.image_cache

            if not render_img:  # Draw okaceholders where needed
                placeholders_drawn += 1
                placeholder_brush = QBrush(
                    QColor(100, 100, 100, 100), Qt.SolidPattern)
                painter.fillRect(display_rects_by_child_id[child.id],
                                 placeholder_brush)
                continue

            if child.should_rebuild_pcommand_cache or \
               child.should_reallocate_image_cache or \
               child.shoud_rerender_image_cache:
                reused_expired_caches += 1

            # Draw the cached redering of the component
            cache_rect = self.image_cache_rect_unprojected(
                display_rects_by_child_id[child.id])
            painter.drawImage(cache_rect, render_img)

            if self.debug_drawing:
                painter.setPen(Qt.NoPen)
                painter.fillRect(display_rects_by_child_id[child.id],
                                 QBrush(Qt.green, Qt.SolidPattern))

            # Draw addinional stuff for selected notes
            if child.id in self.selected_nc_ids:
                # Draw a yellow selection overlay
                overlay_color = QColor(
                    *selection_overlay_color.to_uint8_rgba_list())
                painter.fillRect(
                    display_rects_by_child_id[child.id], overlay_color)

                # Draw the resize circle
                center = display_rects_by_child_id[child.id].bottomRight()
                radius = RESIZE_CIRCLE_RADIUS
                radius *= self.viewport.height_scale_factor()

                circle_outline_color = QColor(
                    *child.note().get_color().to_uint8_rgba_list())
                circle_fill_color = QColor(circle_outline_color)
                circle_fill_color.setAlpha(60)

                painter.save()
                painter.setPen(circle_outline_color)
                painter.setBrush(QBrush(circle_fill_color, Qt.SolidPattern))

                painter.drawEllipse(center, radius, radius)
                painter.restore()

                # Draw guiding lines
                pass

        if self.drag_select_active:
            # Draw the selection rects
            drag_select_rect = QRectF(*self.drag_select_rect_props)
            painter.fillRect(drag_select_rect, QColor(100, 100, 100, 50))

            # Draw the selection overlays
            for nc_id in self.drag_select_nc_ids:
                overlay_color = QColor(
                    *selection_overlay_color.to_uint8_rgba_list())
                painter.fillRect(
                    display_rects_by_child_id[nc_id], overlay_color)

        # Report stats
        notes_on_screen = len(display_rects_by_child_id)

        latency = 1000 * (time.time() - paint_t0)
        # fps = 1000 / latency

        painter.setPen(Qt.red)
        stats_text = ('Last render stats: %s notes on screen ,'
                      ' %s newly allocated,'
                      ' %s as placeholders, %s PC cache jobs, '
                      '%s render to img jobs, %s reusing cache, '
                      '%s reusing expired.Latency: %sms.'
                      ' Painted urgently: %s. Paint event count: %s' %
                      (notes_on_screen,
                       image_cache_memory_allocations,
                       placeholders_drawn,
                       pc_cache_jobs,
                       render_to_image_jobs,
                       notes_reusing_cache,
                       reused_expired_caches,
                       int(latency),
                       'True' if paint_urgently else 'False',
                       self._paint_event_count))

        print(stats_text)
        painter.drawText(10, 10, stats_text)
        painter.end()

        if paint_urgently and \
           (reused_expired_caches > 0 or placeholders_drawn > 0):
            QTimer.singleShot(0, self.update)

    def mousePressEvent(self, event):
        if event.button() is Qt.LeftButton:
            super().handle_left_mouse_press(
                Point(event.pos().x(), event.pos().y()))

    def mouseReleaseEvent(self, event):
        if event.button() is Qt.LeftButton:
            super().handle_left_mouse_release(
                Point(event.pos().x(), event.pos().y()))

    def mouseMoveEvent(self, event):
        super().handle_mouse_move(Point(event.pos().x(), event.pos().y()))

    def mouseDoubleClickEvent(self, event):
        if event.button() is Qt.LeftButton:
            self.handle_left_mouse_double_click(
                Point(event.pos().x(), event.pos().y()))

    def wheelEvent(self, event):
        degrees = event.delta() / 8
        steps = degrees / 15

        self.handle_mouse_scroll(steps)

    def resizeEvent(self, event):
        pass
