# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'editnotedialogue.ui'
##
## Created by: Qt User Interface Compiler version 6.3.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_EditNoteDialogue(object):
    def setupUi(self, EditNoteDialogue):
        if not EditNoteDialogue.objectName():
            EditNoteDialogue.setObjectName(u"EditNoteDialogue")
        EditNoteDialogue.resize(384, 220)
        self.actionEscape = QAction(EditNoteDialogue)
        self.actionEscape.setObjectName(u"actionEscape")
        self.verticalLayout = QVBoxLayout(EditNoteDialogue)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, -1, -1, 0)
        self.yearButton = QPushButton(EditNoteDialogue)
        self.yearButton.setObjectName(u"yearButton")

        self.horizontalLayout_2.addWidget(self.yearButton)

        self.monthButton = QPushButton(EditNoteDialogue)
        self.monthButton.setObjectName(u"monthButton")

        self.horizontalLayout_2.addWidget(self.monthButton)

        self.weekButton = QPushButton(EditNoteDialogue)
        self.weekButton.setObjectName(u"weekButton")

        self.horizontalLayout_2.addWidget(self.weekButton)

        self.dayButton = QPushButton(EditNoteDialogue)
        self.dayButton.setObjectName(u"dayButton")

        self.horizontalLayout_2.addWidget(self.dayButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.textEdit = QTextEdit(EditNoteDialogue)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setAcceptRichText(False)

        self.verticalLayout.addWidget(self.textEdit)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.makeLinkButton = QPushButton(EditNoteDialogue)
        self.makeLinkButton.setObjectName(u"makeLinkButton")

        self.horizontalLayout.addWidget(self.makeLinkButton)

        self.openButton = QPushButton(EditNoteDialogue)
        self.openButton.setObjectName(u"openButton")

        self.horizontalLayout.addWidget(self.openButton)

        self.okButton = QPushButton(EditNoteDialogue)
        self.okButton.setObjectName(u"okButton")

        self.horizontalLayout.addWidget(self.okButton)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(EditNoteDialogue)

        QMetaObject.connectSlotsByName(EditNoteDialogue)
    # setupUi

    def retranslateUi(self, EditNoteDialogue):
        EditNoteDialogue.setWindowTitle(QCoreApplication.translate("EditNoteDialogue", u"New note", None))
        self.actionEscape.setText(QCoreApplication.translate("EditNoteDialogue", u"escape", None))
#if QT_CONFIG(shortcut)
        self.actionEscape.setShortcut(QCoreApplication.translate("EditNoteDialogue", u"Esc", None))
#endif // QT_CONFIG(shortcut)
        self.yearButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Year", None))
        self.monthButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Month", None))
        self.weekButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Week", None))
        self.dayButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Day", None))
#if QT_CONFIG(shortcut)
        self.dayButton.setShortcut(QCoreApplication.translate("EditNoteDialogue", u"Ctrl+D", None))
#endif // QT_CONFIG(shortcut)
        self.textEdit.setHtml(QCoreApplication.translate("EditNoteDialogue", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'Cantarell'; font-size:10pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:'Ubuntu'; font-size:11pt;\"><br /></p></body></html>", None))
        self.makeLinkButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Link to...", None))
#if QT_CONFIG(shortcut)
        self.makeLinkButton.setShortcut(QCoreApplication.translate("EditNoteDialogue", u"Ctrl+L", None))
#endif // QT_CONFIG(shortcut)
        self.openButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Open", None))
        self.okButton.setText(QCoreApplication.translate("EditNoteDialogue", u"Ok(Ctrl+S)", None))
#if QT_CONFIG(shortcut)
        self.okButton.setShortcut(QCoreApplication.translate("EditNoteDialogue", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

