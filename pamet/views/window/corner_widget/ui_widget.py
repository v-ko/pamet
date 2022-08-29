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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QPushButton, QSizePolicy,
    QWidget)

class Ui_CornerWidget(object):
    def setupUi(self, CornerWidget):
        if not CornerWidget.objectName():
            CornerWidget.setObjectName(u"CornerWidget")
        CornerWidget.resize(366, 46)
        self.horizontalLayout = QHBoxLayout(CornerWidget)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.navigationBackButton = QPushButton(CornerWidget)
        self.navigationBackButton.setObjectName(u"navigationBackButton")

        self.horizontalLayout.addWidget(self.navigationBackButton)

        self.navigationToggleButton = QPushButton(CornerWidget)
        self.navigationToggleButton.setObjectName(u"navigationToggleButton")

        self.horizontalLayout.addWidget(self.navigationToggleButton)

        self.navigationForwardButton = QPushButton(CornerWidget)
        self.navigationForwardButton.setObjectName(u"navigationForwardButton")

        self.horizontalLayout.addWidget(self.navigationForwardButton)

        self.menuButton = QPushButton(CornerWidget)
        self.menuButton.setObjectName(u"menuButton")

        self.horizontalLayout.addWidget(self.menuButton)


        self.retranslateUi(CornerWidget)

        QMetaObject.connectSlotsByName(CornerWidget)
    # setupUi

    def retranslateUi(self, CornerWidget):
        CornerWidget.setWindowTitle(QCoreApplication.translate("CornerWidget", u"CornerWidget", None))
        self.navigationBackButton.setText(QCoreApplication.translate("CornerWidget", u"<", None))
#if QT_CONFIG(shortcut)
        self.navigationBackButton.setShortcut(QCoreApplication.translate("CornerWidget", u"Alt+Left", None))
#endif // QT_CONFIG(shortcut)
        self.navigationToggleButton.setText(QCoreApplication.translate("CornerWidget", u"toggle", None))
#if QT_CONFIG(shortcut)
        self.navigationToggleButton.setShortcut(QCoreApplication.translate("CornerWidget", u"Backspace", None))
#endif // QT_CONFIG(shortcut)
        self.navigationForwardButton.setText(QCoreApplication.translate("CornerWidget", u">", None))
#if QT_CONFIG(shortcut)
        self.navigationForwardButton.setShortcut(QCoreApplication.translate("CornerWidget", u"Alt+Right", None))
#endif // QT_CONFIG(shortcut)
        self.menuButton.setText(QCoreApplication.translate("CornerWidget", u"Menu", None))
    # retranslateUi

