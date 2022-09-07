from copy import copy
from typing import List, Tuple, Union

import math
from PySide6.QtCore import QObject, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath

from fusion import fsm
from fusion.util.point2d import Point2D
from fusion.util.rectangle import Rectangle
from fusion.libs.entity.change import Change
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View
from fusion.libs.state import ViewState, view_state_type
from fusion.logging import get_logger
import pamet
from pamet.desktop_app import selection_overlay_qcolor
from pamet.constants import ARROW_EDGE_RAIDUS, ARROW_SELECTION_THICKNESS_DELTA, CONTROL_POINT_RADIUS, POTENTIAL_EDGE_RADIUS

from pamet.model.arrow import BEZIER_CUBIC, Arrow, ArrowAnchorType

log = get_logger(__name__)

CONTROL_POINT_DEBUG_VISUALS = False

TAIL = 'tail'
HEAD = 'head'
ARROW_HAND_LENGTH = 20
ARROW_HAND_ANGLE = math.radians(25)
CP_BASE_DISTANCE = 80
CP_DIST_SEGMENT_ADJUST_K = 0.1


def special_sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x / (CP_BASE_DISTANCE / 2) + 5))


@view_state_type
class ArrowViewState(Arrow, ViewState):

    @property
    def arrow_gid(self):  # TODO: remove
        return self.id

    def get_arrow(self):
        return pamet.find_one(gid=self.arrow_gid)

    def update_from_arrow(self, arrow: Arrow):
        arrow_dict = arrow.asdict()
        assert self.id == arrow_dict.pop('id')
        self.replace(**arrow_dict)


class ArrowView(View):

    def intersects_rect(self, rect: Rectangle) -> bool:
        raise NotImplementedError

    def intersects_circle(self, center: Point2D, radius: float) -> bool:
        raise NotImplementedError


class ArrowWidget(QObject, ArrowView):

    def __init__(self, initial_state: ArrowViewState = None, parent=None):
        QObject.__init__(self, parent)
        ArrowView.__init__(self, initial_state)
        self.map_page_view = parent
        self._anchor_subs_by_note_id = {}
        self._cached_curves = None
        self._cached_path = None

        bind_and_apply_state(self,
                             initial_state,
                             on_state_change=self.on_state_change)
        self.destroyed.connect(lambda: self.unsubscribe_all())

    def unsubscribe_all(self):
        for note_id in copy(self._anchor_subs_by_note_id):
            self.unsubscribe_from_anchor(note_id)

    def update_anchor_subscriptions(self):
        state = self.state()
        new_ids = set()
        if state.tail_note_id:
            new_ids.add(state.tail_note_id)
        if state.head_note_id:
            new_ids.add(state.head_note_id)

        old_ids = set(self._anchor_subs_by_note_id.keys())
        new_subs = new_ids - old_ids
        subs_for_removal = old_ids - new_ids

        for note_id in subs_for_removal:
            self.unsubscribe_from_anchor(note_id)

        for note_id in new_subs:
            self.subscribe_to_anchor(note_id)

    def subscribe_to_anchor(self, note_own_id: str):
        # Clear the previous subscription
        if note_own_id in self._anchor_subs_by_note_id:
            self.unsubscribe_from_anchor(note_own_id)

        map_page_state = self.map_page_view.state()
        note_view_state = map_page_state.view_state_for_note_own_id(note_own_id)
        if not note_view_state:
            raise Exception('Anchor note with own id {note_own_id} not found')

        sub = fsm.state_changes_per_TLA_by_view_id.subscribe(
            handler=self.handle_anchor_note_view_state_change,
            index_val=note_view_state.view_id)
        self._anchor_subs_by_note_id[note_own_id] = sub

    def unsubscribe_from_anchor(self, note_own_id: str):
        if note_own_id not in self._anchor_subs_by_note_id:
            return
        sub = self._anchor_subs_by_note_id.pop(note_own_id)
        sub.unsubscribe()

    def handle_anchor_note_view_state_change(self, change):
        if change.is_delete():
            return  # The arrow should be deleted along the deleted note
        self.update_cached_path()

    def on_state_change(self, change: Change):
        # Update anchor note subscriptions
        if change.updated.tail_note_id or change.updated.head_note_id:
            self.update_anchor_subscriptions()

        if not change.is_delete():
            self.update_cached_path()

    def calculate_terminal_cp(self, terminal_point: Point2D,
                              adjacent_point: Point2D,
                              control_point_distance: float,
                              anchor_type: ArrowAnchorType):
        if anchor_type == ArrowAnchorType.NONE:
            k = control_point_distance / terminal_point.distance_to(
                adjacent_point)
            return terminal_point + (adjacent_point - terminal_point) * k
        elif anchor_type == ArrowAnchorType.MID_LEFT:
            return terminal_point - Point2D(control_point_distance, 0)
        elif anchor_type == ArrowAnchorType.TOP_MID:
            return terminal_point - Point2D(0, control_point_distance)
        elif anchor_type == ArrowAnchorType.MID_RIGHT:
            return terminal_point + Point2D(control_point_distance, 0)
        elif anchor_type == ArrowAnchorType.BOTTOM_MID:
            return terminal_point + Point2D(0, control_point_distance)
        else:
            raise Exception

    def infer_arrow_anchor_type(self, adjacent_point: Point2D,
                                note_rect: Rectangle):
        # If the adjacent point is to the left or right - set a side anchor
        if adjacent_point.x() < note_rect.left():
            return ArrowAnchorType.MID_LEFT
        elif adjacent_point.x() > note_rect.right():
            return ArrowAnchorType.MID_RIGHT
        else:
            # If the point is directly above or below the note - set a
            # top/bottom anchor
            if adjacent_point.y() < note_rect.top():
                return ArrowAnchorType.TOP_MID
            elif adjacent_point.y() > note_rect.bottom():
                return ArrowAnchorType.BOTTOM_MID
            else:
                # If the adjacent point is inside the note_rect - set either
                # a top or bottom anchor (arbitrary, its ugly either way)
                if adjacent_point.y() < note_rect.center():
                    return ArrowAnchorType.TOP_MID
                else:
                    return ArrowAnchorType.BOTTOM_MID

    def cp_distance_for_segment(self, first_point, second_point):
        dist = first_point.distance_to(second_point)

        return (special_sigmoid(dist) * CP_BASE_DISTANCE +
                CP_DIST_SEGMENT_ADJUST_K * dist)

    def bezier_cubic_curves_params(
        self,
        tail_point: Point2D = None,
        head_point: Point2D = None
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
        state = self.state()

        # Handle the first control point of the first curve
        if state.mid_points:
            second_point = state.mid_points[0]
        else:
            second_point = head_point

        # If the anchor type is AUTO - infer it
        if (state.has_tail_anchor()
                and state.tail_anchor_type == ArrowAnchorType.AUTO):
            tail_note = pamet.note(state.page_id, state.tail_note_id)
            note_view = self.map_page_view.note_widget_by_note_gid(
                tail_note.gid())

            tail_anchor_type = self.infer_arrow_anchor_type(
                second_point, note_view.rect())
        else:
            tail_anchor_type = state.tail_anchor_type

        control_point_distance = self.cp_distance_for_segment(
            tail_point, second_point)

        first_cp = self.calculate_terminal_cp(tail_point, second_point,
                                              control_point_distance,
                                              tail_anchor_type)

        # Add the second control point for the first curve
        # and all the middle curves (if any), excluding the last control point
        prev_point: Point2D = tail_point
        for idx, current_point in enumerate(state.mid_points):
            # if idx == 0:
            #     prev_point: Point2D = tail_point

            # If we're at the last point
            if (idx + 1) == len(state.mid_points):
                next_point = head_point
                # should_finish = True
            else:
                next_point = state.mid_points[idx + 1]

            # Calculate alpha (see the schematic for details)
            a = current_point.distance_to(next_point)
            b = prev_point.distance_to(current_point)
            # c = prev_point.distance_to(next_point)
            # beta = math.acos((a**2 + b**2 - c**2) / (a * b * 2))
            dA = prev_point - current_point
            dB = next_point - current_point
            gamma = math.atan2(dA.y(), dA.x())
            theta = math.atan2(dB.y(), dB.x())
            if gamma < 0:
                gamma += math.pi * 2
            if theta < 0:
                theta += math.pi * 2
            beta = (math.pi * 2 + theta - gamma) if gamma > theta else (theta -
                                                                        gamma)
            alpha = math.pi / 2 - beta / 2  # In radians 90 - beta/2

            control_point_distance = self.cp_distance_for_segment(
                prev_point, current_point)

            # Calculate the second control point for the first curve
            if b == 0:
                b = 0.0001
            k = control_point_distance / b
            z_prim: Point2D = current_point + k * (prev_point - current_point)
            second_control_point = z_prim.rotated(alpha, current_point)
            # second_control_point = z_prim
            # second_control_point = current_point + Point2D(50, 50)

            # Save the params
            curves.append(
                (prev_point, first_cp, second_control_point, current_point))

            # Calculate the first control point for the second curve
            # (mirrors the second cp of the last curve)
            control_point_distance = self.cp_distance_for_segment(
                current_point, next_point)
            if a == 0:
                a = 0.0001
            k = control_point_distance / a
            q_prim = current_point + k * (next_point - current_point)
            first_cp = q_prim.rotated(-alpha, current_point)

            prev_point = current_point

        # If the anchor type is AUTO - infer it
        if (state.has_head_anchor()
                and state.head_anchor_type == ArrowAnchorType.AUTO):
            head_note = pamet.note(state.page_id, state.head_note_id)
            note_view = self.map_page_view.note_widget_by_note_gid(
                head_note.gid())

            head_anchor_type = self.infer_arrow_anchor_type(
                second_point, note_view.rect())
        else:
            head_anchor_type = state.head_anchor_type

        if not state.mid_points:
            # Add the second control point for the last curve
            last_control_point = self.calculate_terminal_cp(
                head_point, tail_point, control_point_distance,
                head_anchor_type)
        else:
            # Add the second control point for the last curve
            last_control_point = self.calculate_terminal_cp(
                head_point, current_point, control_point_distance,
                head_anchor_type)

        curves.append((prev_point, first_cp, last_control_point, head_point))

        return curves

    def update_cached_path(self):
        state: ArrowViewState = self.state()
        if state.has_tail_anchor():
            tail_note = pamet.note(state.page_id, state.tail_note_id)
            nv_state = self.map_page_view.get_note_view_state_for_note_gid(
                tail_note.gid())
            if not nv_state:
                raise Exception
            if state.tail_anchor:
                tail_anchor_pos = nv_state.arrow_anchor(state.tail_anchor_type)
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
            head_note = pamet.note(state.page_id, state.head_note_id)
            nv_state = self.map_page_view.get_note_view_state_for_note_gid(
                head_note.gid())
            if not nv_state:
                raise Exception
            if state.head_anchor:
                head_anchor_pos = nv_state.arrow_anchor(state.head_anchor_type)
            else:
                raise NotImplementedError
        elif state.head_point:
            head_anchor_pos = state.head_point
        else:
            # there should be either a position or an anchor set
            # if on init there's acceptable cases without - just return here
            return

        if tail_anchor_pos == head_anchor_pos:
            self._cached_path = None
            return

        if state.line_function_name == BEZIER_CUBIC:
            curves = self.bezier_cubic_curves_params(tail_anchor_pos,
                                                     head_anchor_pos)
            if not curves:
                raise Exception

            self._cached_curves = curves

            start_point = curves[0][0]
            start_point = QPointF(*start_point.as_tuple())
            self._cached_path = QPainterPath(start_point)
            # curves.extend(reversed([reversed(c) for c in curves]))
            for first_point, first_cp, second_cp, second_point in curves:
                first_point = QPointF(*first_point.as_tuple())
                first_cp = QPointF(*first_cp.as_tuple())
                second_cp = QPointF(*second_cp.as_tuple())
                second_point = QPointF(*second_point.as_tuple())

                self._cached_path.cubicTo(first_cp, second_cp, second_point)

            # Add the same path reversed in order to have proper filling and
            # intersections (otherwise it draws a start-end line to close the
            # polygon)
            self._cached_path.addPath(self._cached_path.toReversed())
        else:
            raise NotImplementedError

    def draw_arrow_path_and_heads(self, painter: QPainter):
        painter.drawPath(self._cached_path)

        # Draw the arrow head
        point_at_end = self._cached_curves[-1][-2]
        # point_at_end = self._cached_path.pointAtPercent(0.97)
        point_at_end = Point2D(point_at_end.x(), point_at_end.y())
        end_point = self._cached_curves[-1][-1]
        # end_point = self._cached_path.pointAtPercent(1)  # 100%
        end_point = Point2D(end_point.x(), end_point.y())

        normalized_vec = (end_point -
                          point_at_end) / point_at_end.distance_to(end_point)
        arrow_hand_base = end_point - ARROW_HAND_LENGTH * normalized_vec
        hand_end = arrow_hand_base.rotated(ARROW_HAND_ANGLE, end_point)
        hand_end2 = arrow_hand_base.rotated(-ARROW_HAND_ANGLE, end_point)

        end_point = QPointF(*end_point.as_tuple())
        hand_end = QPointF(*hand_end.as_tuple())
        hand_end2 = QPointF(*hand_end2.as_tuple())
        painter.drawLine(end_point, hand_end)
        painter.drawLine(end_point, hand_end2)

    def render(self, painter: QPainter, draw_selection_overlay: bool,
               draw_control_points: bool):
        if not self._cached_path or not self._cached_path.elementCount():
            log.warning('Render called, but _cached_path is empty')
            return

        state: ArrowViewState = self.state()

        # A hacky curve update in case that a render has been called before
        # the update_cache_state has been invoked from the state update
        # it should be a problem specific to the custom drawing setup
        if len(self._cached_curves) != (len(state.edge_indices()) - 1):
            self.update_cached_path()

        pen = painter.pen()
        pen.setColor(QColor(*state.get_color().to_uint8_rgba_list()))
        pen.setWidthF(state.line_thickness)
        painter.setPen(pen)

        self.draw_arrow_path_and_heads(painter)

        if draw_selection_overlay:
            pen.setColor(selection_overlay_qcolor)
            pen.setWidthF(state.line_thickness +
                          ARROW_SELECTION_THICKNESS_DELTA)
            painter.setPen(pen)
            self.draw_arrow_path_and_heads(painter)

        if draw_control_points:
            # The tail is at idx 0, the head at the last, the midpoints
            # also have integer indices and the potential new midpoints have .5
            # indices

            for idx in state.edge_indices():
                edge_point = QPointF(*self.edge_point_pos(idx).as_tuple())
                painter.drawEllipse(edge_point, CONTROL_POINT_RADIUS,
                                    CONTROL_POINT_RADIUS)

            for idx in state.potential_edge_indices():
                edge_point = QPointF(*self.edge_point_pos(idx).as_tuple())
                painter.drawEllipse(edge_point, POTENTIAL_EDGE_RADIUS,
                                    POTENTIAL_EDGE_RADIUS)

        if CONTROL_POINT_DEBUG_VISUALS:
            for curve_idx, curve in enumerate(self._cached_curves):

                c1, c2 = (QPointF(*p.as_tuple()) for p in curve[1:3])
                painter.drawEllipse(c1, 10, 10)
                painter.drawEllipse(c2, 10, 10)

                if (curve_idx + 1) < len(self._cached_curves):
                    next_curve = self._cached_curves[curve_idx + 1]
                    nc1, nc2 = (QPointF(*p.as_tuple())
                                for p in next_curve[1:3])
                    painter.drawLine(c2, nc1)

    def edge_point_pos(self, edge_index: float) -> Point2D:
        """Returns the edge point position for the given index. Those
        include the tail, midpoints and head.

        The indeces are not integers, since the suggested new edge points
        are denoted with non-whole indices (e.g. 0.5, 1.5 etc.).
        More over the tail index is 0, and the head index is the last one.
        """

        if edge_index == 0:
            return self._cached_curves[0][0]
        elif edge_index % 1 == 0:
            curve_idx = int(edge_index - 1)
            curve = self._cached_curves[curve_idx]
            _, _, _, point = curve
            return copy(point)
        else:  # A non-whole index - a potential cp is requested
            curve_idx = int(edge_index)
            curve = self._cached_curves[curve_idx]
            p1, cp1, cp2, p2 = (QPointF(*p.as_tuple()) for p in curve)

            path = QPainterPath(p1)
            path.cubicTo(cp1, cp2, p2)
            potential_cp = path.pointAtPercent(0.5)
            return Point2D(potential_cp.x(), potential_cp.y())

    def edge_at(self, position: Point2D) -> Union[float, None]:
        real_pos = self.map_page_view.state().unproject_point(position)
        indices = self.state().all_edge_indices()
        for idx in indices:
            point = self.edge_point_pos(idx)

            if idx % 1 == 0:  # If it's a real edge
                radius = ARROW_EDGE_RAIDUS
            else:
                radius = POTENTIAL_EDGE_RADIUS
            if point.distance_to(real_pos) <= radius:
                return idx
        return None

    def intersects_circle(self, center: Point2D, radius: float) -> bool:
        if not self._cached_path:
            return False

        path = QPainterPath()
        path.addEllipse(QPointF(*center.as_tuple()), radius, radius)
        return self._cached_path.intersects(path)

    def intersects_rect(self, rect: Rectangle) -> bool:
        if not self._cached_path:
            return False

        selector_rect = QRectF(*rect.as_tuple())
        return self._cached_path.intersects(selector_rect)
