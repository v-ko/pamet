from misli_gui import components_lib

from .app import DesktopAppComponent, DESKTOP_APP_COMPONENT
from .browser_window import BrowserWindowComponent, BROWSER_WINDOW_COMPONENT
from .browser_tab import BrowserTabComponent, BROWSER_TAB
from .map_page.qt_component import MapPageQtComponent
from .note_components.text.qt_component import TextNoteQtComponent
from .note_components.text.edit_qt_component import TextNoteEditQtComponent

components_lib.add(DESKTOP_APP_COMPONENT, DesktopAppComponent)
components_lib.add(BROWSER_WINDOW_COMPONENT, BrowserWindowComponent)
components_lib.add(BROWSER_TAB, BrowserTabComponent)
components_lib.add('MapPage', MapPageQtComponent)

components_lib.add('Text', TextNoteQtComponent)
components_lib.add('Redirect', TextNoteQtComponent)

components_lib.add('TextEdit', TextNoteEditQtComponent)
components_lib.map_edit_component('Text', 'TextEdit')
components_lib.map_edit_component('Redirect', 'TextEdit')
