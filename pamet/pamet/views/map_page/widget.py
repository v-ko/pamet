import time
from typing import List

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QTimer, QRectF
from PySide6.QtGui import QPainter, QPicture, QImage, QColor, QBrush, QCursor
from PySide6.QtGui import QKeySequence, QShortcut

import misli
from misli.basic_classes import Point2D, Rectangle
from misli.gui.actions_library import action
from misli.gui.utils import qt_widgets
from misli.gui.view_library.view import View

from pamet.constants import MAX_RENDER_TIME, RESIZE_CIRCLE_RADIUS
from pamet.constants import SELECTION_OVERLAY_COLOR, ALIGNMENT_LINE_LENGTH
from pamet.constants import LONG_PRESS_TIMEOUT

import pamet
from pamet import actions
from pamet.views.map_page.view import MapPageView, MapPageViewState

from misli.entity_library.change import Change

log = misli.get_logger(__name__)

IMAGE_CACHE_PADDING = 1
MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT = 10


class NoteViewCache:

    def __init__(self):
        self.pcommand_cache: QPicture = None
        self.image_cache: QImage = None

        self.should_rebuild_pcommand_cache: bool = True
        self.should_reallocate_image_cache: bool = True
        self.should_rerender_image_cache: bool = True


def image_cache_rect_unprojected(display_rect: Rectangle):
    '''Project and round down to the pixel grid'''
    cache_rect = display_rect.toRect()

    cache_rect.moveTo(cache_rect.x() - IMAGE_CACHE_PADDING,
                      cache_rect.y() - IMAGE_CACHE_PADDING)
    cache_rect.setWidth(cache_rect.width() + 2 * IMAGE_CACHE_PADDING)
    cache_rect.setHeight(cache_rect.height() + 2 * IMAGE_CACHE_PADDING)

    return cache_rect


class MapPageWidget(QWidget, MapPageView):

    def __init__(self, parent, initial_state: MapPageViewState):
        QWidget.__init__(self, parent=parent)
        MapPageView.__init__(self, parent, initial_state)

        self.tab_widget = parent

        # Local variables
        self._cache_per_nc_id = {}
        self._paint_event_count = 0
        self.debug_drawing = False
        self._mouse_press_position = QPoint()
        self._note_widgets = {}

        # Setup shortcuts
        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.handle_delete_shortcut)

        color_notes_blue = QShortcut(QKeySequence('1'), self)
        color_notes_blue.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.id, color=[0, 0, 1, 1], background_color=[0, 0, 1, 0.1]))
        color_notes_green = QShortcut(QKeySequence('2'), self)
        color_notes_green.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.id,
                color=[0, 0.64, 0.235, 1],
                background_color=[0, 1, 0, 0.1]))
        color_notes_red = QShortcut(QKeySequence('3'), self)
        color_notes_red.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.id, color=[1, 0, 0, 1], background_color=[1, 0, 0, 0.1]))
        color_notes_gray = QShortcut(QKeySequence('4'), self)
        color_notes_gray.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.id, color=[0, 0, 0, 1], background_color=[0, 0, 0, 0.1]))
        remove_note_background = QShortcut(QKeySequence('5'), self)
        remove_note_background.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.id, background_color=[0, 0, 0, 0]))
        select_all_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_A), self)
        select_all_shortcut.activated.connect(
            lambda: actions.map_page.select_all_notes(self.id))

        # Widget config
        pal = self.palette()
        pal.setColor(pal.Window, Qt.white)

        self.setPalette(pal)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        qt_widgets.bind_and_apply_state(self,
                                        initial_state,
                                        on_state_change=self.on_state_change)

        # Subscribe to note changes
        self.subscribtion_ids = []
        self.nw_subscribtions = {}  # by note widget
        self.subscribtion_ids.append(
            pamet.channels.entity_changes_by_id.subscribe(
                self.handle_page_change, index_val=self.state().page.id))
        self.subscribtion_ids.append(
            pamet.channels.entity_changes_by_parent_gid.subscribe(
                self.handle_note_change, index_val=self.state().page.id))

        self.destroyed.connect(self.unsubscribe_all)

    def unsubscribe_all(self):
        for sid in self.subscribtion_ids:
            misli.unsubscribe(sid)

        for nw, sid in self.nw_subscribtions.items():
            misli.unsubscribe(sid)

    def get_children(self) -> List[View]:
        yield from self.note_widgets()

    def on_state_change(self, change: Change):
        # state = change.last_state()

        # if change.updated.name:
        #     # Fix the tab text when changing the page name
        #     window = self.tab_widget.parent_window
        #     self_idx = window.ui.tabBarWidget.indexOf(self)
        #     window.ui.tabBarWidget.setTabText(self_idx, state.name)

        if change.updated.viewport_height:
            # Invalidate image_cache for all children
            for child in self.children():
                nv_cache = self.note_view_cache(child.id)
                nv_cache.should_reallocate_image_cache = True
                nv_cache.should_rerender_image_cache = True
            # self.update()

        for nv_state in change.added.note_view_states:
            self.add_note_widget(nv_state)

        for nv_state in change.removed.note_view_states:
            note_widget = self.note_widget(nv_state.id)
            self.remove_note_widget(note_widget)

        self.update()

    def add_note_widget(self, nv_state):
        ViewType = pamet.note_view_type_by_state(type(nv_state).__name__)
        note_widget = ViewType(parent=self, initial_state=nv_state)
        self._note_widgets[nv_state.id] = note_widget

        sid = misli.gui.channels.state_changes_by_id.subscribe(
            lambda change: self.on_child_updated(change.last_state()),
            index_val=note_widget.id)
        self.nw_subscribtions[note_widget] = sid
        # self.update()

    def on_child_updated(self, note_view):
        nv_cache = self.note_view_cache(note_view.id)
        nv_cache.should_rebuild_pcommand_cache = True
        nv_cache.should_rerender_image_cache = True
        nv_cache.should_reallocate_image_cache = True
        self.update()

    def remove_note_widget(self, note_widget):
        nw_id = note_widget.state().id
        self.delete_note_view_cache(nw_id)
        misli.unsubscribe(self.nw_subscribtions[note_widget])
        note_widget = self._note_widgets.pop(nw_id)
        note_widget.deleteLater()
        # self.update()

    @action('MapPageView.handle_note_change')
    def handle_note_change(self, change: Change):
        state = self.state()
        note = change.last_state()
        if change.is_create():
            ViewType = pamet.note_view_type(note_type_name=type(note).__name__,
                                            edit=False)
            StateType = pamet.note_state_type_by_view(ViewType.__name__)
            nv_state = StateType(**note.asdict(), note_gid=note.gid())
            misli.gui.add_state(nv_state)
            state.note_view_states.append(nv_state)
            misli.gui.update_state(state)

        elif change.is_delete():
            nv_states = filter(lambda x: x.note_gid == note.gid(),
                               state.note_view_states)
            for nv_state in nv_states:  # Should be len==1
                misli.gui.remove_state(nv_state)
                state.note_view_states.remove(nv_state)
            misli.gui.update_state(state)

        else:  # Updated
            note_widget = self.note_widget_by_note_id(note.id)
            nv_state = note_widget.state()
            nv_state.replace(**note.asdict())
            misli.gui.update_state(nv_state)
            self.on_child_updated(note_widget)

    def note_view_cache(self, note_view_id):
        if note_view_id not in self._cache_per_nc_id:
            self._cache_per_nc_id[note_view_id] = NoteViewCache()

        return self._cache_per_nc_id[note_view_id]

    def delete_note_view_cache(self, note_view_id):
        del self._cache_per_nc_id[note_view_id]

    def note_widgets(self):
        for nw_id, note_widget in self._note_widgets.items():
            yield note_widget

    def note_widget(self, state_id):
        return self._note_widgets[state_id]

    def note_widget_by_note_id(self, note_id):
        for nw_id, note_widget in self._note_widgets.items():
            if note_widget.state().note.id == note_id:
                return note_widget

    def prep_command_cache_for_child(self, child):
        # In order to be pixel perfect - relay through QPicture
        # Otherwise QWidget rounds up coordinates.
        # RIP 30 hours of trying other workarounds
        pcommand_cache = QPicture()

        child.render(pcommand_cache, QPoint(0, 0))

        nv_cache = self.note_view_cache(child.id)
        nv_cache.pcommand_cache = pcommand_cache
        nv_cache.should_rebuild_pcommand_cache = False

    def _render_image_cache_for_child(self, child: View,
                                      display_rect: Rectangle):
        painter = QPainter()

        cache_rect = image_cache_rect_unprojected(display_rect)
        nv_cache = self.note_view_cache(child.id)

        pcommand_cache = nv_cache.pcommand_cache
        render_img = nv_cache.image_cache
        render_img.fill(0)

        if self.debug_drawing:
            render_img.fill(QColor(255, 0, 0, 100))

        painter.begin(render_img)

        # Drawing on the cache image needs to be
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

        nv_cache = self.note_view_cache(child.id)
        nv_cache.image_cache = render_img
        nv_cache.should_rerender_image_cache = False

    def _draw_guide_lines_for_child(self, display_rect: Rectangle,
                                    painter: QPainter):
        # Draw guiding lines. How: get the four lines, sort the points,
        # elongate them and draw
        rect = display_rect
        h_lines = [[rect.top_left(), rect.top_right()],
                   [rect.bottom_left(),
                    rect.bottom_right()]]
        v_lines = [[rect.top_left(), rect.bottom_left()],
                   [rect.top_right(), rect.bottom_right()]]

        elong = ALIGNMENT_LINE_LENGTH
        all_lines = [*h_lines, *v_lines]

        for line in h_lines:
            p1, p2 = line

            p1 = Point2D(
                p1.x() - elong,  # p1.x == p2.x
                min(p1.y(), p1.y()))
            p2 = Point2D(p2.x() + elong, max(p1.y(), p2.y()))

            all_lines.append([p1, p2])

        for line in v_lines:
            p1, p2 = line

            p1 = Point2D(min(p1.x(), p2.x()), p1.y() - elong)  # p1.y == p2.y
            p2 = Point2D(max(p1.x(), p2.x()), p2.y() + elong)

            all_lines.append([p1, p2])

        for line in all_lines:
            p1, p2 = line
            points = [*p1.as_tuple(), *p2.as_tuple()]
            painter.drawLine(*points)

    def _visible_display_rects_by_child_id(self):
        viewport_rect = Rectangle(self.rect().x(),
                                  self.rect().y(),
                                  self.rect().width(),
                                  self.rect().height())
        unprojected_viewport = self.viewport.unproject_rect(viewport_rect)

        display_rects_by_child_id = {}  # {nc_id: rect}
        for note_widget in self.note_widgets():
            nt_rect = note_widget.state().rect()

            if not nt_rect.intersects(unprojected_viewport):
                continue

            unprojected_rect = self.viewport.project_rect(nt_rect)
            display_rects_by_child_id[note_widget.id] = QRectF(
                *unprojected_rect.as_tuple())

        return display_rects_by_child_id

    def paintEvent(self, event):
        model = self.state()
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
            child = self.note_widget(child_id)
            nv_cache = self.note_view_cache(child.id)

            if time.time() - paint_t0 > MAX_RENDER_TIME:
                paint_urgently = True

                if non_urgent_count >= MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT:
                    continue

            if nv_cache.should_rebuild_pcommand_cache:
                pc_cache_jobs += 1
                self.prep_command_cache_for_child(child)

            # Allocate the image_cache. Done on resize, but not e.g. panning
            if nv_cache.should_reallocate_image_cache:
                image_cache_memory_allocations += 1
                cache_rect = image_cache_rect_unprojected(display_rect)

                render_img = QImage(cache_rect.size(),
                                    QImage.Format_ARGB32_Premultiplied)
                nv_cache.image_cache = render_img
                nv_cache.should_reallocate_image_cache = False

            if nv_cache.should_rerender_image_cache:
                render_to_image_jobs += 1
                non_urgent_count += 1

                self._render_image_cache_for_child(child, display_rect)

            else:
                notes_reusing_cache += 1

        # Draw the cached images, along with various decorations
        for child_id, display_rect in display_rects_by_child_id.items():
            child = self.note_widget(child_id)
            nv_cache = self.note_view_cache(child.id)

            render_img = nv_cache.image_cache

            nt_main_color = QColor(
                *child.state().get_color().to_uint8_rgba_list())

            nt_background_color = QColor(
                *child.state().get_background_color().to_uint8_rgba_list())

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

            if nv_cache.should_rebuild_pcommand_cache or \
               nv_cache.should_reallocate_image_cache or \
               nv_cache.should_rerender_image_cache:
                reused_expired_caches += 1

            # Draw the cached redering of the component
            cache_rect = image_cache_rect_unprojected(display_rect)
            painter.drawImage(cache_rect, render_img)

            # Load test
            # for i in range(10):
            #     painter.drawImage(QRect(cache_rect.topLeft() + QPoint(i*50,i*50), cache_rect.size()) , render_img)

            # Draw directly from the command cache to the page
            # (several times slower)
            # painter.save()
            # painter.translate(cache_rect.topLeft())
            # painter.scale(
            #     self.viewport.height_scale_factor(),
            #     self.viewport.height_scale_factor())
            # nv_cache.pcommand_cache.play(painter)
            # # Load test
            # for i in range(10):
            #     painter.drawPicture(i*50,i*50, nv_cache.pcommand_cache)
            # painter.restore()

            # # Test text
            # painter.save()
            # font = painter.font()
            # font.setPointSizeF(20 * self.viewport.height_scale_factor())
            # painter.setFont(font)
            # painter.drawText(cache_rect.topLeft() + QPoint(0, 0.5), 'Test')
            # painter.restore()

            if self.debug_drawing:
                painter.save()
                painter.setPen(Qt.NoPen)
                green_brush = QBrush(Qt.green, Qt.SolidPattern)
                painter.fillRect(display_rect, green_brush)
                painter.restore()

            # Draw addinional stuff for selected notes
            if child.id in model.selected_nc_ids:
                # Draw a yellow selection overlay
                overlay_color = QColor(
                    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())
                painter.fillRect(display_rect, overlay_color)

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
            if model.note_resize_active or model.note_drag_active:
                if child.id in model.selected_nc_ids:
                    qdr = display_rect
                    dr = Rectangle(qdr.x(), qdr.y(), qdr.width(), qdr.height())
                    self._draw_guide_lines_for_child(dr, painter)

        if model.drag_select_active:
            # Draw the selection rects
            drag_select_rect = QRectF(*model.drag_select_rect_props)
            painter.fillRect(drag_select_rect, QColor(100, 100, 100, 50))

            # Draw the selection overlays
            for nc_id in model.drag_selected_nc_ids:
                if nc_id not in display_rects_by_child_id:
                    continue

                overlay_color = QColor(
                    *SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())
                painter.fillRect(display_rects_by_child_id[nc_id],
                                 overlay_color)

        # Report stats
        notes_on_screen = len(display_rects_by_child_id)

        latency = 1000 * (time.time() - paint_t0)
        # fps = 1000 / latency

        painter.setPen(Qt.red)
        stats_text = (
            'Last render stats: %s notes on screen ,'
            ' %s newly allocated,'
            ' %s as placeholders, %s PC cache jobs, '
            '%s render to img jobs, %s reusing cache, '
            '%s reusing expired.Latency: %sms.'
            ' Painted urgently: %s. Paint event count: %s' %
            (notes_on_screen, image_cache_memory_allocations,
             placeholders_drawn, pc_cache_jobs, render_to_image_jobs,
             notes_reusing_cache, reused_expired_caches, int(latency),
             'True' if paint_urgently else 'False', self._paint_event_count))

        log.info(stats_text)
        painter.drawText(10, 10, stats_text)
        painter.end()

        if paint_urgently and \
           (reused_expired_caches > 0 or placeholders_drawn > 0):
            QTimer.singleShot(0, self.update)

    def check_for_long_press(self):
        new_pos = self.mapFromGlobal(QCursor.pos())
        if self._mouse_press_position == new_pos and \
           self._left_mouse_is_pressed:
            self.handle_left_mouse_long_press(Point2D(new_pos.x(),
                                                      new_pos.y()))

    def mousePressEvent(self, event):
        self._mouse_press_position = event.pos()

        QTimer.singleShot(LONG_PRESS_TIMEOUT * 1000, self.check_for_long_press)

        if event.button() is Qt.LeftButton:
            self.handle_left_mouse_press(
                Point2D(event.pos().x(),
                        event.pos().y()))

        elif event.button() is Qt.RightButton:
            self.handle_right_mouse_press(
                Point2D(event.pos().x(),
                        event.pos().y()))

    def mouseReleaseEvent(self, event):
        if event.button() is Qt.LeftButton:
            self.handle_left_mouse_release(
                Point2D(event.pos().x(),
                        event.pos().y()))

    def mouseMoveEvent(self, event):
        self.handle_mouse_move(Point2D(event.pos().x(), event.pos().y()))

    def mouseDoubleClickEvent(self, event):
        if event.button() is Qt.LeftButton:
            self.handle_left_mouse_double_click(
                Point2D(event.pos().x(),
                        event.pos().y()))

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15

        self.handle_mouse_scroll(steps)

    def resizeEvent(self, event):
        self.update()
        self.handle_resize_event(event.size().width(), event.size().height())
