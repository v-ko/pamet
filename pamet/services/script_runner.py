import os
import shutil
from pathlib import Path
import subprocess
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox
import pamet
from pamet import desktop_app
from pamet.model.script_note import ScriptNote

python_missing_text = '''
Python is not installed on your system. Install it and try again.
It's best to do so with your package manager/ app store.
'''
dependency_missing_text = 'Dependency missing'


def google_url(search_text: str):
    url = f'https://www.google.com/search?q={search_text.replace(" ", "+")}'
    return url


def no_bash_warning():
    QMessageBox(
        QApplication.activeWindow(), 'No bash :(',
        ('Bash not found. Support for non-linux systems'
            ' is not fully implemented yet. Checkout the '
            'github issues for the project'))


class ScriptRunner:

    def __init__(self):
        pass

    def run(self, note: ScriptNote):
        # Veeery Ad-hoc ATM
        command = f'{note.script_path} {note.command_args}'
        path: Path = note.script_path

        if path.suffix == '.py':
            if os.name == 'nt':
                if not shutil.which('py'):
                    QMessageBox.information(QApplication.activeWindow(),
                                            dependency_missing_text,
                                            python_missing_text)

                    QDesktopServices.openUrl(
                        QUrl(google_url('microsoft store python')))
                    return
                command = f'py {command}'
            elif os.name == 'posix':
                if not shutil.which('python'):
                    QMessageBox.information(QApplication.activeWindow(),
                                            dependency_missing_text,
                                            python_missing_text)
                    QDesktopServices.openUrl(QUrl(
                        google_url('install python')))
                    return
                command = f'python {command}'
        elif path.suffix == '.sh':
            if os.name == 'nt':
                QMessageBox.warning(
                    QApplication.activeWindow(), 'Cannot run script',
                    ('Running bash scripts in Windows not implemented. '
                     'It\'s probably possible via WSL.'))
                return

            if not shutil.which('bash'):
                no_bash_warning()
                return
            command = f'bash {command}'

        config = desktop_app.get_user_settings()
        if note.run_in_terminal:
            if os.name == 'posix':
                if not shutil.which('bash'):
                    no_bash_warning()
                    return
                escaped = command.replace('"', '\\"')
                command = f'bash -c "{escaped}; bash"'
                command = f'{config.run_in_terminal_prefix_posix}{command}'
            elif os.name == 'nt':
                command = f'{config.run_in_terminal_prefix_windows}{command}'

        subprocess.run(command, shell=True)
