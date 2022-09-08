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

    with exec_action(delay_before_next=0.0029449462890625,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=0.5214769840240479,
                     apply_delay=not run_headless):
        pamet.actions.map_page.start_child_move(
            map_page_view_state=fsm.view_state('3'),
            mouse_pos=Point2D(944, 475))

    with exec_action(delay_before_next=0.5144076347351074,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-12.0, -32.0))

    with exec_action(delay_before_next=0.5219848155975342,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-36.0, -140.0))

    with exec_action(delay_before_next=0.5219817161560059,
                     apply_delay=not run_headless):
        pamet.actions.map_page.moved_child_view_update(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-18.0, -236.0))

    with exec_action(delay_before_next=0.5362186431884766,
                     apply_delay=not run_headless):
        pamet.actions.map_page.finish_child_move(
            map_page_view_state=fsm.view_state('3'),
            delta=Point2D(-18.0, -236.0))

    with exec_action(delay_before_next=0.009685754776000977,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.009208917617797852,
                     apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('4'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.start_notes_resize(
            map_page_view_state=fsm.view_state('3'),
            main_note=TextNote(id=("6baa9455", "7a024204"),
                               geometry=[-180, -320, 320, 160],
                               style={},
                               content={"text": "Mock help note"},
                               metadata={},
                               created="2022-09-08T18:01:03+03:00",
                               modified="2022-09-08T18:01:03+03:00",
                               tags=[]),
            mouse_position=Point2D(988, 399),
            resize_circle_center_projected=Point2D(989.0, 401.5))

    with exec_action(delay_before_next=0.5253458023071289,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(234.0, 97.0))

    with exec_action(delay_before_next=0.5214567184448242,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(212.0, 91.0))

    with exec_action(delay_before_next=0.008827686309814453,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_note_views(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(190.0, 85.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.finish_notes_resize(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(190.0, 85.0))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.start_editing_note(
            tab_view_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "7a024204"),
                          geometry=[-180, -320, 190, 80],
                          style={},
                          content={"text": "Mock help note"},
                          metadata={},
                          created="2022-09-08T18:01:03+03:00",
                          modified="2022-09-08T18:01:03+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_editing_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "7a024204"),
                          geometry=[-180, -320, 190, 80],
                          style={},
                          content={"text": "Mock help note\nMultiline"},
                          metadata={},
                          created="2022-09-08T18:01:03+03:00",
                          modified="2022-09-08T18:01:19+03:00",
                          tags=[]))

    with exec_action(delay_before_next=0.9817540645599365,
                     apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5074722766876221,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.create_new_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "0bb2c3f0"),
                          geometry=[-86.0, -207.0, 320, 160],
                          style={},
                          content={"text": ""},
                          metadata={},
                          created="2022-09-08T18:01:24+03:00",
                          modified="2022-09-08T18:01:24+03:00",
                          tags=[]))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.finish_creating_note(
            tab_state=fsm.view_state('2'),
            note=TextNote(id=("6baa9455", "0bb2c3f0"),
                          geometry=[-86.0, -207.0, 100, 30],
                          style={},
                          content={"text": "New note"},
                          metadata={},
                          created="2022-09-08T18:01:28+03:00",
                          modified="2022-09-08T18:01:28+03:00",
                          tags=[]))

    assert True
