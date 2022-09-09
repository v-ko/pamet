import pamet
from fusion.visual_inspection.action_camera import exec_action
from fusion import fsm

from pamet.model.text_note import TextNote
from fusion.util.point2d import Point2D


# Resize note
# Move note
# Edit note (with multiline text)
# Delete note
# Create note
def test_note_crud(window_fixture, request):
    run_headless = request.config.getoption('--headless')

    with exec_action(delay_before_next=0.001154184341430664,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=0.00896000862121582,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.007747173309326172,
                     apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.start_notes_resize(
            map_page_view_state=fsm.view_state('3'),
            main_note=TextNote(id=("00000001", "00000002"),
                               geometry=[-160.0, -80.0, 320, 160],
                               style={},
                               content={"text": "Mock help note"},
                               metadata={},
                               created="2022-09-09T10:03:12+03:00",
                               modified="2022-09-09T10:03:12+03:00",
                               tags=[]),
            mouse_position=Point2D(1002, 523),
            resize_circle_center_projected=Point2D(999.0, 521.5))

    with exec_action(delay_before_next=0.5956573486328125,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(188.0, 95.0))

    with exec_action(delay_before_next=0.5051360130310059,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(186.0, 95.0))

    with exec_action(delay_before_next=0.5053880214691162,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(176.0, 93.0))

    with exec_action(delay_before_next=0.003194570541381836,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(174.0, 93.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_notes_resize(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(174.0, 93.0))

    with exec_action(delay_before_next=0.003925800323486328,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=0.5153989791870117,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_child_move(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(884, 455))

    with exec_action(delay_before_next=0.5095925331115723,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-8.0, -74.0))

    with exec_action(delay_before_next=0.5160834789276123,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-24.0, -178.0))

    with exec_action(delay_before_next=0.5158922672271729,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-20.0, -210.0))

    with exec_action(delay_before_next=0.007718324661254883,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-20.0, -212.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_child_move(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-20.0, -212.0))

    with exec_action(delay_before_next=0.0045282840728759766,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.start_editing_note(
            tab_view_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000002"),
                          geometry=[-180, -290, 170, 90],
                          style={},
                          content={"text": "Mock help note"},
                          metadata={},
                          created="2022-09-09T10:03:12+03:00",
                          modified="2022-09-09T10:03:12+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_editing_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000002"),
                          geometry=[-180, -290, 170, 90],
                          style={},
                          content={"text": "Mock help note\nEdited multiline"},
                          metadata={},
                          created="2022-09-09T10:03:12+03:00",
                          modified="2022-09-09T10:03:36+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5052444934844971,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.create_new_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000005"),
                          geometry=[-128.0, -207.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-09T10:03:44+03:00",
                          modified="2022-09-09T10:03:44+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_creating_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("00000001", "00000005"),
                          geometry=[-128.0, -207.0, 100, 30],
                          style={},
                          content={"text": "New note"},
                          metadata={},
                          created="2022-09-09T10:03:47+03:00",
                          modified="2022-09-09T10:03:47+03:00",
                          tags=[]))

    assert True
