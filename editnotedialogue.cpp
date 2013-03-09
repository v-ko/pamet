/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "editnotedialogue.h"
#include "ui_editnotedialogue.h"

#include "misliwindow.h"

EditNoteDialogue::EditNoteDialogue(MisliWindow *msl_w_) :
    ui(new Ui::EditNoteDialogue)
{
    ui->setupUi(this);
    msl_w=msl_w_;
}

EditNoteDialogue::~EditNoteDialogue()
{
    delete ui;
}

void EditNoteDialogue::new_note()
{
    setWindowTitle(tr("Make new note"));

    x_on_new_note=msl_w->gl_w->mapFromGlobal( QCursor::pos() ).x(); //cursor position relative to the gl widget
    y_on_new_note=msl_w->gl_w->mapFromGlobal( QCursor::pos() ).y();

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

    edited_note=msl_w->curr_misli()->curr_nf()->get_first_selected_note();
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

void EditNoteDialogue::input_done(){

    QString text = ui->textEdit->toPlainText().trimmed();
    text = text.replace("\r\n","\n"); //for the f-n windows standart

    Note null_note;

    /*if(text.size()>600){
        QMessageBox mb(QMessageBox::Warning,"Too much text","This note is more than 600 characters . This would slow down the program . This limitation won't be in the next release",QMessageBox::Ok);
        mb.exec();
        return;
    }*/

    float x,y;
    Note *nt;
    float txt_col[] = {0,0,1,1};
    float bg_col[] = {0,0,1,0.1};

    if( edited_note==NULL){//If we're making a new note
        msl_w->gl_w->unproject_to_plane(0,x_on_new_note,y_on_new_note,x,y); //get mouse pos in real coordinates
        nt=msl_w->curr_misli()->curr_nf()->add_note(msl_w->curr_misli(),text,x,y,null_note.z,null_note.a,null_note.b,null_note.font_size,QDateTime::currentDateTime(),QDateTime::currentDateTime(),txt_col,bg_col);
        nt->link_to_selected();
    }else {//else we're in edit mode
        x=edited_note->x;
        y=edited_note->y;
        if(edited_note->text!=text){
            edited_note->text=text;
            edited_note->t_mod=QDateTime::currentDateTime();
        }

        //font,cvqt,etc
        edited_note->init();
    }
    msl_w->curr_misli()->curr_nf()->save();
    msl_w->edit_w->close();

    edited_note=NULL;
    }

void EditNoteDialogue::make_link()
{
    ui->textEdit->setText("this_note_points_to:");
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
