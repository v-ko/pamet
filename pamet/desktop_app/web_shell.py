from pathlib import Path
from PySide6.QtCore import QDir, QUrl
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow


class WebShellWindow(QMainWindow):

    def __init__(self, endpoint: str, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('WebShell')
        self.resize(800, 600)
        self.show()

        # Set the main widget to a QWebEngineView
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)

        # Load the index from the endpoint
        endpoint_url = QUrl(endpoint)
        print(f"Loading URL: {endpoint_url.toString()}")  # Print the URL

        # Show the main window
        self.show()

        self.web_view.load(endpoint_url)
        # self.web_view.load(QUrl("https://www.google.com/"))

        # Connect to the loadFinished signal
        self.web_view.loadFinished.connect(self.handle_load_finished)

        # Show the dev tools
        # Create a new window for the dev tools
        self.dev_tools_window = QMainWindow()
        self.dev_tools_window.setWindowTitle('Dev Tools')
        self.dev_tools_window.resize(800, 600)

        # Create a new QWebEngineView to host the dev tools
        self.dev_tools_view = QWebEngineView()

        # Set the dev tools page to the main view's page
        self.web_view.page().setDevToolsPage(self.dev_tools_view.page())

        # Show the dev tools window
        self.dev_tools_window.setCentralWidget(self.dev_tools_view)
        self.dev_tools_window.show()

    def handle_load_finished(self, ok):
        if ok:
            print("Page loaded successfully.")
        else:
            print("Failed to load page.")

    def load_scripts(self, directory, page):
        # Get the script collection
        script_collection = page.scripts()
        directory = Path(directory)

        # Iterate over the files in the directory
        for filename in directory.iterdir():
            # Only process .js files
            if not filename.suffix == '.js':
                continue

            # Create a new QWebEngineScript
            script = QWebEngineScript()

            # Set the script's source code to the contents of the file
            with open(directory / filename, 'r') as file:
                script.setSourceCode(file.read())

            # Add the script to the collection
            script_collection.insert(script)
