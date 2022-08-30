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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_BaseNoteEditWidget(object):
    def setupUi(self, BaseNoteEditWidget):
        if not BaseNoteEditWidget.objectName():
            BaseNoteEditWidget.setObjectName(u"BaseNoteEditWidget")
        BaseNoteEditWidget.resize(640, 480)
        self.verticalLayout = QVBoxLayout(BaseNoteEditWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout = QHBoxLayout()
        self.topLayout.setObjectName(u"topLayout")
        self.topLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.topLayout.addItem(self.horizontalSpacer)

        self.toolbarLayout = QHBoxLayout()
        self.toolbarLayout.setObjectName(u"toolbarLayout")
        self.toolbarLayout.setContentsMargins(6, 6, 6, 6)
        self.devButton = QPushButton(BaseNoteEditWidget)
        self.devButton.setObjectName(u"devButton")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.devButton.sizePolicy().hasHeightForWidth())
        self.devButton.setSizePolicy(sizePolicy)
        self.devButton.setMinimumSize(QSize(0, 0))

        self.toolbarLayout.addWidget(self.devButton)


        self.topLayout.addLayout(self.toolbarLayout)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.topLayout.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.topLayout)

        self.centralAreaWidget = QWidget(BaseNoteEditWidget)
        self.centralAreaWidget.setObjectName(u"centralAreaWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.centralAreaWidget.sizePolicy().hasHeightForWidth())
        self.centralAreaWidget.setSizePolicy(sizePolicy1)
        self.verticalLayout_3 = QVBoxLayout(self.centralAreaWidget)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout.addWidget(self.centralAreaWidget)

        self.bottomLayout = QHBoxLayout()
        self.bottomLayout.setObjectName(u"bottomLayout")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.bottomLayout.addItem(self.horizontalSpacer_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setSpacing(9)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(6, 6, 6, 6)
        self.cancelButton = QPushButton(BaseNoteEditWidget)
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout_4.addWidget(self.cancelButton)

        self.saveButton = QPushButton(BaseNoteEditWidget)
        self.saveButton.setObjectName(u"saveButton")

        self.horizontalLayout_4.addWidget(self.saveButton)


        self.bottomLayout.addLayout(self.horizontalLayout_4)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.bottomLayout.addItem(self.horizontalSpacer_4)


        self.verticalLayout.addLayout(self.bottomLayout)


        self.retranslateUi(BaseNoteEditWidget)

        QMetaObject.connectSlotsByName(BaseNoteEditWidget)
    # setupUi

    def retranslateUi(self, BaseNoteEditWidget):
        BaseNoteEditWidget.setWindowTitle(QCoreApplication.translate("BaseNoteEditWidget", u"BaseNoteEditWidget", None))
        self.devButton.setText(QCoreApplication.translate("BaseNoteEditWidget", u"dev", None))
        self.cancelButton.setText(QCoreApplication.translate("BaseNoteEditWidget", u"Cancel (Esc)", None))
        self.saveButton.setText(QCoreApplication.translate("BaseNoteEditWidget", u"Save (ctrl+s)", None))
#if QT_CONFIG(shortcut)
        self.saveButton.setShortcut(QCoreApplication.translate("BaseNoteEditWidget", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

