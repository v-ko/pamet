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
#include <QLayout>

#include "misliwindow.h"
#include "../canvas.h"

EditNoteDialogue::EditNoteDialogue(MisliWindow *misliWindow_) :
    linkMenu(this),
    chooseNFMenu(tr("NoteFile"),&linkMenu),
    actionChooseTextFile(tr("Text file"),&linkMenu),
    actionChoosePicture(tr("Picture"),&linkMenu),
    actionPythonScriptNote(tr("Script note"),&linkMenu),
    actionWebPageNote(tr("Web page note"),&linkMenu),
    ui(new Ui::EditNoteDialogue)
{
    ui->setupUi(this);
    misliWindow = misliWindow_;
    addAction(ui->actionEscape);

//    actionPythonScriptNote.setCheckable(true);

    linkMenu.addMenu(&chooseNFMenu);
    linkMenu.addAction(&actionChoosePicture);
    linkMenu.addAction(&actionChooseTextFile);
    linkMenu.addAction(&actionPythonScriptNote);
    linkMenu.addAction(&actionWebPageNote);

    connect(ui->okButton,SIGNAL(clicked()),this,SLOT(inputDone()));
    connect(&chooseNFMenu,SIGNAL(aboutToShow()),this,SLOT(updateChooseNFMenu()));
    connect(ui->makeLinkButton,SIGNAL(clicked()),this,SLOT(showLinkMenu()));
    connect(&chooseNFMenu,SIGNAL(triggered(QAction*)),this,SLOT(makeLinkNote(QAction*)));
    connect(&actionChoosePicture,SIGNAL(triggered()),this,SLOT(choosePicture()));
    connect(&actionChooseTextFile,SIGNAL(triggered()),this,SLOT(chooseTextFile()));
    connect(&actionPythonScriptNote,SIGNAL(triggered()),this,SLOT(setSystemCallPrefix()));
    connect(&misliWindow->timelineWidget.timeline->slider, &QSlider::valueChanged, this, &EditNoteDialogue::raise);

    //UI functions
    //Set duration to a day (lambda)
    connect(ui->dayButton,&QPushButton::clicked,[&](){
        Timeline *timeline = misliWindow->timelineWidget.timeline;
        QSlider *slider = &timeline->slider;

        if(timeline->viewportSizeInMSecs<days){
            timeline->viewportSizeInMSecs = days;
            timeline->update();
        }

        QDateTime sliderStartTime = QDateTime::fromMSecsSinceEpoch(timeline->scaleToMSeconds(slider->pos().x())+timeline->leftEdgeInMSecs());
        sliderStartTime.setTime( QTime(0,0,0) );

        x_on_new_note = timeline->scaleToPixels( sliderStartTime.toMSecsSinceEpoch() - timeline->leftEdgeInMSecs() );
        if(x_on_new_note<0){
            timeline->positionInMSecs += timeline->scaleToMSeconds(x_on_new_note);
            x_on_new_note = 0;
        }
        slider->move(x_on_new_note, slider->pos().y());
        slider->setValue( timeline->scaleToPixels( days ) - 5);
        timeline->update();
    });

    //Set duration to a week (lambda)
    connect(ui->weekButton,&QPushButton::clicked,[&](){
        Timeline *timeline = misliWindow->timelineWidget.timeline;
        QSlider *slider = &timeline->slider;

        if(timeline->viewportSizeInMSecs<(7*days)){
            timeline->viewportSizeInMSecs = 7*days;
            timeline->update();
        }

        QDateTime sliderStartTime = QDateTime::fromMSecsSinceEpoch(timeline->scaleToMSeconds(slider->pos().x())+timeline->leftEdgeInMSecs());
        sliderStartTime.setTime( QTime(0,0,0) );
        //QDateTime dt = sliderStartTime.addDays( -sliderStartTime.date().dayOfWeek() + 1); //Set to Monday
        //sliderStartTime.setDate( dt.date() );

        x_on_new_note = timeline->scaleToPixels( sliderStartTime.toMSecsSinceEpoch() - timeline->leftEdgeInMSecs() );
        if(x_on_new_note<0){
            timeline->positionInMSecs += timeline->scaleToMSeconds(x_on_new_note);
            x_on_new_note = 0;
        }
        slider->move(x_on_new_note, slider->pos().y());
        slider->setValue( timeline->scaleToPixels( 7*days ) - 5);
        timeline->update();
    });

    //Set duration to a month (lambda)
    connect(ui->monthButton,&QPushButton::clicked,[&](){
        Timeline *timeline = misliWindow->timelineWidget.timeline;
        QSlider *slider = &timeline->slider;

        if(timeline->viewportSizeInMSecs<months){
            timeline->viewportSizeInMSecs = months;
            timeline->update();
        }

        QDateTime sliderStartTime = QDateTime::fromMSecsSinceEpoch(timeline->scaleToMSeconds(slider->pos().x())+timeline->leftEdgeInMSecs());
        sliderStartTime.setTime( QTime(0,0,0) );
        sliderStartTime.setDate( QDate( sliderStartTime.date().year(), sliderStartTime.date().month(), 1));

        x_on_new_note = timeline->scaleToPixels( sliderStartTime.toMSecsSinceEpoch() - timeline->leftEdgeInMSecs() );
        if(x_on_new_note<0){
            timeline->positionInMSecs += timeline->scaleToMSeconds(x_on_new_note);
            x_on_new_note = 0;
        }
        slider->move(x_on_new_note, slider->pos().y());
        slider->setValue( timeline->scaleToPixels( months ) - 5);
        timeline->update();
    });

    //Set duration to a year (lambda)
    connect(ui->yearButton,&QPushButton::clicked,[&](){
        Timeline *timeline = misliWindow->timelineWidget.timeline;
        QSlider *slider = &timeline->slider;

        if(timeline->viewportSizeInMSecs<years){
            timeline->viewportSizeInMSecs = years;
            timeline->update();
        }

        QDateTime sliderStartTime = QDateTime::fromMSecsSinceEpoch(timeline->scaleToMSeconds(slider->pos().x())+timeline->leftEdgeInMSecs());
        sliderStartTime.setTime( QTime(0,0,0) );
        sliderStartTime.setDate( QDate( sliderStartTime.date().year(), 1, 1));

        x_on_new_note = timeline->scaleToPixels( sliderStartTime.toMSecsSinceEpoch() - timeline->leftEdgeInMSecs() );
        if(x_on_new_note<0){
            timeline->positionInMSecs += timeline->scaleToMSeconds(x_on_new_note);
            x_on_new_note = 0;
        }
        slider->move(x_on_new_note, slider->pos().y());
        slider->setValue( timeline->scaleToPixels( years ) - 5);
        timeline->update();
    });

    //Set the web page note template
    connect(&actionWebPageNote,&QAction::triggered,[&](){
        ui->textEdit->setText("define_web_page_note:\nurl=\nname="+ui->textEdit->toPlainText());
        ui->textEdit->setFocus();
        ui->textEdit->moveCursor (QTextCursor::End);
    });
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

    x_on_new_note = misliWindow->currentCanvas_m->mousePos().x(); //cursor position relative to the gl widget
    y_on_new_note = misliWindow->currentCanvas_m->mousePos().y();

    move(QCursor::pos());

    ui->textEdit->setText("");
    edited_note = NULL;

    //UI stuff
    ui->openButton->hide();
    if(misliWindow->timelineTabIsActive()){
        ui->yearButton->show();
        ui->monthButton->show();
        ui->weekButton->show();
        ui->dayButton->show();
    }else{
        ui->yearButton->hide();
        ui->monthButton->hide();
        ui->weekButton->hide();
        ui->dayButton->hide();
    }
    show();
    raise();
    activateWindow();
    ui->textEdit->setFocus(Qt::ActiveWindowFocusReason);
}

void EditNoteDialogue::editNote() //false for new note , true for edit
{
    Timeline *timeline = misliWindow->timelineWidget.timeline;
    QSlider *slider = &timeline->slider;

    if(misliWindow->timelineTabIsActive()){
        ui->yearButton->show();
        ui->monthButton->show();
        ui->weekButton->show();
        ui->dayButton->show();
        edited_note = misliWindow->timelineWidget.timeline->archiveModule.noteFile.getFirstSelectedNote();
    }else{
        ui->yearButton->hide();
        ui->monthButton->hide();
        ui->weekButton->hide();
        ui->dayButton->hide();
        edited_note = misliWindow->currentCanvas_m->noteFile()->getFirstSelectedNote();
    }
    if(edited_note==NULL){return;}

    if(misliWindow->timelineTabIsActive()){
        slider->move( timeline->scaleToPixels(edited_note->timeMade.toMSecsSinceEpoch() - timeline->leftEdgeInMSecs()),
                      timeline->baselineY() );
        qint64 intTest = edited_note->timeModified.toMSecsSinceEpoch() -
                edited_note->timeMade.toMSecsSinceEpoch();
        float test = timeline->scaleToPixels( intTest );
        slider->setValue( test );
        slider->show();
    }
    setWindowTitle(tr("Edit note"));
    move(QCursor::pos());

    setTextEditText(edited_note->text_m);

    if(edited_note->type==NoteType::systemCall){
        ui->openButton->show();
    }else{
        ui->openButton->hide();
    }

    show();
    raise();
    activateWindow();
    ui->textEdit->setFocus(Qt::ActiveWindowFocusReason);

    return;
}

void EditNoteDialogue::inputDone()
{
    Timeline *timeline = misliWindow->timelineWidget.timeline;
    QSlider *slider = &timeline->slider;

    misliWindow->misliDesktopGUI->setOverrideCursor(Qt::WaitCursor);
    misliWindow->timelineWidget.timeline->slider.hide();

    QString text = ui->textEdit->toPlainText().trimmed();
    text = text.replace("\r\n","\n"); //for the f-in windows standart

    Note *nt;
    QColor txt_col,bg_col;
    txt_col.setRgbF(0,0,1,1);
    bg_col.setRgbF(0,0,1,0.1);
    float x, y;

    if( edited_note==NULL){//If we're making a new note

        if( !misliWindow->timelineTabIsActive() ){
            misliWindow->currentCanvas_m->unproject(x_on_new_note,y_on_new_note, x, y); //get mouse pos in real coordinates
            nt=new Note();
            nt->id = misliWindow->currentCanvas_m->noteFile()->getNewId();
            nt->text_m = text;
            nt->setRect(QRectF(x,y,1,1));
            nt->timeMade = QDateTime::currentDateTime();
            nt->timeModified = QDateTime::currentDateTime();
            nt->textColor_m = txt_col;
            nt->backgroundColor_m = bg_col;
            nt->commonInitFunction();
            nt->requestAutoSize = true;

            misliWindow->currentCanvas_m->noteFile()->linkSelectedNotesTo(nt);
            misliWindow->currentCanvas_m->noteFile()->addNote(nt); //invokes save
        }else if( misliWindow->timelineTabIsActive() ){
            nt=new Note();
            nt->id = 0;
            nt->text_m = text;
            nt->setRect(QRectF(x,y,1,1));
            nt->timeMade = QDateTime::fromMSecsSinceEpoch( timeline->leftEdgeInMSecs() + timeline->scaleToMSeconds( slider->pos().x() ) );
            nt->timeModified = nt->timeMade.addMSecs( timeline->scaleToMSeconds(slider->value()) );
            nt->textColor_m = txt_col;
            nt->backgroundColor_m = bg_col;
            nt->commonInitFunction();

            timeline->archiveModule.noteFile.addNote(nt);
        }

    }else { //else we're in edit mode
        if(misliWindow->timelineTabIsActive()){
            QDateTime newStart = QDateTime::fromMSecsSinceEpoch( timeline->leftEdgeInMSecs() +
                                                                    timeline->scaleToMSeconds( slider->pos().x()) );
            QDateTime newEnd = newStart.addMSecs( timeline->scaleToMSeconds( slider->value()) );

            if( (newStart!=edited_note->timeMade) | (newEnd!=edited_note->timeModified) ) {
                edited_note->timeMade = newStart;
                edited_note->timeModified = newEnd;

                if(text!=edited_note->text()){
                    edited_note->setText(text);
                }else{
                    emit edited_note->propertiesChanged();
                }
            }else{
                edited_note->setText(text);
            }

        }else{
            edited_note->changeTextAndTimestamp(text);
        }
    }
    close();
    edited_note=nullptr;

    misliWindow->misliDesktopGUI->restoreOverrideCursor();
}

void EditNoteDialogue::makeLinkNote(QAction *act)
{
    ui->textEdit->setText("this_note_points_to:"+act->text());
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);

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

    ui->textEdit->setText("define_picture_note:"+maybeToRelativePath(file));
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::chooseTextFile()
{
    QFileDialog dialog;
    QString file = dialog.getOpenFileName(this,tr("Choose a picture"));

    ui->textEdit->setText("define_text_file_note:"+maybeToRelativePath(file));
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}
void EditNoteDialogue::setSystemCallPrefix()
{
    ui->textEdit->setText("define_system_call_note:"+ui->textEdit->toPlainText());
    ui->textEdit->setFocus();
    ui->textEdit->moveCursor (QTextCursor::End);
}

void EditNoteDialogue::closeEvent(QCloseEvent *)
{

    misliWindow->timelineWidget.timeline->slider.hide();
}

QString EditNoteDialogue::maybeToRelativePath(QString path)
{
    if(path.startsWith(misliWindow->currentDir()->directoryPath())){
        return path.replace(misliWindow->currentDir()->directoryPath(),".");
    }else{
        return path;
    }
}

void EditNoteDialogue::on_openButton_clicked()
{
    QString path = edited_note->addressString.split(" ")[0];
    QFile f(path);
    if(!f.exists()){
        f.open(QFile::WriteOnly);
        f.setPermissions(QFileDevice::ExeOwner | f.permissions());
        f.write("#!/bin/bash\n");
        f.write("#!/usr/bin/env python\n");
        f.close();

    }
    QProcess::execute("subl3", QStringList()<<path);
}
