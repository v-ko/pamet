import fusion
from fusion.gui import context

import pamet
from pamet.views import map_page


def editing_note():
    tab = pamet.views.current_tab()
    if tab and tab.edit_view_state:
        return True
    return False


def page_focus():
    focused_view = fusion.gui.focused_view()
    return isinstance(focused_view, map_page.view.MapPageView)


# def in_page_properties():
#     curr_tab = pamet.views.current_tab()
#     return curr_tab.state().page_properties_open


def notes_selected():
    curr_tab = pamet.views.current_tab()
    if not curr_tab:
        return False

    page_view = curr_tab.page_view()
    if not page_view:
        return False

    if not page_view.state().selected_children:
        return False

    return True


context.add_callable('editingNote', editing_note)
context.add_callable('pageFocus', page_focus)
context.add_callable('inPageProperties', in_page_properties)
context.add_callable('notesSelected', notes_selected)
