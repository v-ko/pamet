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

#include "editnotedialogue.h"
#include "../misliinstance.h"
#include "../notefile.h"
#include "../notessearch.h"

class Canvas;
class MisliDesktopGui;
class MisliDir;

namespace Ui {
class MisliWindow;
}

class MisliWindow : public QMainWindow
{
    Q_OBJECT

    Q_PROPERTY(MisliDir* currentDir READ currentDir WRITE setCurrentDir NOTIFY currentDirChanged)
    
public:
    //Functions
    MisliWindow(MisliDesktopGui * misli_dg_);
    ~MisliWindow();

    void export_settings();
    MisliInstance *misliInstance();

    //Properties
    MisliDir* currentDir();

    //Windows
    Ui::MisliWindow *ui;
    Canvas *canvas;
    EditNoteDialogue *edit_w;
    NotesSearch *notes_search;

    //Variables
    QSettings settings;
    NoteFile *clipboardNoteFile,*helpNoteFile;
    QMetaObject::Connection nfChangedConnecton;

    MisliDesktopGui * misli_dg;

    QString language;
    NoteFile *nfBeforeHelp;
    
signals:
    void currentDirChanged(MisliDir*);

public slots:
    //Properties
    void setCurrentDir(MisliDir*newDir);

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
    void removeCurrentFolder();
    void clearSettingsAndExit();

    void updateTitle();

    void copySelectedNotesToClipboard();
    void colorSelectedNotes(float txtR,float txtG,float txtB,float txtA,float backgroundR,float backgroundG,float backgroundB,float backgroundA);
    void colorTransparentBackground();

    void zoomOut();
    void zoomIn();

    void updateNoteFilesListMenu();
    void updateDirListMenu();

    void handleNoteFilesChange();

    void handleFoldersMenuClick(QAction *action);
    void handleNoteFilesMenuClick(QAction *action);

private:
    //Functions
    bool event(QEvent *event);
    bool gestureEvent(QGestureEvent *event);
    void pinchTriggered(QPinchGesture *gesture);

    //void closeEvent(QCloseEvent *);

    //Propertie variables
    MisliDir* currentDir_m;
};

#endif // MISLIWINDOW_H
