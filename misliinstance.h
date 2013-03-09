/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef MISLIINSTANCE_H
#define MISLIINSTANCE_H

#include <unistd.h>

#include <QWidget>
#include <QString>
#include <QDir>
#include <QTimer>

#include "../../petko10.h"
#include "../../petko10q.h"

#include "filesystemwatcher.h"
#include "glwidget.h"
#include "notefile.h"
#include "common.h"

class MisliWindow;

class MisliInstance : public QObject

{
    Q_OBJECT

public:
    //Functions
    MisliInstance(QString nts_dir,MisliWindow* msl_w_); //0 = no visualisation ; 1 = normal
    int make_notes_file(QString);
    void set_current_notes(int);
    NoteFile * nf_by_id(int);
    NoteFile * nf_by_name(QString name);
    NoteFile * curr_nf();
    NoteFile * clipboard_nf();
    NoteFile * default_nf_on_startup();
    void save_eye_coords_to_nf();
    NoteFile * find_first_normal_nf();
    int copy_selected_notes(NoteFile *source_nf,NoteFile *target_nf);

    //Window classes
    MisliWindow * msl_w;
    GLWidget * gl_w;

    //Variables
    FileSystemWatcher *fs_watch;
    QTimer * hanging_nf_check;
    int changes_accounted_for;
    int error,using_external_classes;
    QString notes_dir;
    NotesVector *curr_note;
    std::vector<NoteFile> note_file;
    int current_note_file;
    int last_nf_id;
    //bool notes_rdy;
    int mode;
    int nf_before_help;


public slots:
    void check_for_hanging_nfs();

    void emit_current_nf_switched();
    void emit_current_nf_updated();

    int next_nf();
    int previous_nf();
    int delete_nf(int id);

    int undo();

    int init_notes_files();
    int reinit_redirect_notes();

    void set_curr_nf_as_default_on_startup();
    int delete_selected();

    void file_changed(QString file);
};

#endif // MISLIINSTANCE_H
