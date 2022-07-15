from __future__ import annotations

from PySide6.QtWidgets import QCompleter, QPushButton, QTextEdit

import misli
from misli.gui.view_library.view import View
from pamet import register_note_view_type
import pamet
from pamet.desktop_app import trash_icon, link_icon
from pamet.helpers import Url
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.views.note.anchor.edit_widget import AnchorEditWidgetMixin
from pamet.views.note.anchor.props_edit.widget import AnchorEditPropsWidget
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget
from pamet.views.note.text.props_edit.widget import TextEditPropsWidget

log = misli.get_logger(__name__)


class TextEditViewState(NoteEditViewState, TextNote):
    pass


@register_note_view_type(state_type=TextEditViewState,
                         note_type=TextNote,
                         edit=True)
class TextNoteEditWidget(BaseNoteEditWidget, View, AnchorEditWidgetMixin):

    def __init__(self, parent, initial_state: NoteEditViewState):
        super().__init__(parent, initial_state)
        View.__init__(self, initial_state=initial_state)

        # Add the link props widget
        self.link_props_widget: AnchorEditPropsWidget = AnchorEditPropsWidget(
            parent=self)
        self.text_props_widget = TextEditPropsWidget(self)
        self.text_edit = self.text_props_widget.ui.text_edit  # a shorthand

        self.ui.centralAreaWidget.layout().addWidget(self.link_props_widget)

        self.link_props_widget.ui.pametPageLabel.hide()
        self.link_props_widget.ui.invalidUrlLabel.hide()
        self.link_props_widget.ui.urlLineEdit.textChanged.connect(
            self.on_url_change)

        if initial_state.url.is_empty():
            self.link_props_widget.hide()
            self.text_props_widget.ui.get_title_button.hide()
        else:
            self.link_props_widget.ui.urlLineEdit.setText(
                str(initial_state.url))

        self_page = pamet.page(id=initial_state.page_id)
        page_completer = QCompleter(
            (p.name for p in pamet.pages() if p != self_page), parent=self)
        self.link_props_widget.ui.urlLineEdit.setCompleter(page_completer)

        # Setup the text edit props
        self.ui.centralAreaWidget.layout().addWidget(self.text_props_widget)
        self.text_props_widget.ui.get_title_button.clicked.connect(
            self._update_text_from_url)

        self.text_edit.textChanged.connect(self.on_text_change)
        self.text_edit.setPlainText(initial_state.text)

        # Add toolbar actions
        link_button = QPushButton(link_icon, '', self)
        link_button.setCheckable(True)
        trash_button = QPushButton(trash_icon, '', self)
        self.ui.toolbarLayout.addWidget(link_button)
        self.ui.toolbarLayout.addWidget(trash_button)
        link_button.toggled.connect(self.handle_link_button_toggled)

    # This shouldn't be specified explicitly IMO, but I couldn't find the bug
    def focusInEvent(self, event) -> None:
        # print(self.focusPolicy())  -> NoFocus. So why does it not give focus
        # to the text edit automatically.. ?
        self.text_edit.setFocus()

    def on_text_change(self):
        self.edited_note.text = self.text_edit.toPlainText()

    def handle_link_button_toggled(self, checked):
        if checked:
            self.link_props_widget.show()
            self.link_props_widget.ui.urlLineEdit.setFocus()
            self.text_props_widget.ui.get_title_button.show()
        else:
            self.link_props_widget.hide()
            self.edited_note.url = None
            self.text_props_widget.ui.get_title_button.hide()

    def decorate_for_internal_url(self, url_is_internal):
        if url_is_internal:
            self.link_props_widget.ui.pametPageLabel.show()
            self.text_edit.setEnabled(False)
        else:
            self.link_props_widget.ui.pametPageLabel.hide()
            self.text_edit.setEnabled(True)

    def on_url_change(self):
        url_field = self.link_props_widget.ui.urlLineEdit.text()
        self.edited_note.url = url_field

        # If there's no scheme it's probably an internal page (or a web link)
        url = Url(url_field)
        if not url.scheme:
            # We check if it happens to be the name of a note page
            page_by_name = None
            for page in pamet.pages():
                if page.name == url_field:
                    page_by_name = page
                    break

            # If there's a page with that name setup the url accordingly
            if page_by_name:
                self.decorate_for_internal_url(True)
                self.edited_note.url = page_by_name.url()
                self.text_edit.setText(page.name)
            # Else assume it's a web link without a schema
            else:
                self.decorate_for_internal_url(False)

        else:  # If there is a schema
            # If an URI is pasted with a pamet schema
            linked_page: Page = self.edited_note.url.get_page()
            if linked_page:
                self.decorate_for_internal_url(True)
                self.link_props_widget.ui.urlLineEdit.setText(linked_page.name)
                return

    def _update_text_from_url(self):
        linked_page = self.edited_note.url.get_page()
        if linked_page:
            self.text_edit.setText(linked_page.name)

        elif self.edited_note.url.is_custom_uri():
            self.text_edit.setText(
                self.link_props_widget.ui.urlLineEdit.text())

        else:  # Assume web page note
            pass
            # misli.requests.get(self.edited_note.url,
            #     on_complete=w
            # )
