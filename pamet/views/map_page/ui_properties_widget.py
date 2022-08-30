# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'properties_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_MapPagePropertiesWidget(object):
    def setupUi(self, MapPagePropertiesWidget):
        if not MapPagePropertiesWidget.objectName():
            MapPagePropertiesWidget.setObjectName(u"MapPagePropertiesWidget")
        MapPagePropertiesWidget.resize(335, 503)
        self.verticalLayout = QVBoxLayout(MapPagePropertiesWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(MapPagePropertiesWidget)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.nameLineEdit = QLineEdit(MapPagePropertiesWidget)
        self.nameLineEdit.setObjectName(u"nameLineEdit")

        self.verticalLayout.addWidget(self.nameLineEdit)

        self.nameWarningLabel = QLabel(MapPagePropertiesWidget)
        self.nameWarningLabel.setObjectName(u"nameWarningLabel")

        self.verticalLayout.addWidget(self.nameWarningLabel)

        self.saveButton = QPushButton(MapPagePropertiesWidget)
        self.saveButton.setObjectName(u"saveButton")

        self.verticalLayout.addWidget(self.saveButton)

        self.line = QFrame(MapPagePropertiesWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 10, -1, -1)
        self.setAsHomePageCheckBox = QCheckBox(MapPagePropertiesWidget)
        self.setAsHomePageCheckBox.setObjectName(u"setAsHomePageCheckBox")

        self.horizontalLayout_2.addWidget(self.setAsHomePageCheckBox)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.verticalSpacer = QSpacerItem(20, 274, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.deleteButton = QPushButton(MapPagePropertiesWidget)
        self.deleteButton.setObjectName(u"deleteButton")

        self.verticalLayout.addWidget(self.deleteButton)


        self.retranslateUi(MapPagePropertiesWidget)

        QMetaObject.connectSlotsByName(MapPagePropertiesWidget)
    # setupUi

    def retranslateUi(self, MapPagePropertiesWidget):
        MapPagePropertiesWidget.setWindowTitle(QCoreApplication.translate("MapPagePropertiesWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("MapPagePropertiesWidget", u"Name:", None))
        self.nameWarningLabel.setText(QCoreApplication.translate("MapPagePropertiesWidget", u"You should not be seeing this, lol", None))
        self.saveButton.setText(QCoreApplication.translate("MapPagePropertiesWidget", u"Save (Ctrl+S)", None))
#if QT_CONFIG(shortcut)
        self.saveButton.setShortcut(QCoreApplication.translate("MapPagePropertiesWidget", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.setAsHomePageCheckBox.setText(QCoreApplication.translate("MapPagePropertiesWidget", u"Set as home page when starting the app", None))
        self.deleteButton.setText(QCoreApplication.translate("MapPagePropertiesWidget", u"Delete page", None))
    # retranslateUi

