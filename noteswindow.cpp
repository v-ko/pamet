/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <QtGui>

#include "noteswindow.h"
#include "notefile.h"
#include "common.h"
#include "misliinstance.h"

class GLWidget;

NotesWindow::NotesWindow(MisliInstance *m_i)
{
    misl_i=m_i;
    gl_w = new GLWidget(m_i);

    //Shortcuts
    //--------E - show edit window ---------------
    shE = new QShortcut(QKeySequence("E"),this);
    connect(shE,SIGNAL( activated() ),misl_i->edit_w,SLOT( edit_note() ) );
    //--------Q - exit app ---------------
    shQ = new QShortcut(QKeySequence("Q"),this);
    connect(shQ,SIGNAL( activated() ),this,SLOT( close() ) ); //edit the first selected note
    //--------M - new note ---------------
    shM = new QShortcut(QKeySequence("M"),this);
    connect(shM,SIGNAL( activated() ),misl_i->edit_w,SLOT( new_note()) );
    //--------N - new notefile---------------
    shN = new QShortcut(QKeySequence("N"),this);
    connect(shN,SIGNAL( activated() ),misl_i->get_nf_name_w,SLOT( new_nf() ) );
    //--------L - make a new link---------------
    shL = new QShortcut(QKeySequence("L"),this);
    connect(shL,SIGNAL( activated() ),gl_w,SLOT( set_linking_on() ) );
    //--------Plus - next nf ---------------
    shPlus = new QShortcut(QKeySequence(Qt::Key_Plus),this);
    connect(shPlus,SIGNAL( activated() ),misl_i,SLOT( next_nf() ) );
    //--------Minus - previous nf ---------------
    shMinus = new QShortcut(QKeySequence(Qt::Key_Minus),this);
    connect(shMinus,SIGNAL( activated() ),misl_i,SLOT( previous_nf() ) );
    //--------Delete - delete all selected ---------------
    shDelete = new QShortcut(QKeySequence(Qt::Key_Delete),this);
    connect(shDelete,SIGNAL( activated() ),misl_i,SLOT( delete_selected() ) );
    //--------PageUp - zoom out ---------------
    shPageUp = new QShortcut(QKeySequence(Qt::Key_PageUp),this);
    connect(shPageUp,SIGNAL( activated() ),this,SLOT( zoom_out() ) );
    //--------PageUp - zoom in ---------------
    shPageDown = new QShortcut(QKeySequence(Qt::Key_PageDown),this);
    connect(shPageDown,SIGNAL( activated() ),this,SLOT( zoom_in() ) );

    //Setup actions for the menus

    //-------Clear settings action----------
    clearSettingsAct = new QAction("Clear settings and quit",this);
    //newAct->setShortcuts(QKeySequence::New);
    clearSettingsAct->setStatusTip(tr("Clears the settings file and exits the application"));
    connect(clearSettingsAct, SIGNAL(triggered()), this, SLOT(wipe_settings_out()));

    //-------Open the help window-----------
    helpAct = new QAction("Help",this);
    helpAct->setShortcuts(QKeySequence::HelpContents);
    helpAct->setStatusTip(tr("Display help"));
    connect(helpAct, SIGNAL(triggered()), this, SLOT(open_help()));

    //--------Undo-----------
    undoAct = new QAction("Undo",this);
    undoAct->setShortcuts(QKeySequence::Undo);
    undoAct->setStatusTip(tr("Undo action"));
    connect(undoAct, SIGNAL(triggered()), misl_i, SLOT( undo() ));

    //--------Copy-----------
    copyAct = new QAction("Copy",this);
    copyAct->setShortcuts(QKeySequence::Copy);
    copyAct->setStatusTip(tr("Copy action"));
    connect(copyAct, SIGNAL(triggered()), misl_i, SLOT( copy() ));

    //--------Cut-----------
    cutAct = new QAction("Cut",this);
    cutAct->setShortcuts(QKeySequence::Cut);
    cutAct->setStatusTip(tr("Cut action"));
    connect(cutAct, SIGNAL(triggered()), misl_i, SLOT( cut() ));

    //--------Paste-----------
    pasteAct = new QAction("Paste",this);
    pasteAct->setShortcuts(QKeySequence::Paste);
    pasteAct->setStatusTip(tr("Paste action"));
    connect(pasteAct, SIGNAL(triggered()), misl_i, SLOT( paste() ));

    //------Display this NF on startup---------
    setStartupNFAct = new QAction("Display this notefile on program start",this);
    //setStartupNFAct->setShortcuts(QKeySequence::Paste);
    setStartupNFAct->setStatusTip(tr("Sets the current notefile as the default at program startup"));
    connect(setStartupNFAct, SIGNAL(triggered()), misl_i, SLOT( set_curr_nf_as_default_on_startup() ));

    //--------Make this the starting position-----------
    makeCurrentViewpointDefaultAct = new QAction("Make this viewpoint default on startup",this);
    //makeCurrentViewpointDefaultAct->setShortcuts(QKeySequence::Paste);
    makeCurrentViewpointDefaultAct->setStatusTip(tr("Sets the current view position as the default for this notefile on program startup"));
    connect(makeCurrentViewpointDefaultAct, SIGNAL(triggered()), misl_i, SLOT( make_this_the_default_viewpoint() ));

    //Setup menus

    editMenu = menuBar()->addMenu(tr("&Edit"));
    editMenu->addAction(undoAct);
    editMenu->addAction(copyAct);
    editMenu->addAction(cutAct);
    editMenu->addAction(pasteAct);

    settingsMenu = menuBar()->addMenu(tr("&Settings"));
    settingsMenu->addAction(clearSettingsAct);
    settingsMenu->addAction(setStartupNFAct);
    settingsMenu->addAction(makeCurrentViewpointDefaultAct);

    helpMenu = menuBar()->addMenu(tr("&Help"));
    helpMenu->addAction(helpAct);

    //Layout setup
    setCentralWidget(gl_w);

    setWindowIcon(QIcon(":/img/icon.png"));
    setWindowTitle(tr("Misli"));
}

void NotesWindow::wipe_settings_out()
{
    misl_i->settings = new QSettings;
    misl_i->settings->clear();
    misl_i->settings->sync();

    exit(1);
}

void NotesWindow::zoom_out()
{
    eye.z+=misli_speed;
    gl_w->updateGL();
}
void NotesWindow::zoom_in()
{
    eye.z-=misli_speed;
    gl_w->updateGL();
}

void NotesWindow::open_help()
{

 misl_i->help_w->show();
 misl_i->help_w->raise();
 misl_i->help_w->activateWindow();

}
