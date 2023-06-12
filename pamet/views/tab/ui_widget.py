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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLineEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_TabMainWidget(object):
    def setupUi(self, TabMainWidget):
        if not TabMainWidget.objectName():
            TabMainWidget.setObjectName(u"TabMainWidget")
        TabMainWidget.resize(1019, 625)
        self.horizontalLayout = QHBoxLayout(TabMainWidget)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.leftSidebarContainer = QWidget(TabMainWidget)
        self.leftSidebarContainer.setObjectName(u"leftSidebarContainer")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(5)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftSidebarContainer.sizePolicy().hasHeightForWidth())
        self.leftSidebarContainer.setSizePolicy(sizePolicy)
        self.leftSidebarContainer.setMinimumSize(QSize(100, 0))
        self.verticalLayout = QVBoxLayout(self.leftSidebarContainer)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.leftSidebarCloseButton = QPushButton(self.leftSidebarContainer)
        self.leftSidebarCloseButton.setObjectName(u"leftSidebarCloseButton")

        self.verticalLayout.addWidget(self.leftSidebarCloseButton)


        self.horizontalLayout.addWidget(self.leftSidebarContainer)

        self.centralContainer = QWidget(TabMainWidget)
        self.centralContainer.setObjectName(u"centralContainer")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(30)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.centralContainer.sizePolicy().hasHeightForWidth())
        self.centralContainer.setSizePolicy(sizePolicy1)
        self.verticalLayout_3 = QVBoxLayout(self.centralContainer)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.commandLineEdit = QLineEdit(self.centralContainer)
        self.commandLineEdit.setObjectName(u"commandLineEdit")

        self.verticalLayout_3.addWidget(self.commandLineEdit)

        self.centralLayout = QHBoxLayout()
        self.centralLayout.setSpacing(0)
        self.centralLayout.setObjectName(u"centralLayout")
        self.mapPageContainer = QWidget(self.centralContainer)
        self.mapPageContainer.setObjectName(u"mapPageContainer")
        sizePolicy2 = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.mapPageContainer.sizePolicy().hasHeightForWidth())
        self.mapPageContainer.setSizePolicy(sizePolicy2)
        self.horizontalLayout_2 = QHBoxLayout(self.mapPageContainer)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.centralLayout.addWidget(self.mapPageContainer)

        self.tourContainer = QWidget(self.centralContainer)
        self.tourContainer.setObjectName(u"tourContainer")
        sizePolicy3 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.tourContainer.sizePolicy().hasHeightForWidth())
        self.tourContainer.setSizePolicy(sizePolicy3)
        self.horizontalLayout_3 = QHBoxLayout(self.tourContainer)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)

        self.centralLayout.addWidget(self.tourContainer)


        self.verticalLayout_3.addLayout(self.centralLayout)


        self.horizontalLayout.addWidget(self.centralContainer)

        self.rightSidebarContainer = QWidget(TabMainWidget)
        self.rightSidebarContainer.setObjectName(u"rightSidebarContainer")
        sizePolicy4 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy4.setHorizontalStretch(5)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.rightSidebarContainer.sizePolicy().hasHeightForWidth())
        self.rightSidebarContainer.setSizePolicy(sizePolicy4)
        self.rightSidebarContainer.setMinimumSize(QSize(100, 0))
        self.verticalLayout_2 = QVBoxLayout(self.rightSidebarContainer)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.rightSidebarCloseButton = QPushButton(self.rightSidebarContainer)
        self.rightSidebarCloseButton.setObjectName(u"rightSidebarCloseButton")

        self.verticalLayout_2.addWidget(self.rightSidebarCloseButton)


        self.horizontalLayout.addWidget(self.rightSidebarContainer)


        self.retranslateUi(TabMainWidget)

        QMetaObject.connectSlotsByName(TabMainWidget)
    # setupUi

    def retranslateUi(self, TabMainWidget):
        TabMainWidget.setWindowTitle(QCoreApplication.translate("TabMainWidget", u"Form", None))
        self.leftSidebarCloseButton.setText(QCoreApplication.translate("TabMainWidget", u"<", None))
        self.rightSidebarCloseButton.setText(QCoreApplication.translate("TabMainWidget", u">", None))
    # retranslateUi

