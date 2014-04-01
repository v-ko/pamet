/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef MISLIWINDOW_H
#define MISLIWINDOW_H

#include <QMainWindow>
#include <QSettings>
#include <QAction>
#include <QGesture>
#include <QClipboard>

#include "../emitmynameaction.h"
#include "../misliinstance.h"
#include "../notefile.h"

class NewNFDialogue;
class EditNoteDialogue;
class GetDirDialogue;
class Canvas;
class MisliDesktopGui;
//class MisliInstance;
class MisliDir;

namespace Ui {
class MisliWindow;
}

class MisliWindow : public QMainWindow
{
    Q_OBJECT
    
public:
    //Functions
    MisliWindow(MisliDesktopGui * misli_dg_);
    ~MisliWindow();

    void export_settings();
    int copy_selected_notes(NoteFile *source_nf,NoteFile *target_nf);
    QAction *get_action_for_name(QString name);
    MisliInstance *misli_i();

    //Windows
    Canvas *canvas;

    //Variables
    //---Child objects(to delete later)---
    //QSettings *settings;
    MisliDir * clipboard_dir;
    NoteFile * clipboard_nf;

    MisliDesktopGui * misli_dg;

    QString language;
    QString nf_before_help;


    bool past_initial_load;
    bool doing_cut_paste; //suspends undo image collection , because a cut/paste is one action
    bool display_search_results;
    
public slots:

    void undo();
    int copy();
    void paste();
    int cut();

    void edit_note();
    void new_note();
    void new_note_from_clipboard();

    void new_nf();
    void rename_nf();
    void delete_nf();

    void make_link();
    void next_nf();
    void prev_nf();
    void delete_selected();

    void toggle_help();
    void make_viewpoint_default();
    void make_current_viewpoint_height_default();
    void make_nf_default();
    void add_new_folder();
    void add_menu_entry_for_dir(QString path);
    void remove_current_folder();
    void set_current_misli_dir(QString name);
    void clear_settings_and_exit();

    void set_lang_bg();
    void set_lang_en();

    void switch_current_nf();
    void update_current_nf();

    void col_blue();
    void col_green();
    void col_red();
    void col_black();
    void col_transparent_background();

    void zoom_out();
    void zoom_in();
    void move_up();
    void move_down();
    void move_right();
    void move_left();

    void recheck_for_dirs();
    void display_results(QString string);
    void hide_search_stuff();
    void select_all_notes();
    void find_by_text(QString string);
    void show_note_details_window();
    void select_note_under_mouse();
    void show_about_dialog();
public:
    Ui::MisliWindow *ui;
private:
    //Functions
    //bool event(QEvent *event);
    //bool gestureEvent(QGestureEvent *event);
    //bool pinchTriggered(QPinchGesture *gesture);
    void closeEvent(QCloseEvent *);
    void import_settings_and_folders();

};

#endif // MISLIWINDOW_H
