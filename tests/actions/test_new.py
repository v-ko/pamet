# import pamet
# from fusion.visual_inspection.action_camera import exec_action
# from fusion.gui.misli_gui import view_state

# from pamet.model.text_note import TextNote
# from fusion.basic_classes.point2d import Point2D


# def test_new(window_fixture, request):
#     run_headless = request.config.getoption('--headless')

#     # Select
#     with exec_action(delay_before_next=0.0031130313873291016,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.clear_child_selection(
#             map_page_view_state=view_state('3'))

#     with exec_action(delay_before_next=0.010173320770263672,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.update_child_selections(
#             map_page_view_state=view_state('3'),
#             selection_updates_by_child_id={view_state('4'): True})

#     # Resize
#     with exec_action(delay_before_next=0.013455867767333984,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.start_notes_resize(
#             map_page_view_state=view_state('3'),
#             main_note=TextNote(id=("6baa9455", "c8a70639"),
#                                geometry=[-160.0, -80.0, 320, 160],
#                                style={},
#                                content={"text": "Mock help note"},
#                                metadata={},
#                                created="2022-09-02T19:15:55+03:00",
#                                modified="2022-09-02T19:15:55+03:00",
#                                tags=[]),
#             mouse_position=Point2D(999, 523),
#             resize_circle_center_projected=Point2D(999.0, 521.5))

#     with exec_action(delay_before_next=0.011806011199951172,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.resize_note_views(
#             map_page_view_state=view_state('3'),
#             new_size=Point2D(318.0, 157.0))

#     with exec_action(delay_before_next=0.0038678646087646484,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.resize_note_views(
#             map_page_view_state=view_state('3'),
#             new_size=Point2D(300.0, 140.0))

#     with exec_action(delay_before_next=0.0038678646087646484,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.resize_note_views(
#             map_page_view_state=view_state('3'),
#             new_size=Point2D(280.0, 120.0))

#     with exec_action(delay_before_next=0.8659837245941162,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.finish_notes_resize(
#             map_page_view_state=view_state('3'),
#             new_size=Point2D(262.0, 107.0))

#     # Select for move
#     with exec_action(delay_before_next=0.010939359664916992,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.clear_child_selection(
#             map_page_view_state=view_state('3'))

#     with exec_action(delay_before_next=0.3120288848876953,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.update_child_selections(
#             map_page_view_state=view_state('3'),
#             selection_updates_by_child_id={view_state('4'): True})

#     # Move
#     with exec_action(delay_before_next=0.24416422843933105,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.start_child_move(
#             map_page_view_state=view_state('3'), mouse_pos=Point2D(913, 466))

#     with exec_action(delay_before_next=0.0118560791015625,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(0.0, -2.0))

#     with exec_action(delay_before_next=0.013903141021728516,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(0.0, -10.0))

#     with exec_action(delay_before_next=0.02037644386291504,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(0.0, -20.0))

#     with exec_action(delay_before_next=0.017062902450561523,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(2.0, -32.0))

#     with exec_action(delay_before_next=0.018593311309814453,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(4.0, -56.0))

#     with exec_action(delay_before_next=0.016889572143554688,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(4.0, -88.0))

#     with exec_action(delay_before_next=0.014967918395996094,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(4.0, -118.0))

#     with exec_action(delay_before_next=0.003950595855712891,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.moved_child_view_update(
#             map_page_view_state=view_state('3'), delta=Point2D(2.0, -126.0))

#     with exec_action(delay_before_next=0.7968416213989258,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.finish_child_move(
#             map_page_view_state=view_state('3'), delta=Point2D(2.0, -126.0))

#     # Edit note
#     with exec_action(delay_before_next=4.9163289070129395,
#                      apply_delay=not run_headless):
#         pamet.actions.note.start_editing_note(
#             tab_view_state=view_state('2'),
#             note=TextNote(id=("6baa9455", "c8a70639"),
#                           geometry=[-160, -210, 260, 110],
#                           style={},
#                           content={"text": "Mock help note"},
#                           metadata={},
#                           created="2022-09-02T19:15:55+03:00",
#                           modified="2022-09-02T19:15:55+03:00",
#                           tags=[]))

#     with exec_action(delay_before_next=1.5613610744476318,
#                      apply_delay=not run_headless):
#         pamet.actions.note.finish_editing_note(
#             tab_state=view_state('2'),
#             note=TextNote(id=("6baa9455", "c8a70639"),
#                           geometry=[-160, -210, 260, 110],
#                           style={},
#                           content={"text": "Mock help note\nEdited multiline"},
#                           metadata={},
#                           created="2022-09-02T19:15:55+03:00",
#                           modified="2022-09-02T19:16:05+03:00",
#                           tags=[]))

#     # Delete note
#     with exec_action(delay_before_next=2.255450487136841,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.delete_selected_children(
#             map_page_view_state=view_state('3'))

#     with exec_action(delay_before_next=0.12401747703552246,
#                      apply_delay=not run_headless):
#         pamet.actions.map_page.clear_child_selection(
#             map_page_view_state=view_state('3'))

#     # Create new note
#     with exec_action(delay_before_next=2.138749361038208,
#                      apply_delay=not run_headless):
#         pamet.actions.note.create_new_note(
#             tab_state=view_state('2'),
#             note=TextNote(id=("6baa9455", "19086515"),
#                           geometry=[-194.0, -147.0, 320, 160],
#                           style={},
#                           content={"text": ""},
#                           metadata={},
#                           created="2022-09-02T19:16:09+03:00",
#                           modified="2022-09-02T19:16:09+03:00",
#                           tags=[]))

#     with exec_action(delay_before_next=1.6978826522827148,
#                      apply_delay=not run_headless):
#         pamet.actions.note.finish_creating_note(
#             tab_state=view_state('2'),
#             note=TextNote(id=("6baa9455", "19086515"),
#                           geometry=[-194.0, -147.0, 130, 30],
#                           style={},
#                           content={"text": "New note"},
#                           metadata={},
#                           created="2022-09-02T19:16:11+03:00",
#                           modified="2022-09-02T19:16:11+03:00",
#                           tags=[]))

#     assert True
