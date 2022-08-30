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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_ImagePropsWidget(object):
    def setupUi(self, ImagePropsWidget):
        if not ImagePropsWidget.objectName():
            ImagePropsWidget.setObjectName(u"ImagePropsWidget")
        ImagePropsWidget.resize(679, 93)
        self.horizontalLayout = QHBoxLayout(ImagePropsWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.openFileButton = QPushButton(ImagePropsWidget)
        self.openFileButton.setObjectName(u"openFileButton")

        self.verticalLayout.addWidget(self.openFileButton)

        self.urlLineEdit = QLineEdit(ImagePropsWidget)
        self.urlLineEdit.setObjectName(u"urlLineEdit")

        self.verticalLayout.addWidget(self.urlLineEdit)


        self.horizontalLayout.addLayout(self.verticalLayout)

        self.infoLabel = QLabel(ImagePropsWidget)
        self.infoLabel.setObjectName(u"infoLabel")
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.infoLabel.sizePolicy().hasHeightForWidth())
        self.infoLabel.setSizePolicy(sizePolicy)
        self.infoLabel.setAutoFillBackground(True)
        self.infoLabel.setAlignment(Qt.AlignCenter)
        self.infoLabel.setWordWrap(True)

        self.horizontalLayout.addWidget(self.infoLabel)


        self.retranslateUi(ImagePropsWidget)

        QMetaObject.connectSlotsByName(ImagePropsWidget)
    # setupUi

    def retranslateUi(self, ImagePropsWidget):
        ImagePropsWidget.setWindowTitle(QCoreApplication.translate("ImagePropsWidget", u"ImagePropsWidget", None))
        self.openFileButton.setText(QCoreApplication.translate("ImagePropsWidget", u"Open file", None))
        self.infoLabel.setText(QCoreApplication.translate("ImagePropsWidget", u"No image selected", None))
    # retranslateUi

