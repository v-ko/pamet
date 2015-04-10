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

#ifndef MISLIDIR_H
#define MISLIDIR_H

#include <unistd.h>

#include <QDir>
#include <QTimer>

#include "petko10.h"
#include "petko10q.h"

#include "filesystemwatcher.h"
#include "notefile.h"
#include "common.h"

class MisliInstance;
class Canvas;

class MisliDir : public QObject

{
    Q_OBJECT

    Q_PROPERTY(QString notesDir READ notesDir WRITE setNotesDir NOTIFY notesDirChanged)

public:
    //Functions
    MisliDir(QString nts_dir, MisliInstance* msl_i_, bool using_gui_, bool debug_); //Can work without a MisliInstance
    ~MisliDir();

    int make_notes_file(QString);
    void set_current_note_file(QString name);
    void softDeleteAllNoteFiles();
    void deleteAllNoteFiles();

    NoteFile * nf_by_name(QString name);
    NoteFile * curr_nf(); //returns the current note file
    NoteFile * default_nf_on_startup();
    NoteFile * find_first_normal_nf();

    //Properties
    QString notesDir();

    //Variables
    MisliInstance * misli_i;
    QString notes_dir;
    std::vector<NoteFile*> note_file; //all the notefiles

    //----Children(for destruct)----
    FileSystemWatcher *fs_watch; //to watch the dir for changes
    QTimer * hanging_nf_check; //periodical check for unaccounted for note files

    //---Other---
    int mode;
    bool is_current,debug;
    int using_gui;

signals:
    //Property chabges
    void notesDirChanged(QString);

    //Other
    void current_nf_switched();
    void current_nf_updated();

    void noteFilesListChanged(); //FIXME

public slots:
    //Set properties
    void setNotesDir(QString newDirPath);

    //Other
    int load_notes_files();
    int reinit_notes_pointing_to_notefiles();

    void check_for_hanging_nfs();

    int next_nf();
    int previous_nf();
    int delete_nf(QString nfname);

    void set_curr_nf_as_default_on_startup();
    int delete_selected();

    void handle_changed_file(QString file);
};

#endif // MISLIDIR_H
