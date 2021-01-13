# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_component.ui'
##
## Created by: Qt User Interface Compiler version 5.15.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_TextNoteEditComponent(object):
    def setupUi(self, TextNoteEditComponent):
        if not TextNoteEditComponent.objectName():
            TextNoteEditComponent.setObjectName(u"TextNoteEditComponent")
        TextNoteEditComponent.resize(469, 338)
        self.verticalLayout = QVBoxLayout(TextNoteEditComponent)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.textEdit = QTextEdit(TextNoteEditComponent)
        self.textEdit.setObjectName(u"textEdit")

        self.verticalLayout.addWidget(self.textEdit)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.ok_button = QPushButton(TextNoteEditComponent)
        self.ok_button.setObjectName(u"ok_button")

        self.horizontalLayout.addWidget(self.ok_button)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(TextNoteEditComponent)

        QMetaObject.connectSlotsByName(TextNoteEditComponent)
    # setupUi

    def retranslateUi(self, TextNoteEditComponent):
        TextNoteEditComponent.setWindowTitle(QCoreApplication.translate("TextNoteEditComponent", u"Form", None))
        self.ok_button.setText(QCoreApplication.translate("TextNoteEditComponent", u"Save (ctrl+S)", None))
#if QT_CONFIG(shortcut)
        self.ok_button.setShortcut(QCoreApplication.translate("TextNoteEditComponent", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

