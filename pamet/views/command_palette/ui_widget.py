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
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QLineEdit,
    QListWidget, QListWidgetItem, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_CommandPaletteWidget(object):
    def setupUi(self, CommandPaletteWidget):
        if not CommandPaletteWidget.objectName():
            CommandPaletteWidget.setObjectName(u"CommandPaletteWidget")
        CommandPaletteWidget.resize(788, 229)
        self.verticalLayout_2 = QVBoxLayout(CommandPaletteWidget)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.lineEdit = QLineEdit(CommandPaletteWidget)
        self.lineEdit.setObjectName(u"lineEdit")

        self.verticalLayout_2.addWidget(self.lineEdit)

        self.suggestionsListWidget = QListWidget(CommandPaletteWidget)
        self.suggestionsListWidget.setObjectName(u"suggestionsListWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.suggestionsListWidget.sizePolicy().hasHeightForWidth())
        self.suggestionsListWidget.setSizePolicy(sizePolicy)
        self.suggestionsListWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.suggestionsListWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout_2.addWidget(self.suggestionsListWidget)

        QWidget.setTabOrder(self.lineEdit, self.suggestionsListWidget)

        self.retranslateUi(CommandPaletteWidget)

        QMetaObject.connectSlotsByName(CommandPaletteWidget)
    # setupUi

    def retranslateUi(self, CommandPaletteWidget):
        CommandPaletteWidget.setWindowTitle(QCoreApplication.translate("CommandPaletteWidget", u"CommandPaletteWidget", None))
    # retranslateUi

