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

#ifndef MISLIDESKTOPGUI_H
#define MISLIDESKTOPGUI_H

#include <QApplication>
#include <QTranslator>
#include <QSettings>
#include <QSplashScreen>
#include <QFutureWatcher>
#include <QThread>

#include "../notefile.h"
#include "misliwindow.h"
#include "getdirdialogue.h"
#include "newnfdialogue.h"
#include "editnotedialogue.h"
#include "notedetailswindow.h"
#include "../notessearch.h"

class MisliDesktopGui : public QApplication
{
    Q_OBJECT

public:
    //Functions
    MisliDesktopGui(int argc, char *argv[]);
    ~MisliDesktopGui();

    //Variables
    //---Children(for destruct)
    MisliInstance *misli_i;
    MisliWindow *misli_w;
    GetDirDialogue *dir_w;
    NewNFDialogue *newnf_w;
    EditNoteDialogue *edit_w;
    NoteDetailsWindow *note_details_w;
    QSplashScreen *splash;
    NotesSearch *notes_search;

    QSettings *settings;
    QTranslator translator;
    QMessageBox msg; //general purpose

    QThread workerThread;
    QString language;
    bool first_program_start;

public slots:
    void show_warning_message(QString message);
};

#endif // MISLIDESKTOPGUI_H
