from pathlib import Path
from random import choice
import shutil
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton, QWidget
from pamet.desktop_app.config import pamet_data_folder_path
from pamet import desktop_app
from pamet.desktop_app import get_user_settings

from pamet.model.script_note import ScriptNote
from pamet.views.note.card.props_edit.widget import FixedTextEdit
from .name_seed_data import adjectives, fruits, animals

from .ui_props_widget import Ui_ScriptNotePropsWidget

FILE_SCHEMA = 'file://'


def random_name():
    return f'{choice(adjectives)}-{choice(fruits)}-{choice(animals)}'


class ScriptNotePropsWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.ui = Ui_ScriptNotePropsWidget()
        self.ui.setupUi(self)

        self.edit_widget = parent

        # Locals
        self._unsaved_script_changes = False
        config = get_user_settings()
        self._scripts_folder = Path(config.scripts_folder)
        self._scripts_folder.mkdir(parents=True, exist_ok=True)

        # Add the note text edit
        self.text_edit = FixedTextEdit(self)
        self.ui.noteTextVerticalLayout.addWidget(self.text_edit)
        self.text_edit.textChanged.connect(self._handle_text_change)

        # Generate the create script buttons
        self._templates_folder = Path(config.script_templates_folder)
        for template in self._templates_folder.iterdir():
            button = QPushButton(template.stem)
            content = template.read_text()
            extension = template.suffix

            button.clicked.connect(lambda cnt=content, ext=extension: self.
                                   create_script_file(cnt, ext))
            self.ui.createScriptWidget.layout().addWidget(button)

        # Setup the UI according to the note props (is a script path set up)
        script_path = self.edit_widget.edited_note.script_path
        self.ui.scriptPathLineEdit.setText(str(script_path))
        if script_path is None:
            script_path = ''
        self.handle_script_path_change(str(script_path))

        self.ui.argumentsLineEdit.setText(self.edited_note.command_args)
        self.text_edit.setText(self.edited_note.text)

        # Connect the UI with the handlers
        self.ui.scriptPathLineEdit.textChanged.connect(
            self.handle_script_path_change)
        self.ui.scriptNameLineEdit.textChanged.connect(
            self.handle_script_name_change)
        self.ui.renamePushButton.clicked.connect(
            self.handle_rename_button_click)
        self.ui.openInEditorPushButton.clicked.connect(
            self._handle_open_in_editor_button_click)
        self.ui.openContainingFolderPushButton.clicked.connect(
            self._handle_open_containing_folder_button_click)
        self.ui.deletePushButton.clicked.connect(
            self._handle_delete_button_click)
        self.ui.chooseFilePushButton.clicked.connect(self._open_file_chooser)
        self.ui.argumentsLineEdit.textChanged.connect(
            self._handle_args_changed)
        self.ui.setDefaultScriptsFolder.clicked.connect(
            self._set_default_folder)
        self.ui.configureTemplatesButton.clicked.connect(
            self._configure_templates)
        self.ui.runPushButton.clicked.connect(
            lambda: desktop_app.script_runner.run(self.edited_note))
        self.ui.runInTerminalCheckbox.toggled.connect(
            self._handle_run_in_terminal_toggled)

    @property
    def edited_note(self) -> ScriptNote:
        return self.edit_widget.edited_note

    def create_script_file(self, content: str, extension: str):
        script_path = self._scripts_folder
        while script_path.exists():
            script_path = self._scripts_folder / random_name()
            script_path = script_path.with_suffix(extension)

        try:
            script_path.write_text(content)
            # script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        except Exception as e:
            QMessageBox(self, 'Could not write to file',
                        f'Could not create the script file. Exception: {e}')
            return

        self.ui.scriptPathLineEdit.setText(str(script_path))

    def _save_script_changes(self):
        script_path: Path = self.edited_note.script_path
        if not script_path:
            raise Exception

        script_path.write_text(self.edited_note.script_te)

    def _handle_text_change(self):
        self.edited_note.text = self.text_edit.toPlainText()

    def handle_script_path_change(self, new_path: str):
        old_path = self.edited_note.script_path

        if new_path.startswith(FILE_SCHEMA):
            new_path = new_path[len(FILE_SCHEMA):]
            self.ui.scriptPathLineEdit.setText(new_path)
            return

        new_path: Path = Path(new_path)
        self.edited_note.script_path = new_path

        if new_path.exists() and new_path.is_file():
            self.ui.pathErrorLabel.setText('Exists')
            self.ui.deletePushButton.setEnabled(True)
            self.ui.scriptNameLineEdit.setEnabled(True)
            self.ui.scriptNameLineEdit.setText(new_path.name)
            self.ui.openInEditorPushButton.setEnabled(True)
        else:
            if shutil.which(new_path):
                self.ui.pathErrorLabel.setText('Executable')
            else:
                self.ui.pathErrorLabel.setText('Missing')
            self.ui.deletePushButton.setEnabled(False)
            self.ui.scriptNameLineEdit.setEnabled(True)
            self.ui.scriptNameLineEdit.setText('')
            self.ui.openInEditorPushButton.setEnabled(False)

        note_text = self.edited_note.text
        # Keep the text matching the file name except if the user hasn't
        # made an edit (and they differ).
        if not note_text or (old_path and note_text == old_path.name):
            self.text_edit.setText(new_path.name)

    def handle_script_name_change(self, new_name: str):
        if new_name and new_name != self.edited_note.script_path.name:
            self.ui.renamePushButton.setEnabled(True)
        else:
            self.ui.renamePushButton.setEnabled(False)

    def handle_rename_button_click(self):
        script_path: Path = self.edited_note.script_path
        if not (script_path.exists() and script_path.is_file()):
            raise Exception(f'Cannot rename {script_path}. File missing.')

        new_name = self.ui.scriptNameLineEdit.text()
        new_path = script_path.parent / new_name
        try:
            # Make it possible to create a subdir on the spot
            new_path = new_path.resolve()
            new_path.parent.mkdir(parents=True, exist_ok=True)

            script_path.rename(new_path)
        except Exception as e:
            QMessageBox.warning(
                self, 'Error during rename',
                ('Could not rename the file {script_path} to {new_path}.'
                 f' Error: {e}'))
            return

        self.ui.scriptPathLineEdit.setText(str(new_path))

    def _handle_open_in_editor_button_click(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.edited_note.script_path)))

    def _handle_open_containing_folder_button_click(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(
            self.edited_note.script_path.parent)))

    def _handle_delete_button_click(self):
        path = self.edited_note.script_path
        try:
            path.unlink()
        except Exception as e:
            QMessageBox.warning(
                self, 'Error deleting file',
                f'Could not delete file {path}. Exception: {e}')
        self.ui.scriptPathLineEdit.setText('')

    def _open_file_chooser(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose a script file',
                                              str(self._scripts_folder))
        if not path:
            return

        self.ui.scriptPathLineEdit.setText(path)

    def _handle_args_changed(self, new_args_text: str):
        self.edited_note.command_args = new_args_text

    def _set_default_folder(self):
        instructions_text = '''
        The config.json will be opened. You can change the scripts folder there.

        If you don't know what you're doing - it would be best to not touch it.
        '''
        QMessageBox.information(self, 'How to set the folder',
                                instructions_text)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pamet_data_folder_path)))
        self.edit_widget._handle_esc_shortcut()

    def _configure_templates(self):
        instructions_text = '''
        You can add templates to the templates folder, which will be opened
        after you close this prompt.
        To restore the original templates - just delete the files and restart
        the app.
        '''
        QMessageBox.information(self, 'How to set the folder',
                                instructions_text)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._templates_folder)))
        self.edit_widget._handle_esc_shortcut()

    def _handle_run_in_terminal_toggled(self, checked: bool):
        self.edited_note.run_in_terminal = checked
