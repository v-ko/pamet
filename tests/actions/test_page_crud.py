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

    with exec_action(delay_before_next=0.5894737243652344,
                     apply_delay=not run_headless):
        pamet.actions.tab.create_new_page(tab_state=fsm.view_state('2'),
                                          mouse_position=Point2D(940, 340))

    with exec_action(delay_before_next=0.017842769622802734,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.0023813247680664062,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('5'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('5'),
            selection_updates_by_child={fsm.view_state('6'): True})

    with exec_action(delay_before_next=0.5292613506317139,
                     apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/00000001")

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=0.0022859573364257812,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(
            map_page_view_state=fsm.view_state('3'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(
            map_page_view_state=fsm.view_state('3'),
            selection_updates_by_child={fsm.view_state('8'): True})

    with exec_action(delay_before_next=0.526573657989502,
                     apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/00000005")

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=0.5207712650299072,
                     apply_delay=not run_headless):
        pamet.actions.map_page.open_page_properties(
            tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.0053997039794921875,
                     apply_delay=not run_headless):
        pamet.actions.map_page.save_page_properties(
            page=Page(id="00000005",
                      name="New page 1aaaa",
                      created="2022-09-09T09:54:42+03:00",
                      modified="2022-09-09T09:55:06+03:00"))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.close_page_properties(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.014553308486938477,
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

    with exec_action(delay_before_next=0.004543304443359375,
                     apply_delay=not run_headless):
        pamet.actions.window.close_command_view(
            window_state=fsm.view_state('1'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/00000001")

    with exec_action(delay_before_next=0.7721796035766602,
                     apply_delay=not run_headless):
        pamet.actions.window.open_command_view(
            window_state=fsm.view_state('1'))

    with exec_action(delay_before_next=0.0044956207275390625,
                     apply_delay=not run_headless):
        pamet.actions.window.close_command_view(
            window_state=fsm.view_state('1'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.go_to_url(tab_state=fsm.view_state('2'),
                                    url="pamet:/p/00000005")

    with exec_action(delay_before_next=0.5170257091522217,
                     apply_delay=not run_headless):
        pamet.actions.map_page.open_page_properties(
            tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('5'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.023119211196899414,
                     apply_delay=not run_headless):
        pamet.actions.map_page.delete_page(
            tab_view_state=fsm.view_state('2'),
            page=Page(id="00000005",
                      name="New page 1aaaa",
                      created="2022-09-09T09:54:42+03:00",
                      modified="2022-09-09T09:55:06+03:00"))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.close_page_properties(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.5176599025726318,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.apply_page_change_to_anchor_view(
            note_view_state=fsm.view_state('8'))

    with exec_action(delay_before_next=0.5212478637695312,
                     apply_delay=not run_headless):
        pamet.actions.map_page.open_page_properties(
            tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('3'),
            new_size=Point2D(1570, 963))

    with exec_action(delay_before_next=0.04296374320983887,
                     apply_delay=not run_headless):
        pamet.actions.map_page.delete_page(
            tab_view_state=fsm.view_state('2'),
            page=Page(id="00000001",
                      name="New page",
                      created="2022-09-09T09:54:30+03:00",
                      modified="2022-09-09T09:54:30+03:00"))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.tab.close_page_properties(tab_state=fsm.view_state('2'))

    with exec_action(delay_before_next=0.518906831741333,
                     apply_delay=not run_headless):
        pamet.actions.map_page.resize_page(
            map_page_view_state=fsm.view_state('14'),
            new_size=Point2D(1838, 963))

    with exec_action(delay_before_next=1, apply_delay=not run_headless):
        pamet.actions.note.apply_page_change_to_anchor_view(
            note_view_state=fsm.view_state('6'))

    assert True
