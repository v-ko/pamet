/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <QtGui>
#include "editnotewindow.h"
#include "common.h"
#include "misliinstance.h"
#include <QTextCursor>

EditNoteWindow::EditNoteWindow(MisliInstance *m_i)
{
    misl_i=m_i;

    //Init elements
    label = new QLabel("Note text:");
    text_edit = new QTextEdit;
    button = new QPushButton("Ok (ctrl+S)");
    makeLinkButton= new QPushButton("Make link");

    //Connect signals
    connect(button,SIGNAL(clicked()),this,SLOT(input_done()));
    connect(makeLinkButton,SIGNAL(clicked()),this,SLOT(make_link()));

    //Shortcuts
    //--------Enter(return) - submit ---------------
    shEnter = new QShortcut(QKeySequence(Qt::CTRL+Qt::Key_S),this);
    connect(shEnter,SIGNAL( activated() ),button,SIGNAL( clicked() ) ); //edit the first selected note
    //-------Escape---------------------
    shEscape = new QShortcut(QKeySequence(Qt::Key_Escape),this);
    connect(shEscape,SIGNAL( activated() ),this,SLOT( close() ) ); //edit the first selected note
    //-------Make link-----------------
    shMakeLink = new QShortcut(QKeySequence(Qt::CTRL+Qt::Key_L),this);
    connect(shMakeLink,SIGNAL( activated() ),makeLinkButton,SLOT( click() ) ); //edit the first selected note


    //Set layout
    QGroupBox *hbox = new QGroupBox;
        QHBoxLayout *hlayout = new QHBoxLayout;
        hlayout->addWidget(label);
        hlayout->addWidget(makeLinkButton);
    hbox->setLayout(hlayout);

    QVBoxLayout *mainLayout = new QVBoxLayout;
        mainLayout->addWidget(hbox);
        mainLayout->addWidget(text_edit);
        mainLayout->addWidget(button);
    setLayout(mainLayout);

}

void EditNoteWindow::new_note()
{
    setWindowTitle("Make new note");

    x_on_new_note=misl_i->gl_w->mapFromGlobal( QCursor::pos() ).x(); //cursor position relative to the gl widget
    y_on_new_note=misl_i->gl_w->mapFromGlobal( QCursor::pos() ).y();

    move(QCursor::pos());

    text_edit->setText("");
    edited_note=NULL;

    show();
    raise();
    activateWindow();
    text_edit->setFocus(Qt::ActiveWindowFocusReason);

}

int EditNoteWindow::edit_note(){ //false for new note , true for edit

    QString text;

    setWindowTitle("Edit note");

    edited_note=misl_i->curr_nf()->get_first_selected_note();
    if(edited_note==NULL){return 1;}

    move(QCursor::pos());

    text=text.fromUtf8(edited_note->text);
    text_edit->setText(text);

    show();
    raise();
    activateWindow();
    text_edit->setFocus(Qt::ActiveWindowFocusReason);

    return 0;
}

void EditNoteWindow::input_done(){

    QString qstr = text_edit->toPlainText().trimmed();
    char *text=strdup(qstr.toUtf8().data());

    float x,y;
    Note *nt;

    if( edited_note==NULL){//If we're making a new note
        misl_i->gl_w->unproject_to_plane(0,x_on_new_note,y_on_new_note,x,y); //get mouse pos in real coordinates
        nt=misl_i->curr_nf()->add_note(misl_i,text,x,y,null_note.z,null_note.a,null_note.b,null_note.font_size,QDate::currentDate(),QDate::currentDate());
        nt->link_to_selected();
    }else {//else we're in edit mode
        x=edited_note->x;
        y=edited_note->y;
        if(strcmp(edited_note->text,text)!=0){
            edited_note->text=strdup(text);
            edited_note->dt_mod=QDate::currentDate();
        }

        //font,cvqt,etc
        edited_note->init();
    }
    misl_i->curr_nf()->save();

    misl_i->edit_w->close();
    misl_i->gl_w->updateGL();

    edited_note=NULL;
    }

void EditNoteWindow::make_link()
{
    text_edit->setText("this_note_points_to:");
    text_edit->setFocus();
    text_edit->moveCursor (QTextCursor::End);
}
