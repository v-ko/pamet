from dataclasses import field
from typing import List, Tuple

import math
from PySide6.QtCore import QObject, QPointF, QRectF, QSizeF
from PySide6.QtGui import QPainter, QPainterPath
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.entity_library.change import Change
from misli.gui import channels
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.view_library.view import View
from misli.gui.view_library.view_state import ViewState, view_state_type
from misli.logging import get_logger
import pamet

from pamet.model.arrow import BEZIER_CUBIC, Arrow

log = get_logger(__name__)

TAIL = 'tail'
HEAD = 'head'
ARROW_HAND_LENGTH = 10
ARROW_HAND_ANGLE = math.radians(25)


@view_state_type
class ArrowViewState(ViewState, Arrow):
    arrow_gid: str = None
    _curves: list = field(default_factory=list, init=False, repr=False)

    @property
    def curves(self):
        return self._curves

    def get_arrow(self):
        return pamet.find_one(gid=self.arrow_gid)

    def update_from_arrow(self, arrow: Arrow):
        self.replace(**arrow.asdict())
        self._curves = self.bezier_cubic_curves_params()

    def calculate_terminal_cp(self, terminal_point: Point2D,
                              adjacent_point: Point2D,
                              control_point_distance: float, anchor_type: str):
        if not anchor_type:
            k = control_point_distance / terminal_point.distance_to(
                adjacent_point)
            return terminal_point + (adjacent_point - terminal_point) * k
        else:
            raise NotImplementedError

    def bezier_cubic_curves_params(
        self,
        tail_point: Point2D = None,
        head_point: Point2D = None,
        control_point_distance: float = 10
    ) -> List[Tuple[Point2D, Point2D, Point2D, Point2D]]:
        """ Returns a list of curve parameters. Each set of parameters is a
        tuple in the form:
        (start_point, first_control_point, second_control point, end_point)
        The parameters tail_point and head_point can override the corresponding
        internal variables in order to accomodate for anchor position changes.
        """
        tail_point = tail_point or self.tail_point
        head_point = head_point or self.head_point
        curves = []

        # Handle the first control point of the first curve
        if self.mid_points:
            second_point = self.mid_points[0]
        else:
            second_point = head_point

        first_cp = self.calculate_terminal_cp(tail_point, second_point,
                                              control_point_distance,
                                              self.tail_anchor)

        # Add the second control point for the first curve
        # and all the middle curves (if any), excluding the last control point
        prev_point: Point2D = tail_point
        for idx, current_point in enumerate(self.mid_points):
            # if idx == 0:
            #     prev_point: Point2D = tail_point

            # If we're at the last point
            if (idx + 1) == len(self.mid_points):
                next_point = head_point
                # should_finish = True
            else:
                next_point = self.mid_points[idx + 1]

            # Calculate alpha (see the schematic for details)
            a = prev_point.distance_to(next_point)
            b = current_point.distance_to(next_point)
            c = prev_point.distance_to(current_point)
            beta = math.acos(a**2 + b**2 - c**2) / 2
            alpha = math.pi / 2 - beta  # In radians 90-beta

            # Calculate the second control point for the current curve
            k = control_point_distance / c
            z_prim: Point2D = current_point - k * (prev_point - current_point)
            second_control_point = z_prim.rotated(alpha, current_point)

            # Save the params
            curves.append(
                (prev_point, first_cp, second_control_point, current_point))

            # Calculate the first control point for the next curve
            # (mirrors the second cp of the last curve)
            k = control_point_distance / b
            q_prim = current_point - k * (next_point - current_point)
            first_cp = q_prim.rotated(-alpha, current_point)

            # if should_finish:
            #     current_point
            # else:
            prev_point = current_point

        if not self.mid_points:
            # Add the second control point for the last curve
            second_control_point = self.calculate_terminal_cp(
                head_point, tail_point, control_point_distance,
                self.head_anchor)
        else:
            # Add the second control point for the last curve
            second_control_point = self.calculate_terminal_cp(
                head_point, current_point, control_point_distance,
                self.head_anchor)

        curves.append((prev_point, first_cp, second_control_point, head_point))

        return curves


class ArrowView(View):
    def intersects_rect(self, rect: Rectangle) -> bool:
        raise NotImplementedError

    # def intersects_point(self, point: Point2D) -> bool:
    #     if not self._cached_path:
    #         return False

    #     selector_rect = Rectangle()
    #     selector_rect.set_size(SELECTOR_RECT_EDGE, SELECTOR_RECT_EDGE)
    #     selector_rect.move_center(point)

    #     return self.intersects_rect(selector_rect)


class ArrowWidget(QObject, ArrowView):

    def __init__(self, initial_state: ArrowViewState = None, parent=None):
        QObject.__init__(self, parent)
        ArrowView.__init__(self, initial_state)
        self.map_page = parent
        self._anchor_subs_by_name = {}
        self._cached_path = None

        bind_and_apply_state(self,
                             initial_state,
                             on_state_change=self.on_state_change)
        self.destroyed.connect(lambda: self.unsubscribe_all())

    def unsubscribe_all(self):
        for note_id in self._anchor_subs_by_name:
            self.unsubscribe_from_anchor(note_id)

    def subscribe_to_anchor(self, anchor_name: str, note_id: str):
        if anchor_name in self._anchor_subs_by_name:
            self.unsubscribe_from_anchor(anchor_name)

        map_page_state = self.map_page.state()
        note_view_state = map_page_state.view_state_for_note_id(note_id)
        sub = channels.state_changes_by_id.subscribe(
            handler=self.handle_anchor_view_state_change,
            index_val=note_view_state.id)
        self._anchor_subs_by_name[anchor_name] = sub

    def unsubscribe_from_anchor(self, anchor_name: str):
        if anchor_name not in self._anchor_subs_by_name:
            return
        sub = self._anchor_subs_by_name.pop(anchor_name)
        sub.unsubscribe()

    def handle_anchor_view_state_change(self, change):
        self.update_cached_path()

    def on_state_change(self, change: Change):
        # Update anchor note subscriptions
        state = change.last_state()
        if change.updated.tail_note_id:
            if state.tail_note_id:
                self.subscribe_to_anchor(TAIL, state.tail_note_id)
            else:
                self.unsubscribe_from_anchor(TAIL)

        if change.updated.head_note_id:
            if state.head_note_id:
                self.subscribe_to_anchor(HEAD, state.head_note_id)
            else:
                self.unsubscribe_from_anchor(HEAD)

        self.update_cached_path()

    def anchor_position_from_note(self, note, anchor_type):
        note_rect: Rectangle = note.rect()
        tail_anchor_pos = None
        if anchor_type == 'top':
            tail_anchor_pos = note_rect.top_left()
            tail_anchor_pos.set_x(tail_anchor_pos.x() + note_rect.width() / 2)
        if anchor_type == 'bottom':
            tail_anchor_pos = note_rect.bottom_left()
            tail_anchor_pos.set_x(tail_anchor_pos.x() + note_rect.width() / 2)
        if anchor_type == 'left':
            tail_anchor_pos = note_rect.top_left()
            tail_anchor_pos.set_x(tail_anchor_pos.y() + note_rect.height() / 2)
        if anchor_type == 'right':
            tail_anchor_pos = note_rect.top_right()
            tail_anchor_pos.set_x(tail_anchor_pos.y() + note_rect.height() / 2)

        return tail_anchor_pos

    def update_cached_path(self):
        state: ArrowViewState = self.state()
        parent_page = pamet.page(id=state.page_id)
        if state.tail_note_id:
            note = parent_page.note(id=state.tail_note_id)
            if not note:
                raise Exception
            if state.tail_anchor:
                tail_anchor_pos = self.anchor_position_from_note(
                    note, state.tail_anchor)
            else:
                raise NotImplementedError
        elif state.tail_point:
            tail_anchor_pos = state.tail_point
        else:
            # there should be either a position or an anchor set
            # if on init there's acceptable cases without - just return here
            return
            raise Exception

        if state.head_note_id:
            note = parent_page.note(id=state.head_note_id)
            if not note:
                raise Exception
            if state.head_anchor:
                head_anchor_pos = self.anchor_position_from_note(
                    note, state.head_anchor)
            else:
                raise NotImplementedError
        elif state.head_point:
            head_anchor_pos = state.head_point
        else:
            return
            raise Exception

        if tail_anchor_pos == head_anchor_pos:
            self._cached_path = None
            return

        if state.line_function_name == BEZIER_CUBIC:
            curves = state.bezier_cubic_curves_params(tail_anchor_pos,
                                                      head_anchor_pos)
            if not curves:
                raise Exception

            start_point = curves[0][0]
            start_point = QPointF(*start_point.as_tuple())
            self._cached_path = QPainterPath(start_point)
            for first_point, first_cp, second_cp, second_point in curves:
                first_point = QPointF(*first_point.as_tuple())
                first_cp = QPointF(*first_cp.as_tuple())
                second_cp = QPointF(*second_cp.as_tuple())
                second_point = QPointF(*second_point.as_tuple())

                self._cached_path.cubicTo(first_cp, second_cp, second_point)

        else:
            raise NotImplementedError

    def render(self, painter: QPainter):
        if not self._cached_path or not self._cached_path.elementCount():
            log.warning('Render called, but _cached_path is empty')
            return

        painter.drawPath(self._cached_path)

        # Draw the arrow head
        point95 = self._cached_path.pointAtPercent(0.95)
        point95 = Point2D(point95.x(), point95.y())
        end_point = self._cached_path.pointAtPercent(1)
        end_point = Point2D(end_point.x(), end_point.y())

        normalized_vec = (end_point - point95) / point95.distance_to(end_point)
        arrow_hand_base = end_point - ARROW_HAND_LENGTH * normalized_vec
        hand_end = arrow_hand_base.rotated(ARROW_HAND_ANGLE, end_point)
        hand_end2 = arrow_hand_base.rotated(-ARROW_HAND_ANGLE, end_point)

        end_point = QPointF(*end_point.as_tuple())
        hand_end = QPointF(*hand_end.as_tuple())
        hand_end2 = QPointF(*hand_end2.as_tuple())
        painter.drawLine(end_point, hand_end)
        painter.drawLine(end_point, hand_end2)

    def intersects_rect(self, rect: Rectangle) -> bool:
        if not self._cached_path:
            return False

        selector_rect = QRectF(*rect.as_tuple())
        return self._cached_path.intersects(selector_rect)

    # def mousePressEvent(self, event: QMouseEvent) -> None:
    #     os.system(f'notify-send click')
    #     return super().mousePressEvent(event)