#ifndef MISLIWINDOW_H
#define MISLIWINDOW_H

#include <QMainWindow>
#include <QSettings>
#include <QAction>

#include "misliinstance.h"
#include "emitmynameaction.h"

class NewNFDialogue;
class EditNoteDialogue;
class GetDirDialogue;
class GLWidget;

namespace Ui {
class MisliWindow;
}

class MisliWindow : public QMainWindow
{
    Q_OBJECT
    
public:
    //Functions
    MisliWindow(QApplication *app);
    ~MisliWindow();

    void add_dir(QString path);
    MisliInstance * curr_misli();
    MisliInstance * misli_by_name(QString path);

    //Windows
    GLWidget *gl_w;
    GetDirDialogue *dir_w;
    NewNFDialogue *newnf_w;
    EditNoteDialogue *edit_w;

    //Variables
    QApplication *a;
    QSettings *settings;
        QString language;
    std::vector<MisliInstance*> misli;
    QString current_misli_name;
    MisliInstance * curr_msl;
    int notes_rdy;
    bool first_program_start;

public slots:
    void undo();
    void copy();
    void paste();
    void cut();

    void edit_note();
    void new_note();
    void new_nf();
    void make_link();
    void next_nf();
    void prev_nf();
    void delete_selected();
    void zoom_out();
    void zoom_in();
    void toggle_help();
    void make_viewpoint_default();
    void make_nf_default();
    void add_new_folder();
    void remove_current_folder();
    void set_current_misli(QString name);
    void clear_settings_and_exit();

    void set_lang_bg();
    void set_lang_en();

    void switch_current_nf();
    void update_current_nf();
private:
    //Functions
    void import_settings_and_folders();
    void export_settings();

    //Variables
    Ui::MisliWindow *ui;
};

#endif // MISLIWINDOW_H
