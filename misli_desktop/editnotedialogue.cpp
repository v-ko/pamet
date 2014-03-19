/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "editnotedialogue.h"
#include "ui_editnotedialogue.h"

#include "misliwindow.h"
#include "../canvas.h"
#include "mislidesktopgui.h"

EditNoteDialogue::EditNoteDialogue(MisliDesktopGui * misli_dg_) :
    ui(new Ui::EditNoteDialogue)
{
    ui->setupUi(this);
    misli_dg=misli_dg_;
    addAction(ui->actionEscape);
}

MisliInstance * EditNoteDialogue::misli_i()
{
    return misli_dg->misli_i;
}

EditNoteDialogue::~EditNoteDialogue()
{
    delete ui;
}

void EditNoteDialogue::new_note()
{
    setWindowTitle(tr("Make new note"));

    x_on_new_note=misli_dg->misli_w->canvas->mapFromGlobal( QCursor::pos() ).x(); //cursor position relative to the gl widget
    y_on_new_note=misli_dg->misli_w->canvas->mapFromGlobal( QCursor::pos() ).y();

    move(QCursor::pos());

    ui->textEdit->setText("");
    edited_note=NULL;

    show();
    raise();
    activateWindow();
    ui->textEdit->setFocus(Qt::ActiveWindowFocusReason);

}

int EditNoteDialogue::edit_note(){ //false for new note , true for edit

    QString text;

    setWindowTitle(tr("Edit note"));

    edited_note=misli_i()->curr_misli_dir()->curr_nf()->get_first_selected_note();
    if(edited_note==NULL){return 1;}

    move(QCursor::pos());

    text=edited_note->text;
    ui->textEdit->setPlainText(text);

    show();
    raise();
    activateWindow();
    ui->textEdit->setFocus(Qt::ActiveWindowFocusReason);

    return 0;
}

void EditNoteDialogue::input_done()
{
    QString text = ui->textEdit->toPlainText().trimmed();
    text = text.replace("\r\n","\n"); //for the f-n windows standart

    Note null_note;

    float x,y;
    Note *nt;
    float txt_col[] = {0,0,1,1};
    float bg_col[] = {0,0,1,0.1};

    if( edited_note==NULL){//If we're making a new note
        misli_dg->misli_w->canvas->unproject(x_on_new_note,y_on_new_note,x,y); //get mouse pos in real coordinates
        nt=misli_i()->curr_misli_dir()->curr_nf()->add_note(text,x,y,null_note.z,null_note.a,null_note.b,null_note.font_size,QDateTime::currentDateTime(),QDateTime::currentDateTime(),txt_col,bg_col);
        nt->link_to_selected();
        nt->auto_size();
    }else {//else we're in edit mode
        x=edited_note->x;
        y=edited_note->y;
        if(edited_note->text!=text){
            edited_note->text=text;
            edited_note->t_mod=QDateTime::currentDateTime();
        }

        //font,color,etc
        edited_note->init();
    }
    misli_i()->curr_misli_dir()->curr_nf()->save();
    misli_dg->misli_w->update_current_nf();
    misli_dg->edit_w->close();

    edited_note=NULL;
    }

void EditNoteDialogue::make_link()
{
    ui->textEdit->setText("this_note_points_to:");
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}

