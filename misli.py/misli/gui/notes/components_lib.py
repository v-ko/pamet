from .text_note_qt_component import TextNoteQtComponent
# from .redirect import RedirectNoteComponent
# from .markdown import MarkdownNoteComponent
# from .textedit import TexteditNoteComponent


note_compopnents_by_type = {
    'Text': TextNoteQtComponent,
    'Redirect': TextNoteQtComponent
}


def get(note_type):
    return note_compopnents_by_type[note_type]
