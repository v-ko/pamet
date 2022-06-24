import time
from typing import Dict, List

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QPointF, Qt, QPoint, QTimer, QRectF
from PySide6.QtGui import QPainter, QPicture, QImage, QColor, QBrush, QCursor
from PySide6.QtGui import QKeySequence, QShortcut

import misli
from misli.basic_classes import Point2D, Rectangle
from misli.gui.utils import qt_widgets
from misli.gui.view_library.view import View
from misli.gui.views.context_menu.widget import ContextMenuWidget
from pamet import commands

from pamet.constants import MAX_RENDER_TIME, RESIZE_CIRCLE_RADIUS
from pamet.constants import SELECTION_OVERLAY_COLOR, ALIGNMENT_LINE_LENGTH
from pamet.constants import LONG_PRESS_TIMEOUT

import pamet
from pamet import actions
from pamet.actions import map_page as map_page_actions
from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.views.arrow.widget import ArrowView, ArrowViewState, ArrowWidget
from pamet.views.map_page.view import MapPageView
from pamet.views.map_page.state import MapPageViewState, MapPageMode

from misli.entity_library.change import Change
from pamet.views.note.base_note_view import NoteView, NoteViewState

log = misli.get_logger(__name__)

IMAGE_CACHE_PADDING = 1
MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT = 10
DRAG_SELECT_COLOR = QColor(100, 100, 100, 50)
selection_overlay_color = QColor(*SELECTION_OVERLAY_COLOR.to_uint8_rgba_list())
selected_arrow_color = QColor(150, 150, 0, 255)


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
        self._arrow_widgets: Dict[str, ArrowWidget] = {}

        # Setup shortcuts
        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.handle_delete_shortcut)

        color_notes_blue = QShortcut(QKeySequence('1'), self)
        color_notes_blue.activated.connect(
            lambda: actions.map_page.color_selected_notes(self.state(),
                                                          color=[0, 0, 1, 1],
                                                          background_color=
                                                          [0, 0, 1, 0.1]))
        color_notes_green = QShortcut(QKeySequence('2'), self)
        color_notes_green.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.state(),
                color=[0, 0.64, 0.235, 1],
                background_color=[0, 1, 0, 0.1]))
        color_notes_red = QShortcut(QKeySequence('3'), self)
        color_notes_red.activated.connect(
            lambda: actions.map_page.color_selected_notes(self.state(),
                                                          color=[1, 0, 0, 1],
                                                          background_color=
                                                          [1, 0, 0, 0.1]))
        color_notes_gray = QShortcut(QKeySequence('4'), self)
        color_notes_gray.activated.connect(
            lambda: actions.map_page.color_selected_notes(self.state(),
                                                          color=[0, 0, 0, 1],
                                                          background_color=
                                                          [0, 0, 0, 0.1]))
        remove_note_background = QShortcut(QKeySequence('5'), self)
        remove_note_background.activated.connect(
            lambda: actions.map_page.color_selected_notes(
                self.state(), background_color=[0, 0, 0, 0]))
        select_all_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_A), self)
        select_all_shortcut.activated.connect(
            lambda: actions.map_page.select_all_notes(self.id))
        QShortcut(QKeySequence(Qt.Key_E), self, commands.edit_selected_notes)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_E), self,
                  commands.open_page_properties)
        QShortcut(QKeySequence(Qt.Key_L), self, commands.start_arrow_creation)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.handle_esc_shortcut)

        # Widget config
        pal = self.palette()
        pal.setColor(pal.Window, Qt.white)

        self.setPalette(pal)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        self.subscriptions = []
        self.nw_subscribtions = {}  # by note widget
        self.arrow_view_state_subs_by_state_id = {}
        self.new_arrow_view_state_subs_by_state_id = {}

        # Subscribe to the page changes
        self.subscriptions.append(
            pamet.channels.entity_changes_by_id.subscribe(
                self.handle_page_change, index_val=self.state().page.id))
        # Subscribe to note changes
        self.subscriptions.append(
            pamet.channels.entity_changes_by_parent_gid.subscribe(
                self.handle_page_child_change, index_val=self.state().page.id))

        self.destroyed.connect(lambda: self.unsubscribe_all())

        qt_widgets.bind_and_apply_state(self,
                                        initial_state,
                                        on_state_change=self.on_state_change)

    def handle_page_change(self, change: Change):
        if change.updated.name:
            map_page_actions.handle_page_name_updated(self.tab_widget.state(),
                                                      change.last_state())

    def unsubscribe_all(self):
        for subscription in self.subscriptions:
            subscription.unsubscribe()

        for nw, subscription in self.nw_subscribtions.items():
            subscription.unsubscribe()

        for avs_id, sub in self.arrow_view_state_subs_by_state_id.items():
            sub.unsubscribe()

    def note_views(self) -> List[View]:
        yield from self.note_widgets()

    def arrow_views(self) -> List[ArrowView]:
        yield from self.arrow_widgets()

    def on_state_change(self, change: Change):
        state = change.last_state()
        if change.updated.viewport_height:
            # Invalidate image_cache for all children
            for child in self.children():
                nv_cache = self._note_widget_cache(child.id)
                nv_cache.should_reallocate_image_cache = True
                nv_cache.should_rerender_image_cache = True
            # self.update()

        if change.updated.special_mode:
            cursor: QCursor = self.cursor()
            if state.mode() == MapPageMode.CREATE_ARROW:
                cursor.setShape(Qt.CrossCursor)
            else:
                cursor.setShape(Qt.ArrowCursor)
            self.setCursor(cursor)

        for nv_state in change.added.note_view_states:
            self.add_note_widget(nv_state)

        for nv_state in change.removed.note_view_states:
            note_widget = self.note_widget(nv_state.id)
            self.remove_note_widget(note_widget)

        for av_state in change.added.arrow_view_states:
            self.add_arrow_widget(av_state)
        for av_state in change.removed.arrow_view_states:
            self.remove_arrow_widget(av_state)

        for av_state in change.added.new_arrow_view_states:
            self.add_arrow_widget(av_state)
        for av_state in change.removed.new_arrow_view_states:
            self.remove_arrow_widget(av_state)

        self.update()

    def add_arrow_widget(self, av_state: ArrowViewState):
        subscription = misli.gui.channels.state_changes_by_id.subscribe(
            lambda change: self.handle_child_state_update(change),
            index_val=av_state.id)
        self.arrow_view_state_subs_by_state_id[av_state.id] = subscription

        arrow_widget = ArrowWidget(av_state, self)
        self._arrow_widgets[av_state.id] = arrow_widget

    def remove_arrow_widget(self, av_state: ArrowViewState):
        subscription = self.arrow_view_state_subs_by_state_id.pop(av_state.id)
        subscription.unsubscribe()
        arrow_widget = self._arrow_widgets.pop(av_state.id)
        arrow_widget.deleteLater()

    def add_note_widget(self, nv_state: NoteViewState):
        ViewType = pamet.note_view_type_by_state(type(nv_state).__name__)
        note_widget = ViewType(parent=self, initial_state=nv_state)
        note_widget.hide()
        self._note_widgets[nv_state.id] = note_widget

        subscription = misli.gui.channels.state_changes_by_id.subscribe(
            lambda change: self.handle_child_state_update(change),
            index_val=note_widget.id)
        self.nw_subscribtions[note_widget] = subscription
        # misli.call_delayed(self.on_child_updated, 0, args=[note_widget])

    def handle_child_state_update(self, change: Change):
        if change.is_update():
            entity = change.last_state()
            if isinstance(entity, NoteViewState):
                note_widget = self.note_widget_by_note_id(entity.gid())
                self.on_child_updated(note_widget.state())
            else:  # If it's an arrow
                self.update()

    def on_child_updated(self, note_view_state):
        nv_cache = self._note_widget_cache(note_view_state.id)
        nv_cache.should_rebuild_pcommand_cache = True
        nv_cache.should_rerender_image_cache = True
        nv_cache.should_reallocate_image_cache = True
        self.update()

    def remove_note_widget(self, note_widget):
        nw_state_id = note_widget.id
        self.delete_note_view_cache(nw_state_id)
        subscription = self.nw_subscribtions.pop(note_widget)
        subscription.unsubscribe()
        note_widget = self._note_widgets.pop(nw_state_id)
        note_widget.deleteLater()
        # self.update()

    def handle_page_child_change(self, change: Change):
        state = self.state()
        entity = change.last_state()
        if change.is_create():
            map_page_actions.handle_child_added(state, entity)

        elif change.is_delete():
            map_page_actions.handle_child_removed(state, entity)

        else:  # Updated
            if isinstance(entity, Note):
                if change.updated.type_name:
                    map_page_actions.handle_child_removed(state, entity)
                    map_page_actions.handle_child_added(state, entity)
                    return

                child_widget = self.note_widget_by_note_id(entity.gid())
                child_widget_state = child_widget.state()
            elif isinstance(entity, Arrow):
                child_widget_state = self.arrow_state_by_arrow_gid(
                    entity.gid())

            map_page_actions.handle_child_updated(child_widget_state, entity)

    def arrow_state_by_arrow_gid(self, arrow_gid: str) -> ArrowViewState:
        for av_state in self.state().arrow_view_states:
            if av_state.gid() == arrow_gid:
                return av_state
        return None

    def _note_widget_cache(self, note_view_id):
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

    def note_widget_by_note_id(self, note_gid):
        for nw_state_id, note_widget in self._note_widgets.items():
            if note_widget.state().note_gid == note_gid:
                return note_widget

    def arrow_widgets(self):
        for aw_id, arrow_widget in self._arrow_widgets.items():
            yield arrow_widget

    def prep_command_cache_for_child(self, child):
        # In order to be pixel perfect - relay through QPicture
        # Otherwise QWidget rounds up coordinates.
        # RIP 30 hours of trying other workarounds
        pcommand_cache = QPicture()

        child.render(pcommand_cache, QPoint(0, 0))

        nv_cache = self._note_widget_cache(child.id)
        nv_cache.pcommand_cache = pcommand_cache
        nv_cache.should_rebuild_pcommand_cache = False

    def _render_image_cache_for_child(self, child: View,
                                      display_rect: Rectangle):
        painter = QPainter()

        cache_rect = image_cache_rect_unprojected(display_rect)
        nv_cache = self._note_widget_cache(child.id)

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

        scale_factor = self.state().height_scale_factor()

        painter.translate(draw_point_x, draw_point_y)
        painter.scale(scale_factor, scale_factor)

        pcommand_cache.play(painter)
        painter.end()

        nv_cache = self._note_widget_cache(child.id)
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
        self_state = self.state()
        unprojected_viewport = self_state.unproject_rect(viewport_rect)

        display_rects_by_child_id = {}  # {nc_id: rect}
        for note_widget in self.note_widgets():
            nt_rect = note_widget.state().rect()

            if not nt_rect.intersects(unprojected_viewport):
                continue

            unprojected_rect = self_state.project_rect(nt_rect)
            display_rects_by_child_id[note_widget.id] = QRectF(
                *unprojected_rect.as_tuple())

        return display_rects_by_child_id

    def paintEvent(self, event):
        state: MapPageViewState = self.state()
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

        # Prep the unprojected mouse position to check if there's a note there
        q_mouse_pos = self.cursor().pos()
        unprojected_mouse_pos = self.state().unproject_point(
            Point2D(q_mouse_pos.x(), q_mouse_pos.y()))

        # Render the notes into a painter-commands-cache and an image cache
        # (prep only placeholders if slow)
        # At minimum renders one component into cache and preps placeholders
        for child_id, display_rect in display_rects_by_child_id.items():
            note_widget = self.note_widget(child_id)
            nw_cache = self._note_widget_cache(note_widget.id)

            if time.time() - paint_t0 > MAX_RENDER_TIME:
                paint_urgently = True

                if non_urgent_count >= MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT:
                    continue

            if nw_cache.should_rebuild_pcommand_cache:
                pc_cache_jobs += 1
                self.prep_command_cache_for_child(note_widget)

            # Allocate the image_cache. Done on resize, but not e.g. panning
            if nw_cache.should_reallocate_image_cache:
                image_cache_memory_allocations += 1
                cache_rect = image_cache_rect_unprojected(display_rect)

                render_img = QImage(cache_rect.size(),
                                    QImage.Format_ARGB32_Premultiplied)
                nw_cache.image_cache = render_img
                nw_cache.should_reallocate_image_cache = False

            if nw_cache.should_rerender_image_cache:
                render_to_image_jobs += 1
                non_urgent_count += 1

                self._render_image_cache_for_child(note_widget, display_rect)

            else:
                notes_reusing_cache += 1

        # Draw the cached images, along with various decorations
        for child_id, display_rect in display_rects_by_child_id.items():
            note_widget = self.note_widget(child_id)
            nw_cache = self._note_widget_cache(note_widget.id)

            render_img = nw_cache.image_cache

            nt_main_color = QColor(
                *note_widget.state().get_color().to_uint8_rgba_list())

            nt_background_color = QColor(*note_widget.state(
            ).get_background_color().to_uint8_rgba_list())

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

            if nw_cache.should_rebuild_pcommand_cache or \
               nw_cache.should_reallocate_image_cache or \
               nw_cache.should_rerender_image_cache:
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
            #     self.height_scale_factor(),
            #     self.height_scale_factor())
            # nv_cache.pcommand_cache.play(painter)
            # # Load test
            # for i in range(10):
            #     painter.drawPicture(i*50,i*50, nv_cache.pcommand_cache)
            # painter.restore()

            # # Test text
            # painter.save()
            # font = painter.font()
            # font.setPointSizeF(20 * self.height_scale_factor())
            # painter.setFont(font)
            # painter.drawText(cache_rect.topLeft() + QPoint(0, 0.5), 'Test')
            # painter.restore()

            if self.debug_drawing:
                painter.save()
                painter.setPen(Qt.NoPen)
                green_brush = QBrush(Qt.green, Qt.SolidPattern)
                painter.fillRect(display_rect, green_brush)
                painter.restore()

            # Draw the selection overlay and resize circle for selected notes
            if note_widget.id in state.selected_child_ids:
                # Draw a yellow selection overlay
                painter.fillRect(display_rect, selection_overlay_color)

                # Draw the resize circle
                center = display_rect.bottomRight()
                radius = RESIZE_CIRCLE_RADIUS
                radius *= self.state().height_scale_factor()

                circle_fill_color = QColor(nt_main_color)
                circle_fill_color.setAlpha(60)

                painter.save()
                painter.setBrush(QBrush(circle_fill_color, Qt.SolidPattern))

                painter.drawEllipse(center, radius, radius)
                painter.restore()

            # Draw lines for easier visual alignment
            if state.mode() in [
                    MapPageMode.NOTE_RESIZE, MapPageMode.NOTE_MOVE
            ]:
                if note_widget.id in state.selected_child_ids:
                    qdr = display_rect
                    dr = Rectangle(qdr.x(), qdr.y(), qdr.width(), qdr.height())
                    self._draw_guide_lines_for_child(dr, painter)

        # Draw arrows
        painter.save()
        scale_factor = state.height_scale_factor()
        dx, dy = state.unproject_point(Point2D(0, 0)).as_tuple()

        painter.scale(scale_factor, scale_factor)
        painter.translate(-dx, -dy)
        pen = painter.pen()
        for arrow_widget in self.arrow_widgets():
            av_state: ArrowViewState = arrow_widget.state()
            pen.setColor(QColor(*av_state.get_color().to_uint8_rgba_list()))
            pen.setWidthF(av_state.line_thickness)
            painter.setPen(pen)
            arrow_widget.render(painter)

        # Draw the selection overlays where needed
        for arrow_widget in self.arrow_widgets():
            if (arrow_widget.id not in state.selected_child_ids
                    and arrow_widget.id not in state.drag_selected_child_ids):
                continue
            pen.setColor(selection_overlay_color)
            pen.setWidthF(5)
            painter.setPen(pen)
            arrow_widget.render(painter)

        painter.restore()

        # Draw the drag select rectangle
        if state.mode() == MapPageMode.DRAG_SELECT:
            # Draw the selection rects
            drag_select_rect = QRectF(*state.drag_select_rect_props)
            painter.fillRect(drag_select_rect, DRAG_SELECT_COLOR)

            # Draw the selection overlays
            for nc_id in state.drag_selected_child_ids:
                if nc_id not in display_rects_by_child_id:
                    continue
                painter.fillRect(display_rects_by_child_id[nc_id],
                                 selection_overlay_color)
                # elif nc_id in self._arrow_widgets:
                # ^^ that gets done while drawing the arrows

        elif state.mode() == MapPageMode.CREATE_ARROW:
            pass

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
            self.left_mouse_double_click_event(
                Point2D(event.pos().x(),
                        event.pos().y()))

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15

        self.handle_mouse_scroll(steps)

    def resizeEvent(self, event):
        self.update()
        self.handle_resize_event(event.size().width(), event.size().height())

    def handle_right_mouse_press(self, position):
        ncs_under_mouse = self.get_note_views_at(position)
        menu_entries = {}

        mode = self.state().mode()

        if mode == MapPageMode.NONE:
            if ncs_under_mouse:
                map_page_actions.update_child_selections(
                    self.state(), {nv.id: True
                                   for nv in ncs_under_mouse})
                menu_entries['Edit note'] = commands.edit_selected_notes
            else:
                menu_entries['New note'] = commands.create_new_note

            menu_entries['New page'] = commands.create_new_page
            menu_entries['Create arrow'] = commands.start_arrow_creation

        else:
            if mode == MapPageMode.CREATE_ARROW:
                text = 'Cancel arrow creation'
                menu_entries[
                    text] = lambda: map_page_actions.abort_special_mode(
                        self.state())
            else:
                # If we're in another special mode - don't show the menu
                return

        # Open the context menu with the tab as its parent
        context_menu = ContextMenuWidget(self.parent(), entries=menu_entries)
        context_menu.popup_on_mouse_pos()

    def handle_esc_shortcut(self):
        if self.state().mode() != MapPageMode.NONE:
            map_page_actions.abort_special_mode(self.state())
