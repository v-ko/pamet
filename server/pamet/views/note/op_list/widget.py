from PySide6.QtCore import QRect
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox
from pamet.model.op_list_note import OtherPageListNote
from pamet.note_view_lib import register_note_view_type
from pamet.views.note.op_list.state import OtherPageListNoteViewState
from pamet.views.note.text.widget import TextNoteWidget


@register_note_view_type(state_type=OtherPageListNoteViewState,
                         note_type=OtherPageListNote,
                         edit=False)
class OtherPageListNoteWidget(TextNoteWidget):
    def left_mouse_double_click_event(self, position):
        QMessageBox.information(self, 'Other page list info', '''
        The OtherPageList note cannot be edited. It's function is to keep an
        up-to-date list with links to all pages in the Pamet repo. It's useful
        for keeping an updated index of your pages.
        ''')

    def on_state_change(self, change):
        state = change.last_state()
        if change.updated.color or change.updated.background_color:

            fg_col = QColor(*state.get_color().to_uint8_rgba_list())
            bg_col = QColor(*state.get_background_color().to_uint8_rgba_list())

            palette = self.palette()
            palette.setColor(self.backgroundRole(), bg_col)
            palette.setColor(self.foregroundRole(), fg_col)
            self.setPalette(palette)

        if change.updated.geometry:
            self.setGeometry(QRect(*state.geometry))

        if change.updated.text or \
                change.updated.geometry \
                or change.updated.url:
            self.recalculate_elided_text()
