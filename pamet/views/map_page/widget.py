from copy import copy
import time
from typing import Dict, List

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QPointF, Qt, QPoint, QTimer, QRectF
from PySide6.QtGui import QKeyEvent, QPainter, QPicture, QImage, QColor, QBrush, QCursor
from PySide6.QtGui import QKeySequence, QShortcut

import fusion
from fusion.util import Point2D, Rectangle
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View
from fusion.platform.qt_widgets.views.context_menu.widget import ContextMenuWidget
from fusion import fsm as fsm

from pamet import commands
from pamet.constants import ARROW_EDGE_RAIDUS, MAX_RENDER_TIME
from pamet.constants import ALIGNMENT_LINE_LENGTH, RESIZE_CIRCLE_RADIUS
from pamet.constants import LONG_PRESS_TIMEOUT

import pamet
from pamet import actions
from pamet.desktop_app import selection_overlay_qcolor
from pamet.actions import map_page as map_page_actions
from pamet.desktop_app.util import control_is_pressed
from pamet.model.arrow import Arrow, ArrowAnchorType
from pamet.model.note import Note
from pamet.util import snap_to_grid
from pamet.views.arrow.widget import ArrowView, ArrowViewState, ArrowWidget
from pamet.views.map_page.view import MapPageView
from pamet.views.map_page.state import MapPageViewState, MapPageMode

from fusion.libs.entity.change import Change
from pamet.views.note.base.state import NoteViewState

log = fusion.get_logger(__name__)

IMAGE_CACHE_PADDING = 1
MIN_FULL_CHILD_RENDERS_PER_PAINT_EVENT = 10
DRAG_SELECT_COLOR = QColor(100, 100, 100, 50)


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

        # Local variables
        self._cache_per_nc_view_id = {}
        self._paint_event_count = 0
        self.debug_drawing = False
        self._mouse_press_position = QPoint()
        self._note_widgets = {}
        self._arrow_widgets: Dict[str, ArrowWidget] = {}
        self._clipboard_outlines_shown = False

        # Setup shortcuts
        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.handle_delete_shortcut)

        color_notes_blue = QShortcut(QKeySequence('1'), self)
        color_notes_blue.activated.connect(
            lambda: actions.map_page.color_selected_children(
                self.state(),
                color=[0, 0, 1, 1],
                background_color=[0, 0, 1, 0.1]))
        color_notes_green = QShortcut(QKeySequence('2'), self)
        color_notes_green.activated.connect(
            lambda: actions.map_page.color_selected_children(
                self.state(),
                color=[0, 0.64, 0.235, 1],
                background_color=[0, 1, 0, 0.1]))
        color_notes_red = QShortcut(QKeySequence('3'), self)
        color_notes_red.activated.connect(
            lambda: actions.map_page.color_selected_children(
                self.state(),
                color=[1, 0, 0, 1],
                background_color=[1, 0, 0, 0.1]))
        color_notes_gray = QShortcut(QKeySequence('4'), self)
        color_notes_gray.activated.connect(
            lambda: actions.map_page.color_selected_children(
                self.state(),
                color=[0, 0, 0, 1],
                background_color=[0, 0, 0, 0.1]))
        remove_note_background = QShortcut(QKeySequence('5'), self)
        remove_note_background.activated.connect(
            lambda: actions.map_page.color_selected_children(
                self.state(), background_color=[0, 0, 0, 0]))
        select_all_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_A), self)
        select_all_shortcut.activated.connect(
            lambda: actions.map_page.select_all_notes(self.state()))
        QShortcut(QKeySequence(Qt.Key_E), self, commands.edit_selected_notes)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_E), self,
                  commands.open_page_properties)
        QShortcut(QKeySequence(Qt.Key_L), self, commands.start_arrow_creation)
        # QShortcut(QKeySequence(Qt.Key_Escape), self, self.handle_esc_shortcut,
        #           Qt.WidgetShortcut)
        QShortcut(
            QKeySequence(Qt.Key_A), self,
            lambda: map_page_actions.autosize_selected_notes(self.state()))
        QShortcut(QKeySequence('ctrl+Z'), self,
                  lambda: map_page_actions.undo(self.state()))
        QShortcut(QKeySequence('ctrl+shift+Z'), self,
                  lambda: map_page_actions.redo(self.state()))
        QShortcut(QKeySequence('ctrl+'), self,
                  lambda: map_page_actions.redo(self.state()))
        QShortcut(QKeySequence('ctrl+C'), self, commands.copy)
        QShortcut(QKeySequence('ctrl+V'), self, commands.paste)
        QShortcut(QKeySequence('ctrl+X'), self, commands.cut)
        QShortcut(QKeySequence('ctrl+shift+V'), self, commands.paste_special)

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
        self.arrow_view_state_subs_by_view_id = {}
        self.new_arrow_view_state_subs_by_state_id = {}

        # Subscribe to the page changes
        self.subscriptions.append(
            pamet.channels.entity_changes_by_id.subscribe(
                self.handle_page_change, index_val=self.state().page_id))
        # Subscribe to note changes
        self.subscriptions.append(
            pamet.channels.entity_changes_by_parent_gid.subscribe(
                self.handle_page_child_change, index_val=self.state().page_id))

        self.destroyed.connect(lambda: self.unsubscribe_all())

        bind_and_apply_state(self,
                             initial_state,
                             on_state_change=self.on_state_change)

    def handle_page_change(self, change: Change):
        if change.updated.name:
            map_page_actions.handle_page_name_updated(self.parent_tab.state(),
                                                      change.last_state())

    def unsubscribe_all(self):
        for subscription in self.subscriptions:
            subscription.unsubscribe()

        for nw, subscription in self.nw_subscribtions.items():
            subscription.unsubscribe()

        for avs_id, sub in self.arrow_view_state_subs_by_view_id.items():
            sub.unsubscribe()

    def note_views(self) -> List[View]:
        yield from self.note_widgets()

    def arrow_views(self) -> List[ArrowView]:
        yield from self.arrow_widgets()

    def on_state_change(self, change: Change):
        state = change.last_state()
        if change.updated.viewport_height:
            # Invalidate image_cache for all children
            for child in self.note_widgets():
                nv_cache = self._note_widget_cache(child.view_id)
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
            note_widget = self.note_widget(nv_state.view_id)
            if note_widget:
                # Don't fail if it's missing. When changing type - we delete
                # the note widget immediately (in order to avoid it handling
                # a note type it wasn't supposed to)
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
        try:
            arrow_widget = ArrowWidget(av_state, self)
        except Exception as e:
            pamet.entity_broke(av_state, e)
            return

        self._arrow_widgets[av_state.view_id] = arrow_widget

        subscription = fsm.state_changes_per_TLA_by_view_id.subscribe(
            lambda change: self.handle_child_view_state_update(change),
            index_val=av_state.view_id)
        self.arrow_view_state_subs_by_view_id[av_state.view_id] = subscription

    def remove_arrow_widget(self, av_state: ArrowViewState):
        subscription = self.arrow_view_state_subs_by_view_id.pop(
            av_state.view_id)
        subscription.unsubscribe()
        arrow_widget = self._arrow_widgets.pop(av_state.view_id)
        arrow_widget.deleteLater()

    def add_note_widget(self, nv_state: NoteViewState):
        try:
            ViewType = pamet.note_view_type_by_state(type(nv_state).__name__)
            note_widget = ViewType(parent=self, initial_state=nv_state)
        except Exception as e:
            pamet.entity_broke(nv_state, e)
            return

        note_widget.hide()
        self._note_widgets[nv_state.view_id] = note_widget

        subscription = fsm.state_changes_per_TLA_by_view_id.subscribe(
            lambda change: self.handle_child_view_state_update(change),
            index_val=note_widget.view_id)
        self.nw_subscribtions[note_widget] = subscription
        self.update()

    def remove_note_widget(self, note_widget):
        nw_view_id = note_widget.view_id
        self.delete_note_view_cache(nw_view_id)
        subscription = self.nw_subscribtions.pop(note_widget)
        subscription.unsubscribe()
        note_widget = self._note_widgets.pop(nw_view_id)
        note_widget.deleteLater()
        self.update()

    def handle_child_view_state_update(self, change: Change):
        entity = change.last_state()
        if change.is_update():
            if isinstance(entity, NoteViewState):
                self.on_child_updated(change)
            else:  # If it's an arrow
                self.update()

        elif change.is_create():
            if isinstance(entity, NoteViewState):
                pass
                # self.on_child_updated(change)
            else:  # If it's an arrow
                self.update()

    def on_child_updated(self, change: Change):
        if not change.is_update():
            raise Exception

        nv_cache = self._note_widget_cache(change.new_state.view_id)

        if change.updated.geometry:
            if change.old_state.rect().size() != change.new_state.rect().size(
            ):
                nv_cache.should_rebuild_pcommand_cache = True
                nv_cache.should_reallocate_image_cache = True
                nv_cache.should_rerender_image_cache = True

        if change.updated.content:
            nv_cache.should_rebuild_pcommand_cache = True
            nv_cache.should_rerender_image_cache = True

        if change.updated.color or change.updated.background_color:
            nv_cache.should_rebuild_pcommand_cache = True
            nv_cache.should_rerender_image_cache = True

        self.update()

    def handle_page_child_change(self, change: Change):
        self_state = self.state()
        child = change.last_state()
        if change.is_create():
            map_page_actions.handle_child_added(self_state, child)

        elif change.is_delete():
            map_page_actions.handle_child_removed(self_state, child)

        else:  # Updated
            if isinstance(child, Note):
                if type(change.old_state) != type(change.new_state):
                    note_widget = self.note_widget_by_note_gid(child.gid())
                    self.remove_note_widget(note_widget)
                    map_page_actions.handle_child_removed(self_state, child)
                    map_page_actions.handle_child_added(self_state, child)
                    return

                child_widget = self.note_widget_by_note_gid(child.gid())
                child_widget_state = child_widget.state()
            elif isinstance(child, Arrow):
                child_widget_state = self.arrow_state_by_arrow_gid(child.gid())

            map_page_actions.handle_child_updated(child_widget_state, child)

    def arrow_state_by_arrow_gid(self, arrow_gid: str) -> ArrowViewState:
        for av_state in self.state().arrow_view_states:
            if av_state.gid() == arrow_gid:
                return av_state
        return None

    def _note_widget_cache(self, note_view_id):
        if note_view_id not in self._cache_per_nc_view_id:
            self._cache_per_nc_view_id[note_view_id] = NoteViewCache()

        return self._cache_per_nc_view_id[note_view_id]

    def delete_note_view_cache(self, note_view_id):
        if note_view_id not in self._cache_per_nc_view_id:
            return
        del self._cache_per_nc_view_id[note_view_id]

    def note_widgets(self):
        for nw_id, note_widget in self._note_widgets.items():
            yield note_widget

    def note_widget(self, view_Id):
        return self._note_widgets.get(view_Id, None)

    def note_widget_by_note_gid(self, note_gid):
        for nw_state_id, note_widget in self._note_widgets.items():
            if note_widget.state().note_gid == note_gid:
                return note_widget
        return None

    def arrow_widgets(self):
        for aw_id, arrow_widget in self._arrow_widgets.items():
            yield arrow_widget

    def arrow_widget(self, state_id: str):
        return self._arrow_widgets[state_id]

    def prep_command_cache_for_child(self, child):
        # In order to be pixel perfect - relay through QPicture
        # Otherwise QWidget rounds up coordinates.
        # RIP 30 hours of trying other workarounds
        pcommand_cache = QPicture()

        child.render(pcommand_cache, QPoint(0, 0))

        nv_cache = self._note_widget_cache(child.view_id)
        nv_cache.pcommand_cache = pcommand_cache
        nv_cache.should_rebuild_pcommand_cache = False

    def _render_image_cache_for_child(self, child: View,
                                      display_rect: Rectangle):
        painter = QPainter()

        cache_rect = image_cache_rect_unprojected(display_rect)
        nv_cache = self._note_widget_cache(child.view_id)

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

        nv_cache = self._note_widget_cache(child.view_id)
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

    def _visible_display_rects_by_view_id(self):
        viewport_rect = Rectangle(self.rect().x(),
                                  self.rect().y(),
                                  self.rect().width(),
                                  self.rect().height())
        self_state = self.state()
        unprojected_viewport = self_state.unproject_rect(viewport_rect)

        display_rects_by_child_view_id = {}  # {nc_id: rect}
        for note_widget in self.note_widgets():
            nt_rect = note_widget.state().rect()

            if not nt_rect.intersects(unprojected_viewport):
                continue

            unprojected_rect = self_state.project_rect(nt_rect)
            display_rects_by_child_view_id[note_widget.view_id] = QRectF(
                *unprojected_rect.as_tuple())

        return display_rects_by_child_view_id

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
        display_rects_by_view_id = self._visible_display_rects_by_view_id()

        # Prep the unprojected mouse position to check if there's a note there
        q_mouse_pos = self.mapFromGlobal(self.cursor().pos())
        mouse_pos = Point2D(q_mouse_pos.x(), q_mouse_pos.y())
        unprojected_mouse_pos = self.state().unproject_point(mouse_pos)

        # Render the notes into a painter-commands-cache and an image cache
        # (prep only placeholders if slow)
        # At minimum renders one component into cache and preps placeholders
        for child_view_id, display_rect in display_rects_by_view_id.items():
            note_widget = self.note_widget(child_view_id)
            nw_cache = self._note_widget_cache(note_widget.view_id)

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
        for child_view_id, display_rect in display_rects_by_view_id.items():
            note_widget = self.note_widget(child_view_id)
            nw_cache = self._note_widget_cache(note_widget.view_id)
            note_vs = note_widget.state()

            render_img = nw_cache.image_cache

            nt_main_color = QColor(*note_vs.get_color().to_uint8_rgba_list())

            nt_background_color = QColor(
                *note_vs.get_background_color().to_uint8_rgba_list())

            nt_background_brush = QBrush(nt_background_color, Qt.SolidPattern)

            painter.setPen(nt_main_color)
            painter.setBrush(nt_background_brush)

            # Draw placeholders where the note has not been rendered
            if not render_img:
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
            if note_widget.state() in state.selected_children:
                # Draw a yellow selection overlay
                painter.fillRect(display_rect, selection_overlay_qcolor)

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
                    MapPageMode.NOTE_RESIZE, MapPageMode.CHILD_MOVE
            ]:
                if note_widget.state() in state.selected_children:
                    qdr = display_rect
                    dr = Rectangle(qdr.x(), qdr.y(), qdr.width(), qdr.height())
                    self._draw_guide_lines_for_child(dr, painter)

        # Draw arrows and their selection overlays
        painter.save()
        scale_factor = state.height_scale_factor()
        dx, dy = state.unproject_point(Point2D(0, 0)).as_tuple()

        painter.scale(scale_factor, scale_factor)
        painter.translate(-dx, -dy)

        # Draw the arrows
        for arrow_widget in self.arrow_widgets():
            draw_selection_overlay = False
            arrow_widget_state = arrow_widget.state()
            if (arrow_widget_state in state.selected_children
                    or arrow_widget_state in state.drag_selected_children):
                draw_selection_overlay = True

            draw_control_points = False
            if state.arrow_with_visible_cps:
                if state.arrow_with_visible_cps == arrow_widget_state:
                    draw_control_points = True

            arrow_widget.render(painter, draw_selection_overlay,
                                draw_control_points)

        painter.restore()
        # End of the arrow drawing

        # Draw the drag select rectangle
        if state.mode() == MapPageMode.DRAG_SELECT:
            # Draw the selection rects
            drag_select_rect = QRectF(*state.drag_select_rect_props)
            painter.fillRect(drag_select_rect, DRAG_SELECT_COLOR)

            # Draw the selection overlays
            for note_view_state in state.drag_selected_children:
                if note_view_state.view_id not in display_rects_by_view_id:
                    continue
                painter.fillRect(
                    display_rects_by_view_id[note_view_state.view_id],
                    selection_overlay_qcolor)
                # elif nc_id in self._arrow_widgets:
                # ^^ that gets done while drawing the arrows

        elif state.mode() in [
                MapPageMode.CREATE_ARROW, MapPageMode.ARROW_EDGE_DRAG
        ]:
            # Draw the anchors for the notes under/close to the mouse
            for note_widget in self.get_note_views_at(mouse_pos,
                                                      ARROW_EDGE_RAIDUS):
                note_vs = note_widget.state()
                for anchor_type in ArrowAnchorType.real_types():
                    arr_anchor_pos = note_vs.arrow_anchor(anchor_type)
                    arr_anchor_pos = state.project_point(arr_anchor_pos)
                    radius = ARROW_EDGE_RAIDUS * state.height_scale_factor()

                    q_anchor_pos = QPointF(*arr_anchor_pos.as_tuple())
                    nt_main_color = QColor(
                        *note_vs.get_color().to_uint8_rgba_list())

                    nt_background_color = QColor(
                        *note_vs.get_background_color().to_uint8_rgba_list())

                    nt_background_brush = QBrush(nt_background_color,
                                                 Qt.SolidPattern)

                    painter.setPen(nt_main_color)
                    painter.setBrush(nt_background_brush)

                    # q_proj_mouse = QPointF(
                    #     *state.project_point(unprojected_mouse_pos).as_tuple())
                    # painter.drawEllipse(q_proj_mouse, 100, 100)
                    # painter.drawEllipse(q_mouse_pos, 100, 100)
                    painter.drawEllipse(q_anchor_pos, radius, radius)

        # Draw the clipboard outlines if control is pressed
        if control_is_pressed():
            self._clipboard_outlines_shown = True
            for note in pamet.clipboard.get_contents():
                if not isinstance(note, Note):
                    continue
                nt_main_color = QColor(*note.get_color().to_uint8_rgba_list())
                painter.setPen(nt_main_color)
                painter.setBrush(Qt.NoBrush)
                rect = note.rect()
                rect.set_top_left(
                    snap_to_grid(unprojected_mouse_pos + rect.top_left()))
                rect = state.project_rect(rect)
                painter.drawRect(QRectF(*rect.as_tuple()))

        # Report stats
        notes_on_screen = len(display_rects_by_view_id)

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
        mouse_pos = Point2D(event.pos().x(), event.pos().y())
        state = self.state()

        QTimer.singleShot(LONG_PRESS_TIMEOUT * 1000, self.check_for_long_press)

        if event.button() is Qt.LeftButton:

            # If there's an arrow selected
            # check if an arrow edge is under the mouse

            if state.arrow_with_visible_cps:
                arrow_widget = self.arrow_widget(
                    state.arrow_with_visible_cps.view_id)

                edge_under_mouse_idx = arrow_widget.edge_at(mouse_pos)
                if edge_under_mouse_idx is not None:
                    map_page_actions.start_arrow_edge_drag(
                        state, mouse_pos, edge_under_mouse_idx)
                    return

            self.handle_left_mouse_press(mouse_pos)

        elif event.button() is Qt.RightButton:
            self.handle_right_mouse_press(
                Point2D(event.pos().x(),
                        event.pos().y()))

    def mouseReleaseEvent(self, event):
        mouse_pos = Point2D(event.pos().x(), event.pos().y())
        if event.button() is Qt.LeftButton:
            self.handle_left_mouse_release(mouse_pos)

        elif event.button() is Qt.MiddleButton:
            self.middle_click_event(mouse_pos)

    def mouseMoveEvent(self, event):
        old_nvs_under_mouse = copy(self._note_views_under_mouse)
        self.handle_mouse_move(Point2D(event.pos().x(), event.pos().y()))

        if self._note_views_under_mouse != old_nvs_under_mouse:
            if self.state().mode() == MapPageMode.CREATE_ARROW:
                self.update()

        # Prompt updates for the clipboard outline visualization
        if control_is_pressed():
            self.update()

    def mouseDoubleClickEvent(self, event):
        mouse_pos = Point2D(event.pos().x(), event.pos().y())
        state = self.state()

        if event.button() is Qt.LeftButton:
            if state.arrow_with_visible_cps:
                arrow_widget = self.arrow_widget(
                    state.arrow_with_visible_cps.view_id)

                edge_under_mouse_idx = arrow_widget.edge_at(mouse_pos)
                if edge_under_mouse_idx is not None:
                    map_page_actions.delete_arrow_edge(
                        state.arrow_with_visible_cps, edge_under_mouse_idx)
                    return

            self.left_mouse_double_click_event(
                Point2D(event.pos().x(),
                        event.pos().y()))

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15

        self.handle_mouse_scroll(steps)

    def resizeEvent(self, event):
        self.update()
        new_size = Point2D(event.size().width(), event.size().height())
        self.handle_resize_event(new_size)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # For the clipboard outline visualizations
        if event.key() == Qt.Key_Control:
            self.update()
        return super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        # For the clipboard outline visualizations
        if event.key() == Qt.Key_Control:
            self.update()
        return super().keyReleaseEvent(event)

    def handle_right_mouse_press(self, position):
        ncs_under_mouse = list(self.get_note_views_at(position))
        menu_entries = {}

        mode = self.state().mode()

        if mode == MapPageMode.NONE:
            if ncs_under_mouse:
                map_page_actions.update_child_selections(
                    self.state(), {nv: True
                                   for nv in ncs_under_mouse})
                menu_entries['Edit note'] = commands.edit_selected_notes
                menu_entries['Copy'] = commands.copy
                if pamet.clipboard.get_contents():
                    menu_entries['Paste'] = commands.paste
                menu_entries['Cut'] = commands.cut
            else:
                menu_entries['New note'] = commands.create_new_note

            menu_entries['Paste special'] = commands.paste_special
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

    def update_undo_redo_buttons_enabled(self):
        pass
