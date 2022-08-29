#!/usr/bin/env python
import sys

from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QMainWindow
from PySide2.QtGui import QPixmap

from ui_viewer import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    def prev_clicked():
        bcg = QPixmap('rick.png').scaled(window.ui.imageDisplayLabel.size())
        window.ui.imageDisplayLabel.setPixmap(bcg)

    def next_clicked():
        print("Next clicked")

    window.ui.nextButton.clicked.connect(next_clicked)
    window.ui.previousButton.clicked.connect(prev_clicked)

    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
