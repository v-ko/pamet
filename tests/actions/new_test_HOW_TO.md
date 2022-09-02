# Creating new action tests
The Recorder class is used to collect all called top-level actions and generate a test script from them. It opens a window and records while you use the app.

To create a new test run:
```
pytest record_new.py
```

If you want to modify or extend a test - just put `ActionCamera().record_until_exit(output_file_path)` after the already configured action calls. E.g.:
```python
def test_new(window_fixture, request):
    run_headless = request.config.getoption('--headless')

    with exec_action(delay_before_next=0.002991199493408203,
                     apply_delay=not run_headless):
        pamet.actions.map_page.clear_child_selection(view_state('3'))

    with exec_action(delay_before_next=0.5916464328765869,
                     apply_delay=not run_headless):
        pamet.actions.map_page.update_child_selections(view_state('3'),
                                                       {view_state('4'): True})

    with exec_action(delay_before_next=0.035302162170410156,
                     apply_delay=not run_headless):
        pamet.actions.map_page.delete_selected_children(view_state('3'))

    with exec_action(delay_before_next=1.5319700241088867,
                     apply_delay=not run_headless):
        pamet.actions.map_page.handle_child_removed(
            view_state('3'),
            TextNote(id=('6baa9455', 'c8a70639'),
                     geometry=[-160.0, -80.0, 320, 160],
                     style={},
                     content={'text': 'Mock help note'},
                     metadata={},
                     created='2022-09-02 18:09:35.382214+03:00',
                     modified='2022-09-02 18:09:35.382260+03:00',
                     tags=[]))

    ActionCamera().record_until_exit(output_file_path)
```

And then copy and paste the generated action calls.