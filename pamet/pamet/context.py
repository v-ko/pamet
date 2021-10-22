import misli
from misli.gui import context

import pamet
from pamet.views import map_page


def editing_note():
    tab = pamet.views.current_tab()
    if tab and tab.edit_view_id:
        return True
    return False


def page_focus():
    focused_view = misli.gui.focused_view()
    print('IN PAGE FOCUS', focused_view)
    return isinstance(focused_view, map_page.view.MapPageView)


# def focused_view_type():
#     print('IN FOCUS VIEW TYPE')
#     return type(misli.gui.focused_view()).__name__


context.add_callable('editingNote', editing_note)
context.add_callable('pageFocus', page_focus)
# context['focusedViewType'] = property(focused_view_type)
