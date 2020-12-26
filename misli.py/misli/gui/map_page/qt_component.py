import time

from PySide2.QtWidgets import QWidget, QShortcut
from PySide2.QtCore import Qt, QPoint, QTimer, QRectF
from PySide2.QtGui import QPainter, QPicture, QImage, QColor, QBrush, QCursor
from PySide2.QtGui import QKeySequence

import misli
from misli.gui.map_page import usecases
from misli.constants import MAX_RENDER_TIME, RESIZE_CIRCLE_RADIUS
from misli.core.primitives import Point, Rectangle
from misli.gui.constants import SELECTION_OVERLAY_COLOR, ALIGNMENT_LINE_LENGTH
from misli.gui.constants import LONG_PRESS_TIMEOUT
from misli.gui.map_page.component import MapPageComponent
from misli.gui.base_component import Component

log = misli.get_logger(__name__)

IMAGE_CACHE_PADDING = 1
MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT = 10


class MapPageQtComponent(QWidget, MapPageComponent):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        MapPageComponent.__init__(self, parent_id)

        self._paint_event_count = 0
        self.debug_drawing = False
        self._mouse_press_position = QPoint()

        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self._handle_delete_shortcut)

        select_all_shortcut = QShortcut(
            QKeySequence(Qt.CTRL + Qt.Key_A), self)
        select_all_shortcut.activated.connect(
            lambda: usecases.select_all_notes(self.id))

        # Widget config
        pal = self.palette()
        pal.setColor(pal.Window, Qt.white)

        self.setPalette(pal)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def add_child(self, child: Component):
        MapPageComponent.add_child(self, child)
        child.setHidden(True)

    def image_cache_rect_unprojected(self, display_rect: Rectangle):
        # Project and round down to the pixel grid
        cache_rect = display_rect.toRect()

        cache_rect.moveTo(
            cache_rect.x() - IMAGE_CACHE_PADDING,
            cache_rect.y() - IMAGE_CACHE_PADDING)
        cache_rect.setWidth(cache_rect.width() + 2 * IMAGE_CACHE_PADDING)
        cache_rect.setHeight(cache_rect.height() + 2 * IMAGE_CACHE_PADDING)

        return cache_rect

    def prep_command_cache_for_child(self, child: Component):
        # In order to be pixel perfect - relay through QPicture
        # Otherwise QWidget rounds up coordinates.
        # RIP 30 hours of trying other workarounds
        pcommand_cache = QPicture()

        child.render(pcommand_cache, QPoint(0, 0))
        child.pcommand_cache = pcommand_cache
        child.should_rebuild_pcommand_cache = False

    def render_image_cache_for_child(
            self, child: Component, display_rect: Rectangle):
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
        child.should_rerender_image_cache = False

    def _draw_guide_lines_for_child(
            self, display_rect: Rectangle, painter: QPainter):
        # Draw guiding lines. How: get the four lines, sort the points,
        # elongate them and draw
        rect = display_rect
        h_lines = [[rect.top_left(), rect.top_right()],
                   [rect.bottom_left(), rect.bottom_right()]]
        v_lines = [[rect.top_left(), rect.bottom_left()],
                   [rect.top_right(), rect.bottom_right()]]

        elong = ALIGNMENT_LINE_LENGTH
        all_lines = [*h_lines, *v_lines]

        for line in h_lines:
            p1, p2 = line

            p1 = Point(
                p1.x() - elong,  # p1.x == p2.x
                min(p1.y(), p1.y()))
            p2 = Point(
                p2.x() + elong,
                max(p1.y(), p2.y()))

            all_lines.append([p1, p2])

        for line in v_lines:
            p1, p2 = line

            p1 = Point(
                min(p1.x(), p2.x()),
                p1.y() - elong)  # p1.y == p2.y
            p2 = Point(
                max(p1.x(), p2.x()),
                p2.y() + elong)

            all_lines.append([p1, p2])

        for line in all_lines:
            p1, p2 = line
            points = [*p1.to_list(), *p2.to_list()]
            painter.drawLine(*points)

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
        placeholders_drawn = 0
        image_cache_memory_allocations = 0
        pc_cache_jobs = 0
        render_to_image_jobs = 0
        notes_reusing_cache = 0
        reused_expired_caches = 0
        non_urgent_count = 0
        paint_urgently = False

        # Determine the components inside the viewport
        display_rects_by_child_id = self._visible_display_rects_by_child_id()

        # Render the notes into a painter-commands-cache and an image cache
        # (prep only placeholders if slow)
        # At minimum renders one component into cache and preps placeholders
        for child_id, display_rect in display_rects_by_child_id.items():
            child = self.child(child_id)

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
                cache_rect = self.image_cache_rect_unprojected(display_rect)

                render_img = QImage(cache_rect.size(), QImage.Format_ARGB32)
                child.image_cache = render_img
                child.should_reallocate_image_cache = False

            if child.should_rerender_image_cache:
                render_to_image_jobs += 1
                non_urgent_count += 1

                self.render_image_cache_for_child(child, display_rect)

            else:
                notes_reusing_cache += 1

        # Draw the cached images, along with various decorations
        for child_id, display_rect in display_rects_by_child_id.items():
            child = self.child(child_id)

            render_img = child.image_cache

            nt_main_color = QColor(
                *child.note().get_color().to_uint8_rgba_list())

            nt_background_color = QColor(
                *child.note().get_background_color().to_uint8_rgba_list())

            nt_background_brush = QBrush(nt_background_color, Qt.SolidPattern)

            painter.setPen(nt_main_color)
            painter.setBrush(nt_background_brush)

            if not render_img:  # Draw okaceholders where needed
                placeholders_drawn += 1

                ph_color = QColor(nt_background_color)
                ph_color.setAlpha(60)
                ph_brush = QBrush(ph_color, Qt.DiagCrossPattern)

                painter.fillRect(display_rect, ph_brush)
                continue

            if child.should_rebuild_pcommand_cache or \
               child.should_reallocate_image_cache or \
               child.should_rerender_image_cache:
                reused_expired_caches += 1

            # Draw the cached redering of the component
            cache_rect = self.image_cache_rect_unprojected(display_rect)
            painter.drawImage(cache_rect, render_img)

            if self.debug_drawing:
                painter.save()
                painter.setPen(Qt.NoPen)
                green_brush = QBrush(Qt.green, Qt.SolidPattern)
                painter.fillRect(display_rect, green_brush)
                painter.restore()

            # Draw addinional stuff for selected notes
            if child.id in self.selected_nc_ids:
                # Draw a yellow selection overlay
                overlay_color = QColor(
                    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())
                painter.fillRect(
                    display_rect, overlay_color)

                # Draw the resize circle
                center = display_rect.bottomRight()
                radius = RESIZE_CIRCLE_RADIUS
                radius *= self.viewport.height_scale_factor()

                circle_fill_color = QColor(nt_main_color)
                circle_fill_color.setAlpha(60)

                painter.save()
                painter.setBrush(QBrush(circle_fill_color, Qt.SolidPattern))

                painter.drawEllipse(center, radius, radius)
                painter.restore()

            # Draw lines for easier visual alignment
            if self.note_resize_active or self.note_drag_active:
                if child.id in self.selected_nc_ids:
                    qdr = display_rect
                    dr = Rectangle(qdr.x(), qdr.y(), qdr.width(), qdr.height())
                    self._draw_guide_lines_for_child(dr, painter)

        if self.drag_select_active:
            # Draw the selection rects
            drag_select_rect = QRectF(*self.drag_select_rect_props)
            painter.fillRect(drag_select_rect, QColor(100, 100, 100, 50))

            # Draw the selection overlays
            for nc_id in self.drag_select_nc_ids:
                overlay_color = QColor(
                    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())
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

        log.info(stats_text)
        painter.drawText(10, 10, stats_text)
        painter.end()

        if paint_urgently and \
           (reused_expired_caches > 0 or placeholders_drawn > 0):
            QTimer.singleShot(0, self.update)

    def check_for_long_press(self):
        new_pos = self.mapFromGlobal(QCursor.pos())
        if self._mouse_press_position == new_pos and \
           self.left_mouse_is_pressed:
            self.handle_left_mouse_long_press(
                Point(new_pos.x(), new_pos.y()))

    def mousePressEvent(self, event):
        self._mouse_press_position = event.pos()

        QTimer.singleShot(LONG_PRESS_TIMEOUT * 1000, self.check_for_long_press)

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
