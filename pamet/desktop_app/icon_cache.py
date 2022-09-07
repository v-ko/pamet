from PySide6.QtGui import QIcon
from pamet.desktop_app.util import resource_path


class PametQtWidgetsCachedIcons:
    trash: QIcon = None
    link: QIcon = None
    plus: QIcon = None
    text: QIcon = None
    image: QIcon = None

    def load_all(self):
        self.trash = QIcon(str(resource_path('icons/delete-bin-line.svg')))
        self.link = QIcon(str(resource_path('icons/link.svg')))
        self.plus = QIcon(str(resource_path('icons/plus.svg')))
        self.text = QIcon(str(resource_path('icons/text.svg')))
        self.text.addFile(str(resource_path('icons/text.svg')),
                          mode=QIcon.Disabled)
        self.image = QIcon(str(resource_path('icons/image-line.svg')))
        self.more = QIcon(str(resource_path('icons/more-2-line.svg')))
