import pamet
from fusion.visual_inspection.action_camera import exec_action
from fusion import fsm
from pamet.model.arrow import ArrowAnchorType

from pamet.model.text_note import TextNote
from fusion.util.point2d import Point2D

# Create a second note
# Create arrows with free and anchored ends
# Also create one that starts and ends on the same note
# Also try one that starts and ends on the same anchor
# Update control points
# Move notes while arrows present
# Delete arrows


def test_arrow_crud(window_fixture, request):
    run_headless = request.config.getoption('--headless')

    with exec_action(delay_before_next=0.5066771507263184,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.create_new_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "966e1277"),
                          geometry=[470.0, -141.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-08T18:22:09+03:00",
                          modified="2022-09-08T18:22:09+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_creating_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "966e1277"),
                          geometry=[470.0, -141.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-08T18:22:10+03:00",
                          modified="2022-09-08T18:22:10+03:00",
                          tags=[]))

    with exec_action(delay_before_next=0.5183227062225342,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5191559791564941,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(74.0, -373.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5198519229888916,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(74.0, -373.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5256719589233398,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(386.0, -401.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.6451895236968994,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(480.0, -429.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(480.0, -429.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5164065361022949,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5173048973083496,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(162.0, -269.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.524998664855957,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(206.0, -277.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.015883445739746094,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(208.0, -271.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(208.0, -271.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5336296558380127,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(636.0, -161.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5298981666564941,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(638.0, -149.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5337116718292236,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(634.0, -147.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(634.0, -147.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5211074352264404,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5314524173736572,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(154.0, 11.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5273525714874268,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(156.0, 5.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5270562171936035,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(372.0, -35.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5314280986785889,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(468.0, -51.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5295124053955078,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(468.0, -51.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5311119556427002,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(192.0, 11.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5324358940124512,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(180.0, 13.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5327472686767578,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(166.0, 5.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.016069889068603516,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(166.0, 3.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(166.0, 3.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5065515041351318,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.create_new_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "5e4af862"),
                          geometry=[500.0, 161.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-08T18:22:39+03:00",
                          modified="2022-09-08T18:22:39+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_creating_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "5e4af862"),
                          geometry=[500.0, 161.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-08T18:22:40+03:00",
                          modified="2022-09-08T18:22:40+03:00",
                          tags=[]))

    with exec_action(delay_before_next=0.5205059051513672,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5189552307128906,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(166.0, 17.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5329794883728027,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(166.0, 7.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.017444849014282227,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(166.0, 5.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(166.0, 5.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.9366869926452637,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(492.0, 229.0),
            anchor_note_id="5e4af862",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(492.0, 229.0),
            anchor_note_id="5e4af862",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5215902328491211,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5195372104644775,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(14.0, 85.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5378785133361816,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(2.0, 85.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5367221832275391,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(2.0, 85.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5388791561126709,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(-164.0, 11.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5409772396087646,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(-166.0, 5.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(-166.0, 5.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.002861499786376953,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=0.010839462280273438,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('23'): True})

    with exec_action(delay_before_next=0.5137405395507812,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_edge_drag(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(867, 531),
            edge_index=0.5)

    with exec_action(delay_before_next=0.5421297550201416,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(-150.0, 107.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5392813682556152,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(-166.0, 119.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5388913154602051,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(-186.0, 139.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5344064235687256,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(-204.0, 141.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_arrow_edge_drag(
            fixed_pos=Point2D(-204.0, 141.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.010385751724243164,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('12'): True})

    with exec_action(delay_before_next=0.52620530128479,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_mouse_drag_navigation(
            map_page_view_state=fsm.view_state('3'),
            mouse_position=Point2D(1019, 363),
            first_delta=Point2D(89, -69))

    with exec_action(delay_before_next=0.5294089317321777,
                     apply_delay=not run_headless):
        pamet.actions.map_page.mouse_drag_navigation_move(
            map_page_view_state=fsm.view_state('3'),
            mouse_delta=Point2D(92, -75))

    with exec_action(delay_before_next=0.00881338119506836,
                     apply_delay=not run_headless):
        pamet.actions.map_page.finish_mouse_drag_navigation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.update_current_url(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.5329680442810059,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_edge_drag(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(925, 440),
            edge_index=0)

    with exec_action(delay_before_next=0.5392212867736816,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(70.0, -155.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5398030281066895,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(30.0, -103.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5254356861114502,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(22.0, -93.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_arrow_edge_drag(
            fixed_pos=Point2D(22.0, -93.0),
            anchor_note_id="7a024204",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.010600805282592773,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('9'): True})

    with exec_action(delay_before_next=0.514108419418335,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_edge_drag(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(1064, 362),
            edge_index=1)

    with exec_action(delay_before_next=0.5247681140899658,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(660.0, -277.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5474915504455566,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(804.0, -89.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5470280647277832,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(806.0, -69.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_arrow_edge_drag(
            fixed_pos=Point2D(806.0, -69.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5140511989593506,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_edge_drag(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(863, 388),
            edge_index=0)

    with exec_action(delay_before_next=0.5226352214813232,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(132.0, -363.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5448954105377197,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(506.0, -301.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5296719074249268,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(686.0, -255.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5219182968139648,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(774.0, -149.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5210871696472168,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(788.0, -83.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.017419099807739258,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(788.0, -79.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_arrow_edge_drag(
            fixed_pos=Point2D(788.0, -79.0),
            anchor_note_id="966e1277",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.010931730270385742,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('17'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.0026826858520507812,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('6'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.0028977394104003906,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('23'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    assert True
