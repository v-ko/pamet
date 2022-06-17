from __future__ import annotations

from PySide6.QtWidgets import QCompleter, QPushButton

import misli
from pamet.desktop_app import trash_icon, link_icon
from misli.gui.view_library.view import View
from pamet import register_note_view_type
import pamet
from pamet.model.anchor_note import AnchorNote
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.views.note.anchor.props_edit.widget import AnchorEditPropsWidget
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget
from pamet.actions import map_page as map_page_actions

log = misli.get_logger(__name__)


class AnchorEditViewState(NoteEditViewState, AnchorNote):
    pass


@register_note_view_type(state_type=AnchorEditViewState,
                         note_type=AnchorNote,
                         edit=True)
class AnchorEditWidget(BaseNoteEditWidget, View):

    def __init__(self, parent, initial_state: AnchorEditViewState):
        super().__init__(parent, initial_state)
        View.__init__(self, initial_state=initial_state)

        self.props_widget: AnchorEditPropsWidget = AnchorEditPropsWidget(
            parent=self)

        self.ui.centralAreaWidget.layout().addWidget(self.props_widget)
        self.props_widget.ui.pametPageLabel.hide()
        self.props_widget.ui.invalidUrlLabel.hide()

        # Add toolbar actions
        link_button = QPushButton(link_icon, '', self)
        link_button.setCheckable(True)
        link_button.setChecked(True)
        trash_button = QPushButton(trash_icon, '', self)
        self.ui.toolbarLayout.addWidget(link_button)
        self.ui.toolbarLayout.addWidget(trash_button)
        link_button.toggled.connect(self.handle_link_button_toggled)

        self.props_widget.ui.text_edit.textChanged.connect(self.on_text_change)
        self.props_widget.ui.urlLineEdit.textChanged.connect(
            self.on_url_change)
        self.props_widget.ui.text_edit.setPlainText(initial_state.text)
        self.props_widget.ui.urlLineEdit.setText(initial_state.url)

        page_completer = QCompleter((p.name for p in pamet.pages()),
                                    parent=self)
        self.props_widget.ui.urlLineEdit.setCompleter(page_completer)

        self.props_widget.ui.get_title_button.clicked.connect(
            self._update_text_from_url)

    # This shouldn't be specified explicitly IMO, but I couldn't find the bug
    def focusInEvent(self, event) -> None:
        self.props_widget.ui.urlLineEdit.setFocus()

    def on_text_change(self):
        self.edited_note.text = self.props_widget.ui.text_edit.toPlainText()

    def decorate_for_internal_url(self, url_is_internal):
        if url_is_internal:
            self.props_widget.ui.pametPageLabel.show()
            self.props_widget.ui.text_edit.setEnabled(False)
        else:
            self.props_widget.ui.pametPageLabel.hide()
            self.props_widget.ui.text_edit.setEnabled(True)

    def on_url_change(self):
        url_field = self.props_widget.ui.urlLineEdit.text()
        self.edited_note.url = url_field

        # If there's no scheme it's probably an internal page (or a web link)
        if not self.edited_note.parsed_url.scheme:
            # We check if it happens to be the name of a note page
            page_by_name = None
            for page in pamet.pages():
                if page.name == url_field:
                    page_by_name = page
                    break

            # If there's a page with that name setup the url accordingly
            if page_by_name:
                self.decorate_for_internal_url(True)
                self.edited_note.url = f'pamet:///p/{page_by_name.id}'
                self.props_widget.ui.text_edit.setText(page.name)
            # Else assume it's a web link without a schema
            else:
                self.decorate_for_internal_url(False)

        else:  # If there is a schema
            # If an URI is pasted with a pamet schema
            linked_page: Page = self.edited_note.linked_page()
            if linked_page:
                self.decorate_for_internal_url(True)
                self.props_widget.ui.urlLineEdit.setText(linked_page.name)
                return

    def _update_text_from_url(self):
        linked_page = self.edited_note.linked_page()
        if linked_page:
            self.props_widget.ui.text_edit.setText(linked_page.name)

        elif self.edited_note.is_custom_uri():
            self.props_widget.ui.text_edit.setText(
                self.props_widget.ui.urlLineEdit.text())

        else:  # Assume web page note
            pass
            # misli.requests.get(self.edited_note.url,
            #     on_complete=w
            # )

    def handle_link_button_toggled(self, checked):
        if checked:
            raise Exception('Should only be unchecked in a text note edit')
        note_dict = self.edited_note.asdict()
        note = TextNote(**note_dict)

        map_page_actions.switch_note_type(self.parent().state(), note)
