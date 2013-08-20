/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef EDITNOTEDIALOGUE_H
#define EDITNOTEDIALOGUE_H

#include <QtGui>
#include <QWidget>

class Note;
class MisliInstance;

namespace Ui {
class EditNoteDialogue;
}

class EditNoteDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    EditNoteDialogue(MisliInstance * misli_i_);
    ~EditNoteDialogue();
    
    //Variables
    MisliInstance *misli_i;
    Note * edited_note;
    double x_on_new_note,y_on_new_note;

public slots:
    void make_link();
    void new_note();
    int edit_note();
    void input_done();

private:
    Ui::EditNoteDialogue *ui;
};

#endif // EDITNOTEDIALOGUE_H
