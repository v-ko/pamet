# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.3.0
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_TextNoteEditViewWidget(object):
    def setupUi(self, TextNoteEditViewWidget):
        if not TextNoteEditViewWidget.objectName():
            TextNoteEditViewWidget.setObjectName(u"TextNoteEditViewWidget")
        TextNoteEditViewWidget.resize(469, 338)
        self.verticalLayout = QVBoxLayout(TextNoteEditViewWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.textEdit = QTextEdit(TextNoteEditViewWidget)
        self.textEdit.setObjectName(u"textEdit")

        self.verticalLayout.addWidget(self.textEdit)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.ok_button = QPushButton(TextNoteEditViewWidget)
        self.ok_button.setObjectName(u"ok_button")

        self.horizontalLayout.addWidget(self.ok_button)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(TextNoteEditViewWidget)

        QMetaObject.connectSlotsByName(TextNoteEditViewWidget)
    # setupUi

    def retranslateUi(self, TextNoteEditViewWidget):
        TextNoteEditViewWidget.setWindowTitle(QCoreApplication.translate("TextNoteEditViewWidget", u"Form", None))
        self.ok_button.setText(QCoreApplication.translate("TextNoteEditViewWidget", u"Save (ctrl+S)", None))
#if QT_CONFIG(shortcut)
        self.ok_button.setShortcut(QCoreApplication.translate("TextNoteEditViewWidget", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

