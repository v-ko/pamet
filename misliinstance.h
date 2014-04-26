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
    bool initial_load_complete;

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
