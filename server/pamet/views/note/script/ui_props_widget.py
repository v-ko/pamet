# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'props_widget.ui'
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
    QVBoxLayout, QWidget)

class Ui_ScriptNotePropsWidget(object):
    def setupUi(self, ScriptNotePropsWidget):
        if not ScriptNotePropsWidget.objectName():
            ScriptNotePropsWidget.setObjectName(u"ScriptNotePropsWidget")
        ScriptNotePropsWidget.resize(777, 526)
        ScriptNotePropsWidget.setMinimumSize(QSize(640, 0))
        self.verticalLayout = QVBoxLayout(ScriptNotePropsWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.createScriptWidget = QWidget(ScriptNotePropsWidget)
        self.createScriptWidget.setObjectName(u"createScriptWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.createScriptWidget.sizePolicy().hasHeightForWidth())
        self.createScriptWidget.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QVBoxLayout(self.createScriptWidget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(-1, 0, -1, -1)
        self.label_5 = QLabel(self.createScriptWidget)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_7.addWidget(self.label_5)

        self.setDefaultScriptsFolder = QPushButton(self.createScriptWidget)
        self.setDefaultScriptsFolder.setObjectName(u"setDefaultScriptsFolder")

        self.horizontalLayout_7.addWidget(self.setDefaultScriptsFolder)

        self.configureTemplatesButton = QPushButton(self.createScriptWidget)
        self.configureTemplatesButton.setObjectName(u"configureTemplatesButton")

        self.horizontalLayout_7.addWidget(self.configureTemplatesButton)


        self.verticalLayout_3.addLayout(self.horizontalLayout_7)


        self.verticalLayout.addWidget(self.createScriptWidget)

        self.scriptPropertiesWidget = QWidget(ScriptNotePropsWidget)
        self.scriptPropertiesWidget.setObjectName(u"scriptPropertiesWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.scriptPropertiesWidget.sizePolicy().hasHeightForWidth())
        self.scriptPropertiesWidget.setSizePolicy(sizePolicy1)
        self.verticalLayout_2 = QVBoxLayout(self.scriptPropertiesWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.runInTerminalCheckbox = QCheckBox(self.scriptPropertiesWidget)
        self.runInTerminalCheckbox.setObjectName(u"runInTerminalCheckbox")
        self.runInTerminalCheckbox.setChecked(True)

        self.horizontalLayout.addWidget(self.runInTerminalCheckbox)

        self.runPushButton = QPushButton(self.scriptPropertiesWidget)
        self.runPushButton.setObjectName(u"runPushButton")

        self.horizontalLayout.addWidget(self.runPushButton)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.line = QFrame(self.scriptPropertiesWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_2.addWidget(self.line)

        self.openInEditorPushButton = QPushButton(self.scriptPropertiesWidget)
        self.openInEditorPushButton.setObjectName(u"openInEditorPushButton")

        self.verticalLayout_2.addWidget(self.openInEditorPushButton)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(self.scriptPropertiesWidget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.scriptPathLineEdit = QLineEdit(self.scriptPropertiesWidget)
        self.scriptPathLineEdit.setObjectName(u"scriptPathLineEdit")

        self.horizontalLayout_2.addWidget(self.scriptPathLineEdit)

        self.pathErrorLabel = QLabel(self.scriptPropertiesWidget)
        self.pathErrorLabel.setObjectName(u"pathErrorLabel")

        self.horizontalLayout_2.addWidget(self.pathErrorLabel)

        self.chooseFilePushButton = QPushButton(self.scriptPropertiesWidget)
        self.chooseFilePushButton.setObjectName(u"chooseFilePushButton")

        self.horizontalLayout_2.addWidget(self.chooseFilePushButton)

        self.deletePushButton = QPushButton(self.scriptPropertiesWidget)
        self.deletePushButton.setObjectName(u"deletePushButton")

        self.horizontalLayout_2.addWidget(self.deletePushButton)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label = QLabel(self.scriptPropertiesWidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_3.addWidget(self.label)

        self.scriptNameLineEdit = QLineEdit(self.scriptPropertiesWidget)
        self.scriptNameLineEdit.setObjectName(u"scriptNameLineEdit")

        self.horizontalLayout_3.addWidget(self.scriptNameLineEdit)

        self.renamePushButton = QPushButton(self.scriptPropertiesWidget)
        self.renamePushButton.setObjectName(u"renamePushButton")

        self.horizontalLayout_3.addWidget(self.renamePushButton)

        self.openContainingFolderPushButton = QPushButton(self.scriptPropertiesWidget)
        self.openContainingFolderPushButton.setObjectName(u"openContainingFolderPushButton")

        self.horizontalLayout_3.addWidget(self.openContainingFolderPushButton)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_3 = QLabel(self.scriptPropertiesWidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_4.addWidget(self.label_3)

        self.argumentsLineEdit = QLineEdit(self.scriptPropertiesWidget)
        self.argumentsLineEdit.setObjectName(u"argumentsLineEdit")

        self.horizontalLayout_4.addWidget(self.argumentsLineEdit)


        self.verticalLayout_2.addLayout(self.horizontalLayout_4)


        self.verticalLayout.addWidget(self.scriptPropertiesWidget)

        self.noteTextVerticalLayout = QVBoxLayout()
        self.noteTextVerticalLayout.setObjectName(u"noteTextVerticalLayout")
        self.noteTextVerticalLayout.setContentsMargins(-1, 0, -1, -1)
        self.label_4 = QLabel(ScriptNotePropsWidget)
        self.label_4.setObjectName(u"label_4")

        self.noteTextVerticalLayout.addWidget(self.label_4)


        self.verticalLayout.addLayout(self.noteTextVerticalLayout)


        self.retranslateUi(ScriptNotePropsWidget)

        QMetaObject.connectSlotsByName(ScriptNotePropsWidget)
    # setupUi

    def retranslateUi(self, ScriptNotePropsWidget):
        ScriptNotePropsWidget.setWindowTitle(QCoreApplication.translate("ScriptNotePropsWidget", u"ScriptNotePropsWidget", None))
        self.label_5.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Create new:", None))
        self.setDefaultScriptsFolder.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Set default folder", None))
        self.configureTemplatesButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Configure templates", None))
        self.runInTerminalCheckbox.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Run in terminal", None))
        self.runPushButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Run", None))
        self.openInEditorPushButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Open in editor", None))
        self.label_2.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Path/Command", None))
        self.pathErrorLabel.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Path error label", None))
        self.chooseFilePushButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Choose file", None))
        self.deletePushButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Delete", None))
        self.label.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Name", None))
        self.scriptNameLineEdit.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"banana-potato-generated-name.py", None))
        self.renamePushButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Rename", None))
        self.openContainingFolderPushButton.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Open containing folder", None))
        self.label_3.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Arguments", None))
        self.label_4.setText(QCoreApplication.translate("ScriptNotePropsWidget", u"Note text:", None))
    # retranslateUi

