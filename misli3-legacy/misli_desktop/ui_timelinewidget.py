# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'timelinewidget.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Ui_TimelineWidget(object):
    def setupUi(self, TimelineWidget):
        if not TimelineWidget.objectName():
            TimelineWidget.setObjectName(u"TimelineWidget")
        TimelineWidget.resize(707, 360)
        self.horizontalLayout = QHBoxLayout(TimelineWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.sidebar = QVBoxLayout()
        self.sidebar.setObjectName(u"sidebar")
        self.googleTimelinePushButton = QPushButton(TimelineWidget)
        self.googleTimelinePushButton.setObjectName(u"googleTimelinePushButton")

        self.sidebar.addWidget(self.googleTimelinePushButton)


        self.horizontalLayout.addLayout(self.sidebar)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetDefaultConstraint)

        self.horizontalLayout.addLayout(self.verticalLayout)


        self.retranslateUi(TimelineWidget)

        QMetaObject.connectSlotsByName(TimelineWidget)
    # setupUi

    def retranslateUi(self, TimelineWidget):
        TimelineWidget.setWindowTitle(QCoreApplication.translate("TimelineWidget", u"Form", None))
        self.googleTimelinePushButton.setText(QCoreApplication.translate("TimelineWidget", u"Go to Google Timeline", None))
    # retranslateUi

