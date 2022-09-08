import pamet
from fusion.visual_inspection.action_camera import exec_action
from fusion import fsm

from pamet.model.page import Page
from fusion.util.point2d import Point2D


# Create new page
# Go back to the old page via the back link
# Go to the new page via the link
# Rename the page
# Go back to the old page via the Go to file command palette
# Go to the new page via the link
# Delete the new page
# Delete the old/initial page (to test the auto creation on last)
def test_test_page_crud(window_fixture, request):
    run_headless = request.config.getoption('--headless')

    with exec_action(delay_before_next=0.512016773223877,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=0.5878622531890869,
                     apply_delay=not run_headless):
        pamet.actions.tab.create_new_page(tab_state=fsm.view_state('2'),
                                          mouse_position=Point2D(954, 362))

    with exec_action(delay_before_next=0.018275022506713867,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.0025970935821533203,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('5'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('5'),
            selection_updates_by_child={fsm.view_state('6'): True})

    with exec_action(delay_before_next=0.5362789630889893,
                     apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/6baa9455")

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=0.002245664596557617,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('8'): True})

    with exec_action(delay_before_next=0.5347311496734619,
                     apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/98a6416d")

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=0.5204312801361084,
                     apply_delay=not run_headless):
        pamet.actions.map_page.open_page_properties(
            tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.0067195892333984375,
                     apply_delay=not run_headless):
        pamet.actions.map_page.save_page_properties(
            page=Page(id="98a6416d",
                      name="New page 2",
                      created="2022-09-08T18:04:18+03:00",
                      modified="2022-09-08T18:04:35+03:00"))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.close_page_properties(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.019173860549926758,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.apply_page_change_to_anchor_view(
            note_view_state=fsm.view_state('8'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.window.open_command_view(
            window_state=fsm.view_state('1'))

    with exec_action(delay_before_next=0.005650758743286133,
                     apply_delay=not run_headless):
        pamet.actions.window.close_command_view(
            window_state=fsm.view_state('1'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/6baa9455")

    with exec_action(delay_before_next=0.010718584060668945,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('8'): True})

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/98a6416d")

    with exec_action(delay_before_next=0.5209059715270996,
                     apply_delay=not run_headless):
        pamet.actions.map_page.open_page_properties(
            tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.021641969680786133,
                     apply_delay=not run_headless):
        pamet.actions.map_page.delete_page(
            tab_view_state=fsm.view_state('2'),
            page=Page(id="98a6416d",
                      name="New page 2",
                      created="2022-09-08T18:04:18+03:00",
                      modified="2022-09-08T18:04:35+03:00"))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.close_page_properties(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.5245945453643799,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.apply_page_change_to_anchor_view(
            note_view_state=fsm.view_state('8'))

    with exec_action(delay_before_next=0.5215537548065186,
                     apply_delay=not run_headless):
        pamet.actions.map_page.open_page_properties(
            tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.02066826820373535,
                     apply_delay=not run_headless):
        pamet.actions.map_page.delete_page(
            tab_view_state=fsm.view_state('2'),
            page=Page(id="6baa9455",
                      name="New page",
                      created="2022-09-08T18:04:14+03:00",
                      modified="2022-09-08T18:04:14+03:00"))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.close_page_properties(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.511441707611084,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('13'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.apply_page_change_to_anchor_view(
            note_view_state=fsm.view_state('6'))

    assert True
