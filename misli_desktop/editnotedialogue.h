/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef EDITNOTEDIALOGUE_H
#define EDITNOTEDIALOGUE_H

#include <QtGui>
#include <QWidget>
#include <QMenu>

class Note;
class MisliInstance;

class MisliDesktopGui;
namespace Ui {
class EditNoteDialogue;
}

class EditNoteDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    EditNoteDialogue(MisliDesktopGui * misli_dg_);
    ~EditNoteDialogue();

    MisliInstance * misli_i();
    
    //Variables
    QMenu linkMenu,chooseNFMenu;
    QAction actionChooseTextFile,actionChoosePicture,actionSystemCallNote;
    MisliDesktopGui *misli_dg;
    Note * edited_note;
    double x_on_new_note,y_on_new_note;

public slots:
    void new_note();
    int edit_note();
    void input_done();
    void set_textEdit_text(QString text); //expose that publically

    void show_link_menu();
    void make_link_note(QAction *act);
    void choose_picture();
    void choose_text_file();
    void set_system_call_prefix();
private:
    Ui::EditNoteDialogue *ui;
};

#endif // EDITNOTEDIALOGUE_H
