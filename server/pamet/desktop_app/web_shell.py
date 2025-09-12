from pathlib import Path
import secrets
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow


class WebShellWindow(QMainWindow):

    def __init__(self, endpoint: str, show_dev_tools: bool = True, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Pamet - WebShell')
        self.resize(800, 600)

        # Generate secure token for desktop access
        self.desktop_access_token = secrets.token_urlsafe(32)
        print(f"Generated desktop access token: {self.desktop_access_token}")

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

        # Inject desktop configuration immediately
        self._inject_desktop_config()

        # Conditionally show the dev tools
        if show_dev_tools:
            self._setup_dev_tools()

    def _inject_desktop_config(self):
        """Inject desktop configuration into the web view"""
        script_code = f"""
        // Inject desktop configuration
        window.PAMET_DESKTOP_MODE = true;
        window.PAMET_DESKTOP_ACCESS_TOKEN = '{self.desktop_access_token}';

        console.log('Desktop mode enabled with token:', window.PAMET_DESKTOP_ACCESS_TOKEN);
        """

        script = QWebEngineScript()
        script.setSourceCode(script_code)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)

        self.web_view.page().scripts().insert(script)

    def _setup_dev_tools(self):
        """Setup and show the developer tools window"""
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
            # Re-inject desktop config after page load to ensure it's available
            self._inject_desktop_config()
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
