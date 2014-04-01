/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "editnotedialogue.h"
#include "ui_editnotedialogue.h"

#include "misliwindow.h"
#include "../canvas.h"
#include "mislidesktopgui.h"

EditNoteDialogue::EditNoteDialogue(MisliDesktopGui * misli_dg_) :
    linkMenu(this),
    chooseNFMenu(tr("NoteFile"),&linkMenu),
    actionChooseTextFile(tr("Text file (in beta)"),&linkMenu),
    actionChoosePicture(tr("Picure (in beta)"),&linkMenu),
    actionSystemCallNote(tr("System call note (very beta)"),&linkMenu),
    ui(new Ui::EditNoteDialogue)
{
    ui->setupUi(this);
    misli_dg=misli_dg_;
    addAction(ui->actionEscape);

    linkMenu.addMenu(&chooseNFMenu);
    linkMenu.addAction(&actionChoosePicture);
    linkMenu.addAction(&actionChooseTextFile);
    linkMenu.addAction(&actionSystemCallNote);

    connect(ui->makeLinkButton,SIGNAL(clicked()),this,SLOT(show_link_menu()));
    connect(&chooseNFMenu,SIGNAL(triggered(QAction*)),this,SLOT(make_link_note(QAction*)));
    connect(&actionChoosePicture,SIGNAL(triggered()),this,SLOT(choose_picture()));
    connect(&actionChooseTextFile,SIGNAL(triggered()),this,SLOT(choose_text_file()));
    connect(&actionSystemCallNote,SIGNAL(triggered()),this,SLOT(set_system_call_prefix()));
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

    x_on_new_note=misli_dg->misli_w->canvas->current_mouse_x; //cursor position relative to the gl widget
    y_on_new_note=misli_dg->misli_w->canvas->current_mouse_y;

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
    set_textEdit_text(text);

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
        nt->auto_size();
        nt->link_to_selected();
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

void EditNoteDialogue::make_link_note(QAction *act)
{
    ui->textEdit->setText("this_note_points_to:"+act->text());
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::set_textEdit_text(QString text)
{
    ui->textEdit->setPlainText(text);
}
void EditNoteDialogue::show_link_menu()
{
    chooseNFMenu.clear();

    for(unsigned int i=0;i<misli_i()->curr_misli_dir()->note_file.size();i++){
        chooseNFMenu.addAction(misli_i()->curr_misli_dir()->note_file[i]->name);
    }

    linkMenu.popup(cursor().pos());
}

void EditNoteDialogue::choose_picture()
{
    QFileDialog dialog;
    QString file = dialog.getOpenFileName(this,tr("Choose a picture"));

    ui->textEdit->setText("define_picture_note:"+file);
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::choose_text_file()
{
    QFileDialog dialog;
    QString file = dialog.getOpenFileName(this,tr("Choose a picture"));

    ui->textEdit->setText("define_text_file_note:"+file);
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::set_system_call_prefix()
{
    ui->textEdit->setText("define_system_call_note:");
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
