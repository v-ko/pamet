/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef MISLIDIR_H
#define MISLIDIR_H

#include <unistd.h>

#include <QDir>
#include <QTimer>
#include <QClipboard>

#include "../../petko10.h"
#include "../../petko10q.h"

#include "filesystemwatcher.h"
#include "notefile.h"
#include "common.h"

class MisliInstance;
class Canvas;

class MisliDir : public QObject

{
    Q_OBJECT

public:
    //Functions
    MisliDir(QString nts_dir, MisliInstance* msl_i_, bool using_gui_); //Can work without a MisliInstance
    ~MisliDir();

    int make_notes_file(QString);
    void set_current_note_file(QString name);

    NoteFile * nf_by_name(QString name);
    NoteFile * curr_nf(); //returns the current note file
    NoteFile * default_nf_on_startup();
    NoteFile * find_first_normal_nf();

    //Variables
    MisliInstance * misli_i;
    QString notes_dir;
    std::vector<NoteFile*> note_file; //all the notefiles

    //----Children(for destruct)----
    FileSystemWatcher *fs_watch; //to watch the dir for changes
    QTimer * hanging_nf_check; //periodical check for unaccounted for note files

    //---Other---
    int mode;
    bool is_current;
    bool is_virtual;
    int using_gui;

signals:
    void current_nf_switched();
    void current_nf_updated();

public slots:
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
