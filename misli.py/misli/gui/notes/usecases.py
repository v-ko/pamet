from misli import misli


def start_editing_note(tab_component_id, note_component_id, position):
    note = misli.base_object_for_component(note_component_id)

    edit_class_name = misli.components_lib.get_edit_class_name(note.obj_class)
    edit_component = misli.create_component_for_note(
        note.page_id, note.id, edit_class_name, tab_component_id)

    display_rect = note.rect()
    display_rect.moveCenter(position.to_QPointF())

    edit_component.note_display_rect = display_rect
    edit_component.note_text = note.text

    misli.update_component(edit_component.id)


def finish_editing_note(edit_component_id, **note_state):
    edit_component = misli.component(edit_component_id)
    note = misli.base_object_for_component(edit_component_id)

    if note_state:
        misli.update_note(note.id, note.page_id, **note_state)
        misli.update_page(note.page_id)

    misli.remove_component(edit_component.id)
