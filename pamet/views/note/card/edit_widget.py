from __future__ import annotations
from PySide6.QtGui import QCloseEvent
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply

from PySide6.QtWidgets import QCompleter, QPushButton

import fusion
from pamet import register_note_view_type

import pamet
from pamet.desktop_app import icons
from pamet.util.url import Url
from pamet.model.card_note import CardNote
from pamet.model.image_note import ImageNote
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.views.note.image.props_edit.widget import ImagePropsWidget
from pamet.views.note.anchor.edit_widget import AnchorEditWidgetMixin
from pamet.views.note.anchor.props_edit.widget import AnchorEditPropsWidget
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget
from pamet.views.note.card.props_edit.widget import TextEditPropsWidget

log = fusion.get_logger(__name__)


class CardEditViewState(NoteEditViewState):
    pass


@register_note_view_type(state_type=CardEditViewState,
                         note_type=(TextNote, ImageNote, CardNote),
                         edit=True)
class CardNoteEditWidget(BaseNoteEditWidget, AnchorEditWidgetMixin):

    def __init__(self, parent, initial_state: CardEditViewState):
        super().__init__(parent, initial_state)
        self._network_am = QNetworkAccessManager(self)
        self._image_download_reply: QNetworkReply = None

        # Add the link props widget
        self.text_props_widget = TextEditPropsWidget(self)
        self.image_props_widget = ImagePropsWidget(self)
        self.link_props_widget = AnchorEditPropsWidget(self)

        self.ui.centralAreaWidget.layout().addWidget(self.link_props_widget)
        self.ui.centralAreaWidget.layout().addWidget(self.image_props_widget)
        self.ui.centralAreaWidget.layout().addWidget(self.text_props_widget)

        # Setup the link props widget
        self.link_props_widget.ui.pametPageLabel.hide()
        self.link_props_widget.ui.invalidUrlLabel.hide()
        self.link_props_widget.ui.urlLineEdit.textChanged.connect(
            self.on_url_change)

        # Setup a completer with all the page names except the current one
        self_page = pamet.page(initial_state.page_id)
        page_completer = QCompleter(
            (p.name for p in pamet.pages() if p != self_page), parent=self)
        self.link_props_widget.ui.urlLineEdit.setCompleter(page_completer)

        # Setup the text props widget

        if isinstance(self.edited_note, (TextNote, CardNote)):
            self.text_edit.setPlainText(self.edited_note.text)

        # Add toolbar actions
        self.text_button = QPushButton(icons.text, '', self)
        self.text_button.setCheckable(True)
        self.ui.toolbarLayout.insertWidget(0, self.text_button)

        self.image_button = QPushButton(icons.image, '', self)
        self.image_button.setCheckable(True)
        self.ui.toolbarLayout.insertWidget(1, self.image_button)

        self.link_button = QPushButton(icons.link, '', self)
        self.link_button.setCheckable(True)
        self.ui.toolbarLayout.insertWidget(2, self.link_button)

        # Setup the buttons according to the type of the edited note
        if isinstance(self.edited_note, ImageNote):
            self.image_button.setChecked(True)
        else:
            self.image_props_widget.hide()

        if isinstance(self.edited_note, TextNote):
            self.text_button.setChecked(True)
        else:
            self.text_props_widget.hide()
        # The card note inherits both, so if it's a card - both will be checked

        # Setup the link button and line edit
        if initial_state.url.is_empty():
            self.link_props_widget.hide()
            self.text_props_widget.ui.getTitleButton.hide()
        else:
            self.link_button.setChecked(True)
            self.link_props_widget.ui.urlLineEdit.setText(
                str(initial_state.url))

        self.text_button.toggled.connect(self.handle_text_button_toggled)
        self.image_button.toggled.connect(self.handle_image_button_toggled)
        self.link_button.toggled.connect(self.handle_link_button_toggled)
        self.update_buttons_from_note_type()

    @property
    def text_edit(self):
        return self.text_props_widget.text_edit

    # This shouldn't be specified explicitly IMO, but I couldn't find the bug
    def focusInEvent(self, event) -> None:
        edited_note = self.edited_note

        if not self.edited_note.url.is_empty():
            self.link_props_widget.ui.urlLineEdit.setFocus()
        elif isinstance(edited_note, TextNote):
            self.text_edit.setFocus()
        elif isinstance(edited_note, ImageNote):
            self.image_props_widget.ui.urlLineEdit.setFocus()
        elif isinstance(edited_note, CardNote):
            self.text_edit.setFocus()

    def update_note_type_from_buttons(self):
        if self.text_button.isChecked() and self.image_button.isChecked():
            self.edited_note = CardNote(**self.edited_note.asdict())
        elif self.text_button.isChecked():
            self.edited_note = TextNote(**self.edited_note.asdict())
        elif self.image_button.isChecked():
            self.edited_note = ImageNote(**self.edited_note.asdict())
        else:
            raise Exception

        self.update_buttons_from_note_type()

    def update_buttons_from_note_type(self):
        # Should show/hide the widget and if toggled off and the text is not
        # shown - show it (i.e. revert to basic text note)
        if not (self.text_button.isChecked() or self.image_button.isChecked()):
            self.text_button.setChecked(True)

        # Don't allow removing the text if there's no image
        elif self.text_button.isChecked() and \
                not self.image_button.isChecked():
            self.text_button.setEnabled(False)
        else:
            self.text_button.setEnabled(True)

    def handle_text_button_toggled(self, checked: bool):
        if checked:
            self.text_props_widget.show()
        else:
            self.text_props_widget.hide()
        self.update_buttons_from_note_type()
        self.update_note_type_from_buttons()

    def handle_image_button_toggled(self, checked: bool):
        if checked:
            self.image_props_widget.show()
            self.image_props_widget.ui.urlLineEdit.setFocus()

            if not self.text_edit.toPlainText():
                self.text_button.setChecked(False)  # This should call the hide
        else:
            self.image_props_widget.hide()
        self.update_buttons_from_note_type()
        self.update_note_type_from_buttons()

    def handle_link_button_toggled(self, checked: bool):
        if checked:
            self.link_props_widget.show()
            self.link_props_widget.ui.urlLineEdit.setFocus()
            self.text_props_widget.ui.getTitleButton.show()
        else:
            self.link_props_widget.hide()
            self.edited_note.url = None
            self.text_props_widget.ui.getTitleButton.hide()

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
                self.text_edit.setText(page_by_name.name)
                self.edited_note.text = page_by_name.name
            # Else assume it's a web link without a schema
            else:
                self.decorate_for_internal_url(False)

        else:  # If there is a schema
            # If an URI is pasted with a pamet schema
            linked_page: Page = pamet.page(self.edited_note.url.get_page_id())
            if linked_page:
                self.decorate_for_internal_url(True)
                self.link_props_widget.ui.urlLineEdit.setText(linked_page.name)
                return

            # If it's clearly a web URL and the user has set the text -
            # get the title
            if url.scheme in ['http', 'https'] and \
                    not self.text_edit.toPlainText():
                self.text_props_widget._get_title()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._image_download_reply:
            self._image_download_reply.abort()
        return super().closeEvent(event)
