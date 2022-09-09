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

    with exec_action(delay_before_next=0.5032045841217041,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.create_new_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000005"),
                          geometry=[570.0, -371.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-09T10:00:35+03:00",
                          modified="2022-09-09T10:00:35+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_creating_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000005"),
                          geometry=[570.0, -371.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-09T10:00:37+03:00",
                          modified="2022-09-09T10:00:37+03:00",
                          tags=[]))

    with exec_action(delay_before_next=0.7165634632110596,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.515120267868042,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(-112.0, -567.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.010453462600708008,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(-100.0, -553.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.005595207214355469,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(-100.0, -553.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(74.0, -601.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5248458385467529,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(496.0, -673.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(496.0, -673.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5091159343719482,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5119011402130127,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(184.0, -65.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5125882625579834,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(136.0, -41.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.MID_RIGHT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5067262649536133,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(-16.0, -73.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.006644010543823242,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(-8.0, -83.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.005877256393432617,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(-8.0, -83.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(162.0, -185.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.8889937400817871,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(568.0, -309.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5109269618988037,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(568.0, -307.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.005484580993652344,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(568.0, -301.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(568.0, -301.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5188963413238525,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5179836750030518,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(752.0, -379.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.527916669845581,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(746.0, -381.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.533435583114624,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(738.0, -381.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.9121277332305908,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(738.0, -381.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5174984931945801,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(736.0, -383.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.6047213077545166,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(720.0, -389.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5158109664916992,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(720.0, -391.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(720.0, -391.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.TOP_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.7181804180145264,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5064895153045654,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(436.0, -431.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5123739242553711,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(696.0, -233.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5148122310638428,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(720.0, -211.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.016089916229248047,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(726.0, -209.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(726.0, -209.0),
            anchor_note_id="00000005",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5145213603973389,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(380.0, -47.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.6868588924407959,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(216.0, -3.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5117301940917969,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(218.0, -3.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.9635162353515625,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(376.0, -29.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(376.0, -29.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5073676109313965,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.create_new_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000017"),
                          geometry=[566.0, 203.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-09T10:01:10+03:00",
                          modified="2022-09-09T10:01:10+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_creating_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000017"),
                          geometry=[566.0, 203.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-09T10:01:11+03:00",
                          modified="2022-09-09T10:01:11+03:00",
                          tags=[]))

    with exec_action(delay_before_next=0.002137899398803711,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('19'): True})

    with exec_action(delay_before_next=0.5176196098327637,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_creation(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5153346061706543,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(574.0, 293.0),
            anchor_note_id="00000017",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5281515121459961,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(542.0, 291.0),
            anchor_note_id="00000017",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.013361454010009766,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(558.0, 285.0),
            anchor_note_id="00000017",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(558.0, 285.0),
            anchor_note_id="00000017",
            anchor_type=ArrowAnchorType.MID_LEFT,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.9202549457550049,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_move(
            fixed_pos=Point2D(0.0, 93.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.arrow_creation_click(
            fixed_pos=Point2D(0.0, 93.0),
            anchor_note_id="00000002",
            anchor_type=ArrowAnchorType.BOTTOM_MID,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.012984037399291992,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('22'): True})

    with exec_action(delay_before_next=0.5147323608398438,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_edge_drag(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(1034, 600),
            edge_index=0.5)

    with exec_action(delay_before_next=0.8191120624542236,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(422.0, 125.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.9684457778930664,
                     apply_delay=not run_headless):
        pamet.actions.map_page.finish_arrow_edge_drag(
            fixed_pos=Point2D(422.0, 125.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5132126808166504,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_arrow_edge_drag(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(1005, 546),
            edge_index=1.5)

    with exec_action(delay_before_next=0.8163204193115234,
                     apply_delay=not run_headless):
        pamet.actions.map_page.arrow_edge_drag_update(
            fixed_pos=Point2D(146.0, 275.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_arrow_edge_drag(
            fixed_pos=Point2D(146.0, 275.0),
            anchor_note_id=None,
            anchor_type=ArrowAnchorType.NONE,
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.003901958465576172,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('19'): True})

    with exec_action(delay_before_next=0.5120954513549805,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_child_move(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(1299, 621))

    with exec_action(delay_before_next=0.5062975883483887,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(68.0, -50.0))

    with exec_action(delay_before_next=0.9184830188751221,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(132.0, -96.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_child_move(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(132.0, -96.0))

    with exec_action(delay_before_next=0.003981828689575195,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('6'): True})

    with exec_action(delay_before_next=0.5107238292694092,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_child_move(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(1299, 328))

    with exec_action(delay_before_next=0.5067813396453857,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(104.0, -6.0))

    with exec_action(delay_before_next=0.5138816833496094,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(186.0, -8.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_child_move(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(186.0, -8.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.0014564990997314453,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.0010895729064941406,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('9'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    assert True
