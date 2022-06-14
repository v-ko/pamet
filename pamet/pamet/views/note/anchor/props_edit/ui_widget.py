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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_AnchorEditPropsWidget(object):
    def setupUi(self, AnchorEditPropsWidget):
        if not AnchorEditPropsWidget.objectName():
            AnchorEditPropsWidget.setObjectName(u"AnchorEditPropsWidget")
        AnchorEditPropsWidget.resize(571, 231)
        self.verticalLayout = QVBoxLayout(AnchorEditPropsWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_2 = QLabel(AnchorEditPropsWidget)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(9, -1, -1, -1)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.pametPageLabel = QLabel(AnchorEditPropsWidget)
        self.pametPageLabel.setObjectName(u"pametPageLabel")

        self.horizontalLayout_3.addWidget(self.pametPageLabel)

        self.urlLineEdit = QLineEdit(AnchorEditPropsWidget)
        self.urlLineEdit.setObjectName(u"urlLineEdit")

        self.horizontalLayout_3.addWidget(self.urlLineEdit)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.invalidUrlLabel = QLabel(AnchorEditPropsWidget)
        self.invalidUrlLabel.setObjectName(u"invalidUrlLabel")

        self.verticalLayout_2.addWidget(self.invalidUrlLabel)


        self.verticalLayout.addLayout(self.verticalLayout_2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.label = QLabel(AnchorEditPropsWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.get_title_button = QPushButton(AnchorEditPropsWidget)
        self.get_title_button.setObjectName(u"get_title_button")

        self.horizontalLayout_2.addWidget(self.get_title_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.text_edit = QTextEdit(AnchorEditPropsWidget)
        self.text_edit.setObjectName(u"text_edit")

        self.verticalLayout.addWidget(self.text_edit)


        self.retranslateUi(AnchorEditPropsWidget)

        QMetaObject.connectSlotsByName(AnchorEditPropsWidget)
    # setupUi

    def retranslateUi(self, AnchorEditPropsWidget):
        AnchorEditPropsWidget.setWindowTitle(QCoreApplication.translate("AnchorEditPropsWidget", u"AnchorEditPropsWidget", None))
        self.label_2.setText(QCoreApplication.translate("AnchorEditPropsWidget", u"URL or pamet page:", None))
        self.pametPageLabel.setText(QCoreApplication.translate("AnchorEditPropsWidget", u"Pamet page:", None))
        self.invalidUrlLabel.setText(QCoreApplication.translate("AnchorEditPropsWidget", u"Invalid URL", None))
        self.label.setText(QCoreApplication.translate("AnchorEditPropsWidget", u"Text:", None))
        self.get_title_button.setText(QCoreApplication.translate("AnchorEditPropsWidget", u"Get from URL (Page title)", None))
    # retranslateUi

