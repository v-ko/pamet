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
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QSizePolicy,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_BrowserWindow(object):
    def setupUi(self, BrowserWindow):
        if not BrowserWindow.objectName():
            BrowserWindow.setObjectName(u"BrowserWindow")
        BrowserWindow.resize(800, 600)
        self.actionCopy = QAction(BrowserWindow)
        self.actionCopy.setObjectName(u"actionCopy")
        self.actionPaste = QAction(BrowserWindow)
        self.actionPaste.setObjectName(u"actionPaste")
        self.actionCut = QAction(BrowserWindow)
        self.actionCut.setObjectName(u"actionCut")
        self.actionUndo = QAction(BrowserWindow)
        self.actionUndo.setObjectName(u"actionUndo")
        self.actionHelp = QAction(BrowserWindow)
        self.actionHelp.setObjectName(u"actionHelp")
        self.actionAdd_new = QAction(BrowserWindow)
        self.actionAdd_new.setObjectName(u"actionAdd_new")
        self.actionAdd_new.setCheckable(False)
        self.actionRemove_current = QAction(BrowserWindow)
        self.actionRemove_current.setObjectName(u"actionRemove_current")
        self.actionEdit_note = QAction(BrowserWindow)
        self.actionEdit_note.setObjectName(u"actionEdit_note")
        self.actionNew_note = QAction(BrowserWindow)
        self.actionNew_note.setObjectName(u"actionNew_note")
        self.actionNew_notefile = QAction(BrowserWindow)
        self.actionNew_notefile.setObjectName(u"actionNew_notefile")
        self.actionNew_notefile.setCheckable(False)
        self.actionNew_notefile.setChecked(False)
        self.actionMake_link = QAction(BrowserWindow)
        self.actionMake_link.setObjectName(u"actionMake_link")
        self.actionNext_notefile = QAction(BrowserWindow)
        self.actionNext_notefile.setObjectName(u"actionNext_notefile")
        self.actionPrevious_notefile = QAction(BrowserWindow)
        self.actionPrevious_notefile.setObjectName(u"actionPrevious_notefile")
        self.actionDelete_selected = QAction(BrowserWindow)
        self.actionDelete_selected.setObjectName(u"actionDelete_selected")
        self.actionZoom_in = QAction(BrowserWindow)
        self.actionZoom_in.setObjectName(u"actionZoom_in")
        self.actionZoom_out = QAction(BrowserWindow)
        self.actionZoom_out.setObjectName(u"actionZoom_out")
        self.actionMake_this_view_point_default_for_the_notefile = QAction(BrowserWindow)
        self.actionMake_this_view_point_default_for_the_notefile.setObjectName(u"actionMake_this_view_point_default_for_the_notefile")
        self.actionMake_this_notefile_appear_first_on_program_start = QAction(BrowserWindow)
        self.actionMake_this_notefile_appear_first_on_program_start.setObjectName(u"actionMake_this_notefile_appear_first_on_program_start")
        self.actionClose = QAction(BrowserWindow)
        self.actionClose.setObjectName(u"actionClose")
        self.actionBulgarian = QAction(BrowserWindow)
        self.actionBulgarian.setObjectName(u"actionBulgarian")
        self.actionEnglish = QAction(BrowserWindow)
        self.actionEnglish.setObjectName(u"actionEnglish")
        self.actionClear_settings_and_exit = QAction(BrowserWindow)
        self.actionClear_settings_and_exit.setObjectName(u"actionClear_settings_and_exit")
        self.actionRename_notefile = QAction(BrowserWindow)
        self.actionRename_notefile.setObjectName(u"actionRename_notefile")
        self.actionDelete_notefile = QAction(BrowserWindow)
        self.actionDelete_notefile.setObjectName(u"actionDelete_notefile")
        self.actionColor_blue = QAction(BrowserWindow)
        self.actionColor_blue.setObjectName(u"actionColor_blue")
        self.actionColor_green = QAction(BrowserWindow)
        self.actionColor_green.setObjectName(u"actionColor_green")
        self.actionColor_red = QAction(BrowserWindow)
        self.actionColor_red.setObjectName(u"actionColor_red")
        self.actionColor_black = QAction(BrowserWindow)
        self.actionColor_black.setObjectName(u"actionColor_black")
        self.actionMove_down = QAction(BrowserWindow)
        self.actionMove_down.setObjectName(u"actionMove_down")
        self.actionMove_up = QAction(BrowserWindow)
        self.actionMove_up.setObjectName(u"actionMove_up")
        self.actionMove_left = QAction(BrowserWindow)
        self.actionMove_left.setObjectName(u"actionMove_left")
        self.actionMove_right = QAction(BrowserWindow)
        self.actionMove_right.setObjectName(u"actionMove_right")
        self.actionSearch = QAction(BrowserWindow)
        self.actionSearch.setObjectName(u"actionSearch")
        self.actionSearch.setCheckable(True)
        self.actionSelect_all_notes = QAction(BrowserWindow)
        self.actionSelect_all_notes.setObjectName(u"actionSelect_all_notes")
        self.actionJump_to_nearest_note = QAction(BrowserWindow)
        self.actionJump_to_nearest_note.setObjectName(u"actionJump_to_nearest_note")
        self.actionDetails = QAction(BrowserWindow)
        self.actionDetails.setObjectName(u"actionDetails")
        self.actionAbout = QAction(BrowserWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.actionSelect_note_under_mouse = QAction(BrowserWindow)
        self.actionSelect_note_under_mouse.setObjectName(u"actionSelect_note_under_mouse")
        self.actionCreate_note_from_the_clipboard_text = QAction(BrowserWindow)
        self.actionCreate_note_from_the_clipboard_text.setObjectName(u"actionCreate_note_from_the_clipboard_text")
        self.actionTransparent_background = QAction(BrowserWindow)
        self.actionTransparent_background.setObjectName(u"actionTransparent_background")
        self.actionSet_this_height_as_default = QAction(BrowserWindow)
        self.actionSet_this_height_as_default.setObjectName(u"actionSet_this_height_as_default")
        self.actionCopy_donation_address = QAction(BrowserWindow)
        self.actionCopy_donation_address.setObjectName(u"actionCopy_donation_address")
        self.actionSelect_all_red_notes = QAction(BrowserWindow)
        self.actionSelect_all_red_notes.setObjectName(u"actionSelect_all_red_notes")
        self.actionRedo = QAction(BrowserWindow)
        self.actionRedo.setObjectName(u"actionRedo")
        self.actionCheck_for_updates = QAction(BrowserWindow)
        self.actionCheck_for_updates.setObjectName(u"actionCheck_for_updates")
        self.actionCheck_for_updates.setCheckable(True)
        self.actionCheck_for_updates.setChecked(False)
        self.actionDownload_it = QAction(BrowserWindow)
        self.actionDownload_it.setObjectName(u"actionDownload_it")
        self.actionGotoTab1 = QAction(BrowserWindow)
        self.actionGotoTab1.setObjectName(u"actionGotoTab1")
        self.actionGotoTab2 = QAction(BrowserWindow)
        self.actionGotoTab2.setObjectName(u"actionGotoTab2")
        self.actionSwitch_to_the_last_note_file = QAction(BrowserWindow)
        self.actionSwitch_to_the_last_note_file.setObjectName(u"actionSwitch_to_the_last_note_file")
        self.actionExport_all_as_web_notes = QAction(BrowserWindow)
        self.actionExport_all_as_web_notes.setObjectName(u"actionExport_all_as_web_notes")
        self.actionToggle_tags_view = QAction(BrowserWindow)
        self.actionToggle_tags_view.setObjectName(u"actionToggle_tags_view")
        self.actionToggle_tags_view.setCheckable(True)
        self.actionToggle_tag = QAction(BrowserWindow)
        self.actionToggle_tag.setObjectName(u"actionToggle_tag")
        self.actionUse_JSON_format = QAction(BrowserWindow)
        self.actionUse_JSON_format.setObjectName(u"actionUse_JSON_format")
        self.actionMigrate_to_JSON_format = QAction(BrowserWindow)
        self.actionMigrate_to_JSON_format.setObjectName(u"actionMigrate_to_JSON_format")
        self.centralwidget = QWidget(BrowserWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_2 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setObjectName(u"mainLayout")
        self.tabBarWidget = QTabWidget(self.centralwidget)
        self.tabBarWidget.setObjectName(u"tabBarWidget")
        self.tabBarWidget.setTabsClosable(True)
        self.tabBarWidget.setMovable(True)

        self.mainLayout.addWidget(self.tabBarWidget)


        self.horizontalLayout_2.addLayout(self.mainLayout)

        BrowserWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(BrowserWindow)
        self.actionClose.triggered.connect(self.actionToggle_tag.toggle)

        QMetaObject.connectSlotsByName(BrowserWindow)
    # setupUi

    def retranslateUi(self, BrowserWindow):
        BrowserWindow.setWindowTitle(QCoreApplication.translate("BrowserWindow", u"MainWindow", None))
        self.actionCopy.setText(QCoreApplication.translate("BrowserWindow", u"&Copy", None))
#if QT_CONFIG(tooltip)
        self.actionCopy.setToolTip(QCoreApplication.translate("BrowserWindow", u"Copies notes to the internal clipboard, and copies their text to the regular clipboard.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionCopy.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+C", None))
#endif // QT_CONFIG(shortcut)
        self.actionPaste.setText(QCoreApplication.translate("BrowserWindow", u"&Paste", None))
#if QT_CONFIG(tooltip)
        self.actionPaste.setToolTip(QCoreApplication.translate("BrowserWindow", u"Pastes the notes from the internal clipboard.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionPaste.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+V", None))
#endif // QT_CONFIG(shortcut)
        self.actionCut.setText(QCoreApplication.translate("BrowserWindow", u"Cut", None))
#if QT_CONFIG(tooltip)
        self.actionCut.setToolTip(QCoreApplication.translate("BrowserWindow", u"See the tooltip of \"Copy\"", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionCut.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+X", None))
#endif // QT_CONFIG(shortcut)
        self.actionUndo.setText(QCoreApplication.translate("BrowserWindow", u"&Undo", None))
#if QT_CONFIG(tooltip)
        self.actionUndo.setToolTip(QCoreApplication.translate("BrowserWindow", u"Reverts the last action. The max is 30 undo steps. (note there is no Redo for now)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionUndo.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+Z", None))
#endif // QT_CONFIG(shortcut)
        self.actionHelp.setText(QCoreApplication.translate("BrowserWindow", u"&Help", None))
#if QT_CONFIG(tooltip)
        self.actionHelp.setToolTip(QCoreApplication.translate("BrowserWindow", u"Shows the help notefile.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionHelp.setShortcut(QCoreApplication.translate("BrowserWindow", u"F1", None))
#endif // QT_CONFIG(shortcut)
        self.actionAdd_new.setText(QCoreApplication.translate("BrowserWindow", u"&Add another folder", None))
        self.actionRemove_current.setText(QCoreApplication.translate("BrowserWindow", u"&Remove current", None))
#if QT_CONFIG(tooltip)
        self.actionRemove_current.setToolTip(QCoreApplication.translate("BrowserWindow", u"Remove the current folder (does not delete the notefiles from the disk)", None))
#endif // QT_CONFIG(tooltip)
        self.actionEdit_note.setText(QCoreApplication.translate("BrowserWindow", u"&Edit note", None))
#if QT_CONFIG(shortcut)
        self.actionEdit_note.setShortcut(QCoreApplication.translate("BrowserWindow", u"E", None))
#endif // QT_CONFIG(shortcut)
        self.actionNew_note.setText(QCoreApplication.translate("BrowserWindow", u"&New note", None))
#if QT_CONFIG(tooltip)
        self.actionNew_note.setToolTip(QCoreApplication.translate("BrowserWindow", u"Create a new note", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionNew_note.setShortcut(QCoreApplication.translate("BrowserWindow", u"N", None))
#endif // QT_CONFIG(shortcut)
        self.actionNew_notefile.setText(QCoreApplication.translate("BrowserWindow", u"&New notefile", None))
#if QT_CONFIG(tooltip)
        self.actionNew_notefile.setToolTip(QCoreApplication.translate("BrowserWindow", u"Create a new notefile on the disk and open it to add notes.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionNew_notefile.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
        self.actionMake_link.setText(QCoreApplication.translate("BrowserWindow", u"&Make link", None))
#if QT_CONFIG(tooltip)
        self.actionMake_link.setToolTip(QCoreApplication.translate("BrowserWindow", u"Link notes with arrows to visualize their connections.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionMake_link.setShortcut(QCoreApplication.translate("BrowserWindow", u"L", None))
#endif // QT_CONFIG(shortcut)
        self.actionNext_notefile.setText(QCoreApplication.translate("BrowserWindow", u"Next notefile", None))
#if QT_CONFIG(tooltip)
        self.actionNext_notefile.setToolTip(QCoreApplication.translate("BrowserWindow", u"Switch to the next notefile in the alphabetical order.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionNext_notefile.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+PgUp", None))
#endif // QT_CONFIG(shortcut)
        self.actionPrevious_notefile.setText(QCoreApplication.translate("BrowserWindow", u"Previous notefile", None))
#if QT_CONFIG(tooltip)
        self.actionPrevious_notefile.setToolTip(QCoreApplication.translate("BrowserWindow", u"Switch to the previous notefile in thealphabetical order.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionPrevious_notefile.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+PgDown", None))
#endif // QT_CONFIG(shortcut)
        self.actionDelete_selected.setText(QCoreApplication.translate("BrowserWindow", u"&Delete selected", None))
#if QT_CONFIG(tooltip)
        self.actionDelete_selected.setToolTip(QCoreApplication.translate("BrowserWindow", u"Delete selected notes.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionDelete_selected.setShortcut(QCoreApplication.translate("BrowserWindow", u"Del", None))
#endif // QT_CONFIG(shortcut)
        self.actionZoom_in.setText(QCoreApplication.translate("BrowserWindow", u"&Zoom in", None))
#if QT_CONFIG(tooltip)
        self.actionZoom_in.setToolTip(QCoreApplication.translate("BrowserWindow", u"Change the height of the viewpoint over the canvas.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionZoom_in.setShortcut(QCoreApplication.translate("BrowserWindow", u"PgDown", None))
#endif // QT_CONFIG(shortcut)
        self.actionZoom_out.setText(QCoreApplication.translate("BrowserWindow", u"Zoom &out", None))
#if QT_CONFIG(tooltip)
        self.actionZoom_out.setToolTip(QCoreApplication.translate("BrowserWindow", u"Change the height of the viewpoint over the canvas.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionZoom_out.setShortcut(QCoreApplication.translate("BrowserWindow", u"PgUp", None))
#endif // QT_CONFIG(shortcut)
        self.actionMake_this_view_point_default_for_the_notefile.setText(QCoreApplication.translate("BrowserWindow", u"&Make this view point default for the notefile", None))
#if QT_CONFIG(tooltip)
        self.actionMake_this_view_point_default_for_the_notefile.setToolTip(QCoreApplication.translate("BrowserWindow", u"Fix the current viewpoint (height excluded) in the notefile as default on program start.", None))
#endif // QT_CONFIG(tooltip)
        self.actionMake_this_notefile_appear_first_on_program_start.setText(QCoreApplication.translate("BrowserWindow", u"Make this notefile appear first &on program start", None))
#if QT_CONFIG(tooltip)
        self.actionMake_this_notefile_appear_first_on_program_start.setToolTip(QCoreApplication.translate("BrowserWindow", u"Marks the notefile as default on program start for its folder.", None))
#endif // QT_CONFIG(tooltip)
        self.actionClose.setText(QCoreApplication.translate("BrowserWindow", u"Close", None))
#if QT_CONFIG(shortcut)
        self.actionClose.setShortcut(QCoreApplication.translate("BrowserWindow", u"Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionBulgarian.setText(QCoreApplication.translate("BrowserWindow", u"\u0411\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438", None))
        self.actionEnglish.setText(QCoreApplication.translate("BrowserWindow", u"&English", None))
#if QT_CONFIG(tooltip)
        self.actionEnglish.setToolTip(QCoreApplication.translate("BrowserWindow", u"Change the language to english.", None))
#endif // QT_CONFIG(tooltip)
        self.actionClear_settings_and_exit.setText(QCoreApplication.translate("BrowserWindow", u"&Clear settings and exit", None))
#if QT_CONFIG(tooltip)
        self.actionClear_settings_and_exit.setToolTip(QCoreApplication.translate("BrowserWindow", u"Clear program settings and kill this instance.", None))
#endif // QT_CONFIG(tooltip)
        self.actionRename_notefile.setText(QCoreApplication.translate("BrowserWindow", u"&Rename notefile", None))
#if QT_CONFIG(tooltip)
        self.actionRename_notefile.setToolTip(QCoreApplication.translate("BrowserWindow", u"Also changes all of the notes that link to it to the new name.", None))
#endif // QT_CONFIG(tooltip)
        self.actionDelete_notefile.setText(QCoreApplication.translate("BrowserWindow", u"&Delete notefile", None))
#if QT_CONFIG(tooltip)
        self.actionDelete_notefile.setToolTip(QCoreApplication.translate("BrowserWindow", u"Delete the notefile permanetly (on the disk too).", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionDelete_notefile.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+Del", None))
#endif // QT_CONFIG(shortcut)
        self.actionColor_blue.setText(QCoreApplication.translate("BrowserWindow", u"&Color blue", None))
#if QT_CONFIG(shortcut)
        self.actionColor_blue.setShortcut(QCoreApplication.translate("BrowserWindow", u"1", None))
#endif // QT_CONFIG(shortcut)
        self.actionColor_green.setText(QCoreApplication.translate("BrowserWindow", u"Color &green", None))
#if QT_CONFIG(shortcut)
        self.actionColor_green.setShortcut(QCoreApplication.translate("BrowserWindow", u"2", None))
#endif // QT_CONFIG(shortcut)
        self.actionColor_red.setText(QCoreApplication.translate("BrowserWindow", u"Color &red", None))
#if QT_CONFIG(shortcut)
        self.actionColor_red.setShortcut(QCoreApplication.translate("BrowserWindow", u"3", None))
#endif // QT_CONFIG(shortcut)
        self.actionColor_black.setText(QCoreApplication.translate("BrowserWindow", u"Color &black", None))
#if QT_CONFIG(shortcut)
        self.actionColor_black.setShortcut(QCoreApplication.translate("BrowserWindow", u"4", None))
#endif // QT_CONFIG(shortcut)
        self.actionMove_down.setText(QCoreApplication.translate("BrowserWindow", u"&Move down", None))
#if QT_CONFIG(shortcut)
        self.actionMove_down.setShortcut(QCoreApplication.translate("BrowserWindow", u"Down", None))
#endif // QT_CONFIG(shortcut)
        self.actionMove_up.setText(QCoreApplication.translate("BrowserWindow", u"Move &up", None))
#if QT_CONFIG(shortcut)
        self.actionMove_up.setShortcut(QCoreApplication.translate("BrowserWindow", u"Up", None))
#endif // QT_CONFIG(shortcut)
        self.actionMove_left.setText(QCoreApplication.translate("BrowserWindow", u"Move &left", None))
#if QT_CONFIG(shortcut)
        self.actionMove_left.setShortcut(QCoreApplication.translate("BrowserWindow", u"Left", None))
#endif // QT_CONFIG(shortcut)
        self.actionMove_right.setText(QCoreApplication.translate("BrowserWindow", u"Move &right", None))
#if QT_CONFIG(shortcut)
        self.actionMove_right.setShortcut(QCoreApplication.translate("BrowserWindow", u"Right", None))
#endif // QT_CONFIG(shortcut)
        self.actionSearch.setText(QCoreApplication.translate("BrowserWindow", u"&Search ", None))
#if QT_CONFIG(tooltip)
        self.actionSearch.setToolTip(QCoreApplication.translate("BrowserWindow", u"Search in all notes. Click in the results shown under the search field to go to the note.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionSearch.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+F", None))
#endif // QT_CONFIG(shortcut)
        self.actionSelect_all_notes.setText(QCoreApplication.translate("BrowserWindow", u"S&elect all notes", None))
#if QT_CONFIG(shortcut)
        self.actionSelect_all_notes.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+A", None))
#endif // QT_CONFIG(shortcut)
        self.actionJump_to_nearest_note.setText(QCoreApplication.translate("BrowserWindow", u"&Jump to nearest note", None))
#if QT_CONFIG(shortcut)
        self.actionJump_to_nearest_note.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+J", None))
#endif // QT_CONFIG(shortcut)
        self.actionDetails.setText(QCoreApplication.translate("BrowserWindow", u"Details", None))
#if QT_CONFIG(shortcut)
        self.actionDetails.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+D", None))
#endif // QT_CONFIG(shortcut)
        self.actionAbout.setText(QCoreApplication.translate("BrowserWindow", u"&About", None))
        self.actionSelect_note_under_mouse.setText(QCoreApplication.translate("BrowserWindow", u"Select note under mouse", None))
#if QT_CONFIG(shortcut)
        self.actionSelect_note_under_mouse.setShortcut(QCoreApplication.translate("BrowserWindow", u"Return", None))
#endif // QT_CONFIG(shortcut)
        self.actionCreate_note_from_the_clipboard_text.setText(QCoreApplication.translate("BrowserWindow", u"Create &note from the clipboard text", None))
#if QT_CONFIG(tooltip)
        self.actionCreate_note_from_the_clipboard_text.setToolTip(QCoreApplication.translate("BrowserWindow", u"Create note from the text in the regular clipboard.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionCreate_note_from_the_clipboard_text.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+Shift+V", None))
#endif // QT_CONFIG(shortcut)
        self.actionTransparent_background.setText(QCoreApplication.translate("BrowserWindow", u"&Transparent background", None))
#if QT_CONFIG(tooltip)
        self.actionTransparent_background.setToolTip(QCoreApplication.translate("BrowserWindow", u"Changes only the background color of the note to be transparent.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionTransparent_background.setShortcut(QCoreApplication.translate("BrowserWindow", u"5", None))
#endif // QT_CONFIG(shortcut)
        self.actionSet_this_height_as_default.setText(QCoreApplication.translate("BrowserWindow", u"&Set this height as default", None))
#if QT_CONFIG(tooltip)
        self.actionSet_this_height_as_default.setToolTip(QCoreApplication.translate("BrowserWindow", u"Set the current height as default for all files on startup.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(statustip)
        self.actionSet_this_height_as_default.setStatusTip(QCoreApplication.translate("BrowserWindow", u"Set the current height as default for all files on startup.", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        self.actionSet_this_height_as_default.setWhatsThis(QCoreApplication.translate("BrowserWindow", u"Set the current height as default for all files on startup.", None))
#endif // QT_CONFIG(whatsthis)
        self.actionCopy_donation_address.setText(QCoreApplication.translate("BrowserWindow", u"&Copy donation address", None))
        self.actionSelect_all_red_notes.setText(QCoreApplication.translate("BrowserWindow", u"Se&lect all red notes", None))
#if QT_CONFIG(shortcut)
        self.actionSelect_all_red_notes.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+R", None))
#endif // QT_CONFIG(shortcut)
        self.actionRedo.setText(QCoreApplication.translate("BrowserWindow", u"&Redo", None))
#if QT_CONFIG(shortcut)
        self.actionRedo.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+Shift+Z", None))
#endif // QT_CONFIG(shortcut)
        self.actionCheck_for_updates.setText(QCoreApplication.translate("BrowserWindow", u"Check for updates", None))
        self.actionDownload_it.setText(QCoreApplication.translate("BrowserWindow", u"Download it", None))
        self.actionGotoTab1.setText(QCoreApplication.translate("BrowserWindow", u"gotoTab1", None))
#if QT_CONFIG(shortcut)
        self.actionGotoTab1.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+1", None))
#endif // QT_CONFIG(shortcut)
        self.actionGotoTab2.setText(QCoreApplication.translate("BrowserWindow", u"gotoTab2", None))
#if QT_CONFIG(shortcut)
        self.actionGotoTab2.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+2", None))
#endif // QT_CONFIG(shortcut)
        self.actionSwitch_to_the_last_note_file.setText(QCoreApplication.translate("BrowserWindow", u"S&witch to the last note file", None))
#if QT_CONFIG(shortcut)
        self.actionSwitch_to_the_last_note_file.setShortcut(QCoreApplication.translate("BrowserWindow", u"Backspace", None))
#endif // QT_CONFIG(shortcut)
        self.actionExport_all_as_web_notes.setText(QCoreApplication.translate("BrowserWindow", u"&Export all as web notes", None))
        self.actionToggle_tags_view.setText(QCoreApplication.translate("BrowserWindow", u"Toggle tags view", None))
#if QT_CONFIG(shortcut)
        self.actionToggle_tags_view.setShortcut(QCoreApplication.translate("BrowserWindow", u"Ctrl+T", None))
#endif // QT_CONFIG(shortcut)
        self.actionToggle_tag.setText(QCoreApplication.translate("BrowserWindow", u"Toggle tag", None))
#if QT_CONFIG(shortcut)
        self.actionToggle_tag.setShortcut(QCoreApplication.translate("BrowserWindow", u"T", None))
#endif // QT_CONFIG(shortcut)
        self.actionUse_JSON_format.setText(QCoreApplication.translate("BrowserWindow", u"Use JSON format", None))
        self.actionMigrate_to_JSON_format.setText(QCoreApplication.translate("BrowserWindow", u"Migrate to JSON format", None))
    # retranslateUi

