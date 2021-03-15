from misli_gui import components_lib

from .app import DesktopAppView, DESKTOP_APP_COMPONENT
from .browser_window import BrowserWindowView, BROWSER_WINDOW_COMPONENT
from .browser_tab import BrowserTabView, BROWSER_TAB
from pamet_desktop.map_page_widget import MapPageViewWidget
from .note_components.text.widget import TextNoteViewWidget
from .note_components.text.edit_widget import TextNoteEditViewWidget

components_lib.add(DESKTOP_APP_COMPONENT, DesktopAppView)
components_lib.add(BROWSER_WINDOW_COMPONENT, BrowserWindowView)
components_lib.add(BROWSER_TAB, BrowserTabView)
components_lib.add('MapPage', MapPageViewWidget)

components_lib.add('Text', TextNoteViewWidget)
components_lib.add('Redirect', TextNoteViewWidget)

components_lib.add('TextEdit', TextNoteEditViewWidget)
components_lib.map_edit_component('Text', 'TextEdit')
components_lib.map_edit_component('Redirect', 'TextEdit')
