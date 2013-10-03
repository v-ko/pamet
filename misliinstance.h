/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef MISLIINSTANCE_H
#define MISLIINSTANCE_H

#include <QMainWindow>
#include <QSettings>
#include <QtDebug>

#include "mislidir.h"

class MisliDesktopGui;
class MisliWindow;

class MisliInstance : public QObject
{
    Q_OBJECT

public:
    //Functions
    MisliInstance(MisliDesktopGui *misli_dg_);
    ~MisliInstance();

    int load_settings();
    void add_dir(QString path);
    bool notes_rdy(); //true if there's a notes dir present (if it was empty - a default note file was created
    MisliDir * curr_misli_dir(); //returns the current directory

    int load_results_in_search_nf();

    //Variables
    std::vector<MisliDir*> misli_dir; //contains all the directories
    MisliDir *search_notes_dir;
    NoteFile *search_nf;
    QSettings *settings;

    MisliDesktopGui *misli_dg;

    bool using_gui;

signals:
    void notes_dir_changed();
    void notes_dir_added(QString path);
    void load_all_dirs_finished();
public slots:
    void set_current_misli_dir(QString path);
    int load_all_dirs();
    void move_back_to_main_thread();

};

#endif // MISLIINSTANCE_H
