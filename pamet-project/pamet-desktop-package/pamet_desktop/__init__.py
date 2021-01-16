from misli_gui import components_lib

from .app import DesktopApp
from .browser_window import BrowserWindow
from .browser_tab import BrowserTabComponent
from .map_page_qt_component import MapPageQtComponent
from .note_components.text.qt_component import TextNoteQtComponent
from .note_components.text.edit_qt_component import TextNoteEditQtComponent


components_lib.add('DesktopApp', DesktopApp)
components_lib.add('BrowserWindow', BrowserWindow)
components_lib.add('BrowserTab', BrowserTabComponent)
components_lib.add('MapPage', MapPageQtComponent)

components_lib.add('Text', TextNoteQtComponent)
components_lib.add('Redirect', TextNoteQtComponent)

components_lib.add('TextEdit', TextNoteEditQtComponent)
components_lib.map_edit_component('Text', 'TextEdit')
components_lib.map_edit_component('Redirect', 'TextEdit')
