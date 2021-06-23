from pamet import view_library

from pamet.desktop.app import DesktopApp
from pamet.desktop.browser_window import BrowserWindowView
from pamet.desktop.browser_tab import BrowserTabView
from pamet.desktop.map_page_widget import MapPageViewWidget
from pamet.desktop.note_components.text.widget import TextNoteViewWidget
from pamet.desktop.note_components.text.edit_widget import \
    TextNoteEditViewWidget

view_library.add_view_class(DesktopApp)
view_library.add_view_class(BrowserWindowView)
view_library.add_view_class(BrowserTabView)
view_library.add_view_class(MapPageViewWidget)

view_library.add_view_class(TextNoteViewWidget)
# view_library.add('Redirect', TextNoteViewWidget)

# view_library.add('TextEdit', TextNoteEditViewWidget)
view_library.add_edit_view_class(
    TextNoteViewWidget.view_class, TextNoteEditViewWidget)
# view_library.add_edit_view('Redirect', TextNoteEditViewWidget)
