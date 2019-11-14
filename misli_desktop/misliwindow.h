/*  This file is part of Misli.

    Misli is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Misli is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
*/

#ifndef MISLIWINDOW_H
#define MISLIWINDOW_H

#include <QMainWindow>
#include <QSettings>
#include <QAction>
#include <QGesture>
#include <QClipboard>
#include <QNetworkAccessManager>

#include "ui_misliwindow.h"
#include "editnotedialogue.h"
#include "../library_obsolete.h"
#include "../notefile.h"
#include "../notessearch.h"
#include "timelinewidget.h"


class CanvasWidget;
class MisliDesktopGui;
class Library;

namespace Ui {
class MisliWindow;
}

class MisliWindow : public QMainWindow
{
    Q_OBJECT
    
public:
    MisliWindow(MisliDesktopGui *misli_dg_);
    ~MisliWindow();

    bool timelineTabIsActive();

    Library *misliLibrary();
    CanvasWidget *currentCanvasWidget();

    //GUI
    Ui::MisliWindow *ui;
    EditNoteDialogue *edit_w;
    NotesSearch *notes_search;
    QTabWidget tabWidget;
    TimelineWidget timelineWidget;
    QMenu updateMenu;

    //Variables
    QSettings settings;
    NoteFile *clipboardNoteFile,*helpNoteFile;
    QNetworkAccessManager network;
    bool updateCheckDone;

    MisliDesktopGui * misliDesktopGUI;

    QString language;
    NoteFile *nfBeforeHelp;

public slots:

    //Other
    void newNoteFromClipboard();
    void newNoteFile();
    void renameNoteFile();
    void deleteNoteFileFromFS();

    void nextNoteFile();
    void previousNoteFile();

    void toggleHelp();
    void makeViewpointDefault();
    void makeNoteFileDefault();
    void addNewFolder();
    void openNoteFileInNewTab(NoteFile *nf);
//    void removeCurrentFolder();

    void updateTitle();

    void copySelectedNotesToClipboard();
    void colorSelectedNotes(double txtR,double txtG,double txtB,double txtA,double backgroundR,double backgroundG,double backgroundB,double backgroundA);
    void colorTransparentBackground();

    void zoomOut();
    void zoomIn();

    void updateNoteFilesListMenu();
//    void updateDirListMenu();

    void handleNoteFilesChange();

    void handleFoldersMenuClick(QAction *action);
    void handleNoteFilesMenuClick(QAction *action);

    //Functions
    void closeEvent(QCloseEvent*);
    bool event(QEvent *event);
    void keyPressEvent(QKeyEvent *event);
    void keyReleaseEvent(QKeyEvent *event);
    bool gestureEvent(QGestureEvent *event);
    void pinchTriggered(QPinchGesture *gesture);

    void startUpdateCheck();
    void handleVersionInfoReply(QNetworkReply *reply);
private slots:
    void on_tabWidget_currentChanged(int index);
    void on_tabWidget_tabBarClicked(int index);
};

#endif // MISLIWINDOW_H
