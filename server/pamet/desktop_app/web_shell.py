import json
from pathlib import Path

from pamet.services.rest_api.auth import DESKTOP_ACCESS_TOKEN
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow, QSplitter


class WebShellWindow(QMainWindow):

    def __init__(
        self,
        endpoint: str,
        desktop_api_base_url: str,
        show_dev_tools: bool = True,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.setWindowTitle("Pamet - WebShell")
        self.resize(800, 600)

        self.desktop_access_token = DESKTOP_ACCESS_TOKEN
        self.desktop_api_base_url = desktop_api_base_url

        # Create the main web view
        self.web_view = QWebEngineView()

        # Store the show_dev_tools flag for layout decisions
        self.show_dev_tools = show_dev_tools

        if show_dev_tools:
            # Create a splitter for elegant dev tools integration
            self.splitter = QSplitter()
            self.setCentralWidget(self.splitter)

            # Add main web view to splitter
            self.splitter.addWidget(self.web_view)

            # We'll add dev tools view later after determining aspect ratio
            self.dev_tools_view = None
        else:
            # Just use web view as central widget if no dev tools
            self.setCentralWidget(self.web_view)

        # Load the index from the endpoint
        endpoint_url = QUrl(endpoint)
        print(f"Loading URL: {endpoint_url.toString()}")

        # Inject desktop configuration before first navigation so it is
        # available during module initialization in the page.
        self._inject_desktop_config()

        # Connect to the loadFinished signal
        self.web_view.loadFinished.connect(self.handle_load_finished)

        # Show the main window
        self.show()

        self.web_view.load(endpoint_url)

        # Setup dev tools if requested
        if show_dev_tools:
            self._setup_dev_tools()

    def _inject_desktop_config(self):
        """Inject desktop access token into the web view"""
        token_json = json.dumps(self.desktop_access_token or "")
        api_base_url_json = json.dumps(self.desktop_api_base_url or "")
        script_code = f"""
        // Inject desktop access token for API authentication
        window.PAMET_DESKTOP_ACCESS_TOKEN = {token_json};
        window.PAMET_DESKTOP_API_BASE_URL = {api_base_url_json};

        console.log('Desktop access token injected');
        """

        script = QWebEngineScript()
        script.setSourceCode(script_code)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)

        self.web_view.page().scripts().insert(script)

    def _setup_dev_tools(self):
        """Setup and show the developer tools integrated in the same window"""
        # Create the dev tools view
        self.dev_tools_view = QWebEngineView()

        # Set the dev tools page to the main view's page
        self.web_view.page().setDevToolsPage(self.dev_tools_view.page())

        # Add the dev tools view to the splitter
        self.splitter.addWidget(self.dev_tools_view)

        # Set initial layout based on current aspect ratio
        self._update_dev_tools_layout()

        # Connect to resize events to update layout dynamically
        self.resizeEvent = self._on_resize

    def _update_dev_tools_layout(self):
        """Update dev tools layout based on window aspect ratio"""
        if not self.show_dev_tools or not self.dev_tools_view:
            return

        width = self.width()
        height = self.height()
        aspect_ratio = width / height if height > 0 else 1.0

        # Determine orientation based on aspect ratio
        # Wide windows (aspect ratio > 1.3) -> place dev tools to the right
        # Tall/square windows (aspect ratio <= 1.3) -> place dev tools below
        if aspect_ratio > 1.3:
            # Wide layout: main content on left, dev tools on right
            self.splitter.setOrientation(Qt.Orientation.Horizontal)
            # Split equally (50% vs 50%)
            self.splitter.setSizes([int(width * 0.5), int(width * 0.5)])
        else:
            # Tall layout: main content on top, dev tools below
            self.splitter.setOrientation(Qt.Orientation.Vertical)
            # Split equally (50% vs 50%)
            self.splitter.setSizes([int(height * 0.5), int(height * 0.5)])

    def _on_resize(self, event):
        """Handle window resize events to update dev tools layout"""
        # Call the original resize event handler
        super().resizeEvent(event)

        # Update dev tools layout based on new aspect ratio
        self._update_dev_tools_layout()

    def handle_load_finished(self, ok):
        if ok:
            print("Page loaded successfully.")
        else:
            print(
                "Failed to load page. Maybe you're debugging and the frontend server is not started?"
            )

    def load_scripts(self, directory, page):
        # Get the script collection
        script_collection = page.scripts()
        directory = Path(directory)

        # Iterate over the files in the directory
        for filename in directory.iterdir():
            # Only process .js files
            if not filename.suffix == ".js":
                continue

            # Create a new QWebEngineScript
            script = QWebEngineScript()

            # Set the script's source code to the contents of the file
            with open(directory / filename, "r") as file:
                script.setSourceCode(file.read())

            # Add the script to the collection
            script_collection.insert(script)
