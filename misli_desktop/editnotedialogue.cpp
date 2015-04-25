/*  This file is part of Misli.

    Misli is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Misli is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "editnotedialogue.h"
#include "ui_editnotedialogue.h"

#include <QFileDialog>

#include "misliwindow.h"
#include "../canvas.h"

EditNoteDialogue::EditNoteDialogue(MisliWindow *misliWindow_) :
    linkMenu(this),
    chooseNFMenu(tr("NoteFile"),&linkMenu),
    actionChooseTextFile(tr("Text file (in beta)"),&linkMenu),
    actionChoosePicture(tr("Picure (in beta)"),&linkMenu),
    actionSystemCallNote(tr("System call note (very beta)"),&linkMenu),
    ui(new Ui::EditNoteDialogue)
{
    ui->setupUi(this);
    misliWindow = misliWindow_;
    addAction(ui->actionEscape);

    linkMenu.addMenu(&chooseNFMenu);
    linkMenu.addAction(&actionChoosePicture);
    linkMenu.addAction(&actionChooseTextFile);
    linkMenu.addAction(&actionSystemCallNote);

    connect(ui->okButton,SIGNAL(clicked()),this,SLOT(inputDone()));
    connect(&chooseNFMenu,SIGNAL(aboutToShow()),this,SLOT(updateChooseNFMenu()));
    connect(ui->makeLinkButton,SIGNAL(clicked()),this,SLOT(showLinkMenu()));
    connect(&chooseNFMenu,SIGNAL(triggered(QAction*)),this,SLOT(makeLinkNote(QAction*)));
    connect(&actionChoosePicture,SIGNAL(triggered()),this,SLOT(choosePicture()));
    connect(&actionChooseTextFile,SIGNAL(triggered()),this,SLOT(chooseTextFile()));
    connect(&actionSystemCallNote,SIGNAL(triggered()),this,SLOT(setSystemCallPrefix()));
}

MisliInstance * EditNoteDialogue::misli_i()
{
    return misliWindow->misliInstance();
}

EditNoteDialogue::~EditNoteDialogue()
{
    delete ui;
}

void EditNoteDialogue::newNote()
{
    setWindowTitle(tr("Make new note"));

    x_on_new_note=misliWindow->canvas->current_mouse_x; //cursor position relative to the gl widget
    y_on_new_note=misliWindow->canvas->current_mouse_y;

    move(QCursor::pos());

    ui->textEdit->setText("");
    edited_note=NULL;

    show();
    raise();
    activateWindow();
    ui->textEdit->setFocus(Qt::ActiveWindowFocusReason);
}

int EditNoteDialogue::editNote(){ //false for new note , true for edit

    QString text;

    setWindowTitle(tr("Edit note"));

    edited_note=misliWindow->canvas->noteFile()->getFirstSelectedNote();
    if(edited_note==NULL){return 1;}

    move(QCursor::pos());

    text=edited_note->text_m;
    setTextEditText(text);

    show();
    raise();
    activateWindow();
    ui->textEdit->setFocus(Qt::ActiveWindowFocusReason);

    return 0;
}

void EditNoteDialogue::inputDone()
{
    QString text = ui->textEdit->toPlainText().trimmed();
    text = text.replace("\r\n","\n"); //for the f-in windows standart

    float x,y;
    Note *nt;
    QColor txt_col,bg_col;
    txt_col.setRgbF(0,0,1,1);
    bg_col.setRgbF(0,0,1,0.1);

    if( edited_note==NULL){//If we're making a new note
        misliWindow->canvas->unproject(x_on_new_note,y_on_new_note,x,y); //get mouse pos in real coordinates
        nt=new Note(misliWindow->canvas->noteFile()->getNewId(),
                    text,
                    QRectF(x,y,1,1),
                    1,
                    QDateTime::currentDateTime(),
                    QDateTime::currentDateTime(),
                    txt_col,
                    bg_col);
        nt->autoSize();
        misliWindow->canvas->noteFile()->linkSelectedNotesTo(nt);
        misliWindow->canvas->noteFile()->addNote(nt); //invokes save
    }else { //else we're in edit mode
        x = edited_note->rect().x();
        y = edited_note->rect().y();
        if(edited_note->text_m!=text){
            edited_note->setText(text);
        }
    }
    close();
    edited_note=NULL;
}

void EditNoteDialogue::makeLinkNote(QAction *act)
{
    ui->textEdit->setText("this_note_points_to:"+act->text());
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
    this->hide();//FIXME
    this->show();

}
void EditNoteDialogue::setTextEditText(QString text)
{
    ui->textEdit->setPlainText(text);
}

void EditNoteDialogue::updateChooseNFMenu()
{
    chooseNFMenu.clear();

    for(NoteFile *nf: misliWindow->currentDir()->noteFiles()){
        chooseNFMenu.addAction(nf->name());
    }
}

void EditNoteDialogue::showLinkMenu()
{
    linkMenu.popup(cursor().pos());
}

void EditNoteDialogue::choosePicture()
{
    QFileDialog dialog;
    QString file = dialog.getOpenFileName(this,tr("Choose a picture"));

    ui->textEdit->setText("define_picture_note:"+file);
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::chooseTextFile()
{
    QFileDialog dialog;
    QString file = dialog.getOpenFileName(this,tr("Choose a picture"));

    ui->textEdit->setText("define_text_file_note:"+file);
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::setSystemCallPrefix()
{
    ui->textEdit->setText("define_system_call_note:");
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
