# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'widget.ui'
##
## Created by: Qt User Interface Compiler version 6.3.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLineEdit, QListWidget, QListWidgetItem,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_SearchBarWidget(object):
    def setupUi(self, SearchBarWidget):
        if not SearchBarWidget.objectName():
            SearchBarWidget.setObjectName(u"SearchBarWidget")
        SearchBarWidget.resize(453, 525)
        self.verticalLayout = QVBoxLayout(SearchBarWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.searchLineEdit = QLineEdit(SearchBarWidget)
        self.searchLineEdit.setObjectName(u"searchLineEdit")

        self.verticalLayout.addWidget(self.searchLineEdit)

        self.resultsListWidget = QListWidget(SearchBarWidget)
        self.resultsListWidget.setObjectName(u"resultsListWidget")
        self.resultsListWidget.setStyleSheet(u"")
        self.resultsListWidget.setProperty("isWrapping", False)
        self.resultsListWidget.setSpacing(4)
        self.resultsListWidget.setWordWrap(True)

        self.verticalLayout.addWidget(self.resultsListWidget)


        self.retranslateUi(SearchBarWidget)

        QMetaObject.connectSlotsByName(SearchBarWidget)
    # setupUi

    def retranslateUi(self, SearchBarWidget):
        SearchBarWidget.setWindowTitle(QCoreApplication.translate("SearchBarWidget", u"SearchBarWidget", None))
    # retranslateUi

