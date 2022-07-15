# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'widget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

class Ui_TextEditPropsWidget(object):
    def setupUi(self, TextEditPropsWidget):
        if not TextEditPropsWidget.objectName():
            TextEditPropsWidget.setObjectName(u"TextEditPropsWidget")
        TextEditPropsWidget.resize(571, 141)
        self.verticalLayout = QVBoxLayout(TextEditPropsWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.label = QLabel(TextEditPropsWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.get_title_button = QPushButton(TextEditPropsWidget)
        self.get_title_button.setObjectName(u"get_title_button")

        self.horizontalLayout_2.addWidget(self.get_title_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.text_edit = QTextEdit(TextEditPropsWidget)
        self.text_edit.setObjectName(u"text_edit")

        self.verticalLayout.addWidget(self.text_edit)


        self.retranslateUi(TextEditPropsWidget)

        QMetaObject.connectSlotsByName(TextEditPropsWidget)
    # setupUi

    def retranslateUi(self, TextEditPropsWidget):
        TextEditPropsWidget.setWindowTitle(QCoreApplication.translate("TextEditPropsWidget", u"TextEditPropsWidget", None))
        self.label.setText(QCoreApplication.translate("TextEditPropsWidget", u"Text:", None))
        self.get_title_button.setText(QCoreApplication.translate("TextEditPropsWidget", u"Get from URL (Page title)", None))
    # retranslateUi

