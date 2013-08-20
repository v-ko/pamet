/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef MISLIDESKTOPGUI_H
#define MISLIDESKTOPGUI_H

#include <QApplication>
#include <QTranslator>
#include <QSettings>
#include <QSplashScreen>
#include <QFutureWatcher>
#include <QThread>

#include "notefile.h"
#include "misliwindow.h"
#include "getdirdialogue.h"
#include "newnfdialogue.h"
#include "editnotedialogue.h"
#include "notedetailswindow.h"
#include "notessearch.h"

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
    NoteDetailsWindow *note_w;
    QSplashScreen *splash;
    NotesSearch *notes_search;

    QThread workerThread;
    QString language;
    bool first_program_start;

private:
    QSettings settings;
    QTranslator translator;

public slots:
    void start_GUI();
};

#endif // MISLIDESKTOPGUI_H
