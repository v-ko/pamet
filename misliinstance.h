/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef MISLIINSTANCE_H
#define MISLIINSTANCE_H

#include <QWidget>
#include <QString>
#include <unistd.h>

#include <QSettings>
#include <QDir>

#include "../../petko10.h"
#include "../../petko10q.h"

#include "noteswindow.h"
#include "getdirdialogue.h"
#include "getnfname.h"
#include "editnotewindow.h"
#include "helpwindow.h"

#include "notefile.h"
#include "common.h"

class GetDirDialogue;

class MisliInstance : public QWidget
{
    Q_OBJECT

public:
    //Functions
    MisliInstance(int md,QString nts_dir = 0); //0 = no visualisation ; 1 = normal
    int check_settings();
    int make_notes_file(const char*);
    void set_current_notes(int);
    NoteFile * nf_by_id(int);
    NoteFile * nf_by_name(const char*);
    NoteFile * curr_nf();
    NoteFile * clipboard_nf();
    NoteFile * default_nf_on_startup();
    void save_eye_coords_to_nf();

    int copy_selected_notes(NoteFile *source_nf,NoteFile *target_nf);


    //Window classes
    GetDirDialogue *dir_w;
    GetNFName *get_nf_name_w;
    NotesWindow *nt_w;
    GLWidget *gl_w;
    EditNoteWindow *edit_w;
    HelpWindow *help_w;

    //Additional classes
    QSettings *settings;

    //Variables
    QString notes_dir;
    NotesVector *curr_note;
    std::vector<NoteFile> note_file;
    //NoteFile *cut_nf; //nf for copy/cut/paste actions
    int current_note_file;
    int last_nf_id;
    bool notes_rdy;
    int mode;

signals:
    void no_notes_dir();
    void settings_ready();
    void notes_ready();
    //void curr_nf_changed();
public slots:
    int next_nf();
    int previous_nf();

    int undo();
    int copy();
    int cut();
    int paste();

    int init_notes_files();
    int reinit_redirect_notes();

    void settings_ready_publ();
    void set_notes_ready();
    void set_eye_coords(double x, double y, double z);
    void set_curr_nf_as_default_on_startup();
    void make_this_the_default_viewpoint();
    int delete_selected();
};

#endif // MISLIINSTANCE_H
