/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef NOTESWINDOW_H
#define NOTESWINDOW_H

#include <QMainWindow>
#include <QShortcut>
#include <QMenu>
#include <QAction>
#include "glwidget.h"

class MisliInstance;

class NotesWindow : public QMainWindow
{
    Q_OBJECT

public:
    NotesWindow(MisliInstance *m_i);
    GLWidget *gl_w;
    MisliInstance *misl_i;

public slots:
    void wipe_settings_out();
    void zoom_out();
    void zoom_in();
    void open_help();
private:
    QMenu *editMenu,*settingsMenu,*helpMenu;
    QAction *clearSettingsAct,*helpAct,*undoAct,*copyAct,*cutAct,*pasteAct,*setStartupNFAct,*makeCurrentViewpointDefaultAct;
    QShortcut *shE,*shQ,*shM,*shN,*shL,*shPlus,*shMinus,*shDelete,*shPageUp,*shPageDown,*shF1;

};

#endif // NOTESWINDOW_H

