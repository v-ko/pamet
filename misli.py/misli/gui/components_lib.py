from .notes.text.qt_component import TextNoteQtComponent
from .map_page.qt_component import MapPageQtComponent
# from .redirect import RedirectNoteComponent
# from .markdown import MarkdownNoteComponent
# from .textedit import TexteditNoteComponent


compopnents_by_type = {
    'Text': TextNoteQtComponent,
    'Redirect': TextNoteQtComponent,
    'Page': MapPageQtComponent
}


def add(name, ComponentClass):
    compopnents_by_type[name] = ComponentClass


def get(note_type):
    return compopnents_by_type[note_type]
