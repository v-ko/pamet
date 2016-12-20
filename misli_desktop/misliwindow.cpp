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

#include <QInputDialog>
#include <QMessageBox>
#include <QFileDialog>
#include <QtGlobal>
#include <QNetworkReply>
#include <QDomDocument>
#include <QLayout>

#include "misliwindow.h"
#include "../misliinstance.h"
#include "ui_misliwindow.h"

#include "editnotedialogue.h"
#include "../canvas.h"
#include "mislidesktopgui.h"

MisliWindow::MisliWindow(MisliDesktopGui * misli_dg_):
    ui(new Ui::MisliWindow),
    tabWidget(this),
    timelineWidget(this),
    updateMenu(tr("Update available"))
{
    ui->setupUi(this);
    setWindowIcon(QIcon(":/img/icon.png"));

    misliDesktopGUI = misli_dg_;
    currentDir_m = NULL;
    nfBeforeHelp = NULL;
    updateCheckDone = false;

    //Init notes search stuff
    notes_search = new NotesSearch;
    notes_search->moveToThread(&misliDesktopGUI->workerThread);
    notes_search->loadNotes(misliInstance(),1);
    ui->searchListView->setModel(notes_search);
    QItemSelectionModel *selectionModel = ui->searchListView->selectionModel();
    //Handle search result selection (lambda)
    connect(selectionModel, &QItemSelectionModel::selectionChanged, this,
            [&](const QItemSelection &, const QItemSelection &){

        const QModelIndex index = ui->searchListView->selectionModel()->currentIndex();
        NotesSearch::SearchItem searchItem = notes_search->searchResults.at(index.row());
        setCurrentDir(searchItem.md);
        canvas->setNoteFile(searchItem.nf);
        canvas->centerEyeOnNote(searchItem.nt);
    });

    //Init widgets and widnows
    ui->mainLayout->addWidget(&tabWidget);
    edit_w = new EditNoteDialogue(this);
    tabWidget.addTab(&timelineWidget,"/timeline");
    canvas = new Canvas(this);
    tabWidget.addTab(canvas,"");
    ui->searchLineEdit->hide();
    ui->searchListView->hide();
    ui->jumpToNearestNotePushButton->hide();
    updateMenu.addAction(ui->actionDownload_it);

    addAction(ui->actionSelect_note_under_mouse);
    addAction(ui->actionNext_notefile);
    addAction(ui->actionPrevious_notefile);
    addAction(ui->actionGotoTab1);
    addAction(ui->actionGotoTab2);

    //============Update check stuff=======================
    //If it's the android build - just hide the action. No network connectivity will solve the rest
#ifndef Q_OS_ANDROID
    ui->menuOther->addAction(ui->actionCheck_for_updates);
#endif
    if(settings.value("check_for_updates",QVariant(true)).toBool()){
        ui->actionCheck_for_updates->setChecked(true);
    }else{
        ui->actionCheck_for_updates->setChecked(false);
    } //from here on this is the flag if we're checking for updates or not (the checked state)

    connect(&network,&QNetworkAccessManager::finished,this,&MisliWindow::handleVersionInfoReply);
    if(network.networkAccessible()){
        startUpdateCheck();
    }else{
        connect(&network,&QNetworkAccessManager::networkAccessibleChanged,
                [&](QNetworkAccessManager::NetworkAccessibility accessibility){
            if(accessibility==QNetworkAccessManager::Accessible){
                startUpdateCheck();
            }
        });
    }

    //--------------------Connect signals/slots-----------------------------------
    //Actions/shortcuts
    connect(ui->actionJump_to_nearest_note,SIGNAL(triggered()),canvas,SLOT(jumpToNearestNote()));
    connect(ui->actionEdit_note,&QAction::triggered,edit_w,&EditNoteDialogue::editNote);
    connect(ui->actionNew_note,&QAction::triggered,edit_w,&EditNoteDialogue::newNote);
    connect(ui->actionNew_notefile,&QAction::triggered,this,&MisliWindow::newNoteFile);
    connect(ui->actionNext_notefile,&QAction::triggered,this,&MisliWindow::nextNoteFile);
    connect(ui->actionPrevious_notefile,&QAction::triggered,this,&MisliWindow::previousNoteFile);
    connect(ui->actionZoom_in,&QAction::triggered,this,&MisliWindow::zoomIn);
    connect(ui->actionZoom_out,&QAction::triggered,this,&MisliWindow::zoomOut);
    connect(ui->actionHelp,&QAction::triggered,this,&MisliWindow::toggleHelp);
    connect(ui->actionMake_this_notefile_appear_first_on_program_start,&QAction::triggered,this,&MisliWindow::makeNoteFileDefault);
    connect(ui->actionRemove_current,&QAction::triggered,this,&MisliWindow::removeCurrentFolder);
    connect(ui->actionTransparent_background,&QAction::triggered,this,&MisliWindow::colorTransparentBackground);
    connect(ui->actionDelete_notefile,&QAction::triggered,this,&MisliWindow::deleteNoteFileFromFS);
    connect(ui->jumpToNearestNotePushButton,&QPushButton::clicked,canvas,&Canvas::jumpToNearestNote);
    connect(ui->actionAdd_new,&QAction::triggered,this,&MisliWindow::addNewFolder);
    connect(ui->addMisliDirPushButton,&QPushButton::clicked,this,&MisliWindow::addNewFolder);
    connect(ui->menuFolders,&QMenu::triggered,this,&MisliWindow::handleFoldersMenuClick);
    connect(ui->menuSwitch_to_another_note_file,&QMenu::triggered,this,&MisliWindow::handleNoteFilesMenuClick);
    connect(ui->makeNoteFilePushButton,&QPushButton::clicked,this,&MisliWindow::newNoteFile);
    connect(ui->actionRename_notefile,&QAction::triggered,this,&MisliWindow::renameNoteFile);
    connect(ui->actionMake_this_view_point_default_for_the_notefile,&QAction::triggered,this,&MisliWindow::makeViewpointDefault);
    connect(ui->actionCopy,&QAction::triggered,this,&MisliWindow::copySelectedNotesToClipboard);
    connect(ui->actionPaste,&QAction::triggered,canvas,&Canvas::paste);

    //Download update action (lambda)
    connect(ui->actionDownload_it,&QAction::triggered,canvas,[&](){
        QDesktopServices::openUrl(QUrl("http://sourceforge.net/projects/misli/"));
    });

    //Delete selected (lambda)
    connect(ui->actionDelete_selected,&QAction::triggered,canvas,[&](){
        if(timelineTabIsActive()){
            timelineWidget.timeline->archiveModule.noteFile.deleteSelected();
        }else{
            canvas->noteFile()->deleteSelected();
        }
    });
    //Undo (lambda)
    connect(ui->actionUndo,&QAction::triggered,[&](){
        canvas->noteFile()->undo();
    });
    //Redo (lambda)
    connect(ui->actionRedo,&QAction::triggered,[&](){
        canvas->noteFile()->redo();
    });
    //Cut (lambda)
    connect(ui->actionCut,&QAction::triggered,[&](){
        copySelectedNotesToClipboard();
        canvas->noteFile()->deleteSelected();
    });
    //Paste note from clipboard
    connect(ui->actionCreate_note_from_the_clipboard_text,&QAction::triggered,[&](){
        if( canvas->mimeDataIsCompatible( misliDesktopGUI->clipboard()->mimeData() ) ){
                misliDesktopGUI->setOverrideCursor(Qt::WaitCursor);
                canvas->pasteMimeData(misliDesktopGUI->clipboard()->mimeData());
                misliDesktopGUI->restoreOverrideCursor();
        }
    });
    //Make link (lambda)
    connect(ui->actionMake_link,&QAction::triggered,[&](){
        canvas->setLinkingState(true);
    });
    //Make current view point height default (lambda)
    connect(ui->actionSet_this_height_as_default,&QAction::triggered,[&](){
        currentDir_m->setDefaultEyeZ(canvas->noteFile()->eyeZ);
        //pri load polzwaneto na stoinostta stava v MisliDir:: NoteFile
    });
    //Set language to Bulgarian (lambda)
    connect(ui->actionBulgarian,&QAction::triggered,[&](){
        misliDesktopGUI->setLanguage("bg");
    });
    //Set language to English (lambda)
    connect(ui->actionEnglish,&QAction::triggered,[&](){
        misliDesktopGUI->setLanguage("en");
    });
    //Color selected blue (lambda)
    connect(ui->actionColor_blue,&QAction::triggered,[&](){
        colorSelectedNotes(0,0,1,1,0,0,1,0.1);
    });
    //Color selected green (lambda)
    connect(ui->actionColor_green,&QAction::triggered,[&](){
        colorSelectedNotes(0,0.64,0.235,1,0,1,0,0.1);
    });
    //Color selected red (lambda)
    connect(ui->actionColor_red,&QAction::triggered,[&](){
        colorSelectedNotes(1,0,0,1,1,0,0,0.1);
    });
    //Color selected black (lambda)
    connect(ui->actionColor_black,&QAction::triggered,[&](){
        colorSelectedNotes(0,0,0,1,0,0,0,0.1);
    });
    //Move down (lambda)
    connect(ui->actionMove_down,&QAction::triggered,[&](){
        canvas->noteFile()->eyeY+=MOVE_SPEED;
        QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
        canvas->update();
    });
    //Move up (lambda)
    connect(ui->actionMove_up,&QAction::triggered,[&](){
        canvas->noteFile()->eyeY-=MOVE_SPEED;
        QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
        canvas->update();
    });
    //Move left (lambda)
    connect(ui->actionMove_left,&QAction::triggered,[&](){
        if(tabWidget.currentWidget()==canvas){
            canvas->noteFile()->eyeX-=MOVE_SPEED;
            QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
            canvas->update();
        }else if(tabWidget.currentWidget()==&timelineWidget){
            timelineWidget.timeline->positionInMSecs -= timelineWidget.timeline->viewportSizeInMSecs/60;
            timelineWidget.timeline->update();
        }

    });
    //Move right (lambda)
    connect(ui->actionMove_right,&QAction::triggered,[&](){
        if(tabWidget.currentWidget()==canvas){
            canvas->noteFile()->eyeX+=MOVE_SPEED;
            QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
            canvas->update();
        }else if(tabWidget.currentWidget()==&timelineWidget){
            timelineWidget.timeline->positionInMSecs += timelineWidget.timeline->viewportSizeInMSecs/60;
            timelineWidget.timeline->update();
        }
    });
    //Select all notes (lambda)
    connect(ui->actionSelect_all_notes,&QAction::triggered,[&](){
        canvas->noteFile()->selectAllNotes();
    });
    //Select all red notes (lambda)
    connect(ui->actionSelect_all_red_notes,&QAction::triggered,[&](){
        NoteFile *nf = canvas->noteFile();
        for(Note *nt: nf->notes){
            if(nt->textColor()==Qt::red){
                nt->setSelected(true);
            }
        }
    });
    //Instant search on typing in the searchLineEdit (lambda)
    connect(ui->searchLineEdit,&QLineEdit::textChanged,[&](QString text){
        notes_search->searchResults.clear();
        notes_search->findByText(text);
    });
    //Emulate left click on enter (return) press (lambda)
    connect(ui->actionSelect_note_under_mouse,&QAction::triggered,[&](){
        canvas->handleMousePress(Qt::LeftButton);
        canvas->handleMouseRelease(Qt::LeftButton);
    });
    //Show the About dialog (lambda)
    connect(ui->actionAbout,&QAction::triggered,[&](){
        QMessageBox::about(this,tr("Misli"),tr("Misli - an application for organizing thoughts and notes\n\nBugs, suggestions and everything else at:\nhttps://github.com/petko10/misli\nAuthor: Petko Ditchev\nContact: pditchev@gmail.com\nVersion: ")+misliDesktopGUI->applicationVersion());
    });
    //Copy BTC address (lambda)
    connect(ui->actionCopy_donation_address,&QAction::triggered,[&](){
        misliDesktopGUI->clipboard()->setText("185FzaDimiAXJXsGtwHKF8ArTwPjQt8zoi"); //should be more dynamic
    });

    //Handle misli dirs change(lambda)
    connect(misliDesktopGUI->misliInstance,&MisliInstance::misliDirsChanged,[&](){
        //Check if the current dir is removed
        if(!misliInstance()->misliDirs().contains(currentDir_m)){
            setCurrentDir(NULL); //Auto set dir
        }
        updateDirListMenu();
    });

    //Clear settings and exit (lambda)
    connect(ui->actionClear_settings_and_exit,&QAction::triggered,this,[&](){
        misliDesktopGUI->clearSettingsOnExit = true;
        misliDesktopGUI->exit(0);
    });

    //Switch to tab 1
    connect(ui->actionGotoTab1, &QAction::triggered, this, [&](){
        tabWidget.setCurrentIndex(0);
    });
    //Switch to tab 2
    connect(ui->actionGotoTab2, &QAction::triggered, this, [&](){
        tabWidget.setCurrentIndex(1);
    });

    //---------------------Creating the virtual note files----------------------
    clipboardNoteFile = new NoteFile;
    helpNoteFile = new NoteFile;
    helpNoteFile->setFilePath(":/help/help_"+misliDesktopGUI->language()+".misl");

    //Auto set current dir
    setCurrentDir(NULL);

    grabGesture(Qt::PinchGesture);

    //BRUTE FORCE BUG SQUASHING (graphics glitch in ui.tabWidget)
    tabWidget.setCurrentIndex(1);
    tabWidget.setCurrentIndex(0);
}

MisliWindow::~MisliWindow()
{
    delete ui;
    delete clipboardNoteFile;
    delete helpNoteFile;
    delete canvas;
    delete edit_w;
    delete notes_search;
}

bool MisliWindow::timelineTabIsActive()
{
    if(tabWidget.currentWidget()==&timelineWidget){
        return true;
    }else{
        return false;
    }
}
void MisliWindow::closeEvent(QCloseEvent *)
{
    misliDesktopGUI->setQuitOnLastWindowClosed(true);
}

MisliDir* MisliWindow::currentDir()
{
    return currentDir_m;
}
void MisliWindow::setCurrentDir(MisliDir* newDir)
{
    if(currentDir_m==newDir && newDir!=NULL) return;

    disconnect(nfChangedConnecton);
    currentDir_m = newDir;

    if(newDir!=NULL){
        nfChangedConnecton = connect(newDir,&MisliDir::noteFilesChanged,this,&MisliWindow::handleNoteFilesChange);
        ui->addMisliDirPushButton->hide();
        ui->makeNoteFilePushButton->setEnabled(true);

        canvas->setNoteFile(currentDir_m->currentNoteFile);
    }else{
        if(misliInstance()->misliDirs().isEmpty()){//If there are no dirs
            if(misliDesktopGUI->firstProgramStart()){
                misliInstance()->addDir(QStandardPaths::writableLocation(QStandardPaths::DataLocation));
                return;
            }else{ //We just leave currentDir and noteFile NULL
                ui->addMisliDirPushButton->show();
                ui->makeNoteFilePushButton->setEnabled(false);
                canvas->setNoteFile(NULL);
            }
        }else{ //Else just switch to the last
            setCurrentDir(misliInstance()->misliDirs().last());
            return;
        }
    }

    updateDirListMenu();
    emit currentDirChanged(newDir); //Shouldn't actually be used since all who care see each other
}

bool MisliWindow::event(QEvent *event)
{
    if (event->type() == QEvent::Gesture) {
        return gestureEvent(static_cast<QGestureEvent*>(event));
    }

    return QWidget::event(event);
}

bool MisliWindow::gestureEvent(QGestureEvent *event)
{
    //if (QGesture *swipe = event->gesture(Qt::SwipeGesture))
    //    swipeTriggered(static_cast<QSwipeGesture *>(swipe));
    //else if (QGesture *pan = event->gesture(Qt::PanGesture))
    //    panTriggered(static_cast<QPanGesture *>(pan));
    if (QGesture *pinch = event->gesture(Qt::PinchGesture))
        pinchTriggered(static_cast<QPinchGesture *>(pinch));
    return true;
}

void MisliWindow::pinchTriggered(QPinchGesture *gesture)
{
    canvas->noteFile()->eyeZ =  canvas->noteFile()->eyeZ/gesture->scaleFactor();
    canvas->update();
}

MisliInstance * MisliWindow::misliInstance()
{
    return misliDesktopGUI->misliInstance;
}

void MisliWindow::newNoteFromClipboard()
{
    edit_w->x_on_new_note=canvas->current_mouse_x; //cursor position relative to the gl widget
    edit_w->y_on_new_note=canvas->current_mouse_y;
    edit_w->edited_note=NULL;
    edit_w->setTextEditText( QApplication::clipboard()->text() );
    edit_w->inputDone();
}

void MisliWindow::newNoteFile()
{
    QString name = QInputDialog::getText(this,tr("Making a new notefile"),tr("Enter a name for the notefile:"));
    if(name.isEmpty()) return;

    if( currentDir_m->makeNotesFile( name ) != 0 ) {
        QMessageBox::warning(this,tr("Could not make the notefile"),tr("Error making notefile , exclude bad symbols from the name (; < >  ... )"));
        return;
    }else{
        currentDir_m->reinitNotesPointingToNotefiles();
        canvas->setNoteFile(currentDir_m->noteFiles_m.back());
    }
}
void MisliWindow::renameNoteFile()
{
    QString name = QInputDialog::getText(this,tr("Making a new notefile"),tr("Enter a name for the notefile:"));
    NoteFile * nf = canvas->noteFile();

    if(currentDir_m->noteFileByName(name)!=NULL){
        QMessageBox::warning(this,tr("Could not make the notefile"),tr("A notefile with this name exists."));
        return;
    }

    QString file_addr=QDir(currentDir_m->directoryPath()).filePath(name+".misl");
    QString old_name=nf->name();

    QFile file(nf->filePath_m);


    if( file.copy(file_addr) ){ //Copy to a nf with the new name
        currentDir_m->fs_watch->removePath(nf->filePath_m);//deal with fs_watch
        nf->filePath_m = file_addr;
        nf->save();
        nf->setFilePath(nf->filePath_m);
        file.remove();

        //Now change all the notes that point to this one too
        for(NoteFile *nf2: currentDir_m->noteFiles_m){
            for(Note *nt: nf2->notes){
                if(nt->type==NoteType::redirecting){
                    if(nt->textForDisplay_m==old_name){
                        nt->setText("this_note_points_to:"+name);
                    }
                }
            }
        }

    }else{
        misliDesktopGUI->showWarningMessage(tr("Error while renaming file."));
    }
}
void MisliWindow::deleteNoteFileFromFS()
{
    QDir dir(currentDir_m->directoryPath_m);

    //Warn the user
    int ret = QMessageBox::warning(this,tr("Warning"),tr("This will delete the note file permanetly!"),QMessageBox::Ok,QMessageBox::Cancel);
    //If the user confirms
    if(ret==QMessageBox::Ok){
        QString filePath = canvas->noteFile()->filePath_m; //It gets deleted with the soft delete
        currentDir_m->softDeleteNF(canvas->noteFile()); //Before the hard delete (fs_watch gets disabled there)
        if(!dir.remove(filePath)){
            QMessageBox::information(this,tr("FYI"),tr("Could not delete the file from the file system.Check your permissions."));
        }

    }
}
void MisliWindow::nextNoteFile()
{
    for(int i=0;i<(currentDir_m->noteFiles_m.size()-1);i++){ //for every notefile without the last one
        if( (canvas->noteFile()->name()==currentDir_m->noteFiles_m[i]->name()) ){
            canvas->setNoteFile(currentDir_m->noteFiles_m[i+1]);
            break;
        }
    }
}
void MisliWindow::previousNoteFile()
{
    for(int i=1;i<(currentDir_m->noteFiles_m.size());i++){ //for every notefile without the last one
        if( (canvas->noteFile()->name()==currentDir_m->noteFiles_m[i]->name()) ){
            canvas->setNoteFile(currentDir_m->noteFiles_m[i-1]);
            break;
        }
    }
}

void MisliWindow::zoomOut()
{
    canvas->noteFile()->eyeZ+=MOVE_SPEED;
    canvas->update();
}
void MisliWindow::zoomIn()
{
    canvas->noteFile()->eyeZ-=MOVE_SPEED;
    canvas->update();
}

void MisliWindow::toggleHelp()
{
    if(canvas->noteFile()!=helpNoteFile){
        nfBeforeHelp = canvas->noteFile();
        canvas->setNoteFile(helpNoteFile);
    }else{
        canvas->setNoteFile(nfBeforeHelp);
    }
}
void MisliWindow::makeViewpointDefault()
{
    canvas->noteFile()->makeCoordsRelativeTo(canvas->noteFile()->eyeX,canvas->noteFile()->eyeY);
    canvas->noteFile()->initLinks();
    canvas->noteFile()->eyeX=0;
    canvas->noteFile()->eyeY=0;
    canvas->noteFile()->save();
    canvas->update();
}
void MisliWindow::makeNoteFileDefault()
{
    for(NoteFile* nf: currentDir_m->noteFiles_m){
        if(nf==canvas->noteFile()){
            if(!nf->isDisplayedFirstOnStartup){
                nf->isDisplayedFirstOnStartup=true;
                nf->save();
            }
        }else{
            if(nf->isDisplayedFirstOnStartup){ //To avoid saving all of the notefiles
                nf->isDisplayedFirstOnStartup=false;
                nf->save();
            }
        }
    }
}
void MisliWindow::removeCurrentFolder()
{
    misliInstance()->removeDir(currentDir_m);
    if(misliInstance()->misliDirs().isEmpty()){
        setCurrentDir(NULL);
    }else{
        setCurrentDir(misliInstance()->misliDirs().last());
    }
}
void MisliWindow::updateTitle()
{
    QString title;

    //title=tr("Misli - ");
    if(canvas->noteFile()==NULL){
        title+=tr("No note files present");
    }else{
        title+=canvas->noteFile()->name();
        if(!canvas->noteFile()->isReadable){
            title+=tr("(file is not readable)");
        }
    }

    tabWidget.setTabText(tabWidget.indexOf(canvas), title);
}

void MisliWindow::colorSelectedNotes(float txtR, float txtG, float txtB, float txtA, float backgroundR, float backgroundG, float backgroundB, float backgroundA)
{
    Note *nt;
    while(canvas->noteFile()->getFirstSelectedNote()!=NULL){
        nt=canvas->noteFile()->getFirstSelectedNote();

        QColor textColor,bgColor;
        textColor.setRgbF(txtR,txtG,txtB,txtA);
        bgColor.setRgbF(backgroundR,backgroundG,backgroundB,backgroundA);
        nt->setColors(textColor,bgColor);

        nt->setSelected(false);
    }
}

void MisliWindow::colorTransparentBackground()
{
    Note *nt;
    while(canvas->noteFile()->getFirstSelectedNote()!=NULL){
        nt=canvas->noteFile()->getFirstSelectedNote();

        nt->setColors(nt->textColor(),QColor(0,0,0,0));
        nt->setSelected(false);
    }
}

void MisliWindow::updateNoteFilesListMenu()
{
    ui->menuSwitch_to_another_note_file->clear();
    if(currentDir_m==NULL) return;
    for(NoteFile *nf: currentDir_m->noteFiles_m){
        QAction *action = ui->menuSwitch_to_another_note_file->addAction(nf->name());
        action->setCheckable(true);
        if(nf==canvas->noteFile()) action->setChecked(true);
    }
}
void MisliWindow::updateDirListMenu()
{
    //Clear the old list
    while(ui->menuFolders->actions().size()>2){ //Until the only actions left are the add/remove buttons
        //Remove the last action
        ui->menuFolders->removeAction(ui->menuFolders->actions().at(ui->menuFolders->actions().size()-1));
    }

    //Make the new one
    for(MisliDir* misliDir: misliInstance()->misliDirs()){
        QAction *action = ui->menuFolders->addAction(misliDir->directoryPath());
        action->setCheckable(true);
        if(misliDir==currentDir_m) action->setChecked(true);
    }
}

void MisliWindow::copySelectedNotesToClipboard() //It's not a lambda because it's used also in cut, and other
{
    //Avoid clearing the clipboard when there's nothing selected for copy
    if(canvas->noteFile()->getFirstSelectedNote()==NULL) return;

    //Clear the clipboard note file
    clipboardNoteFile->selectAllNotes();
    clipboardNoteFile->deleteSelected();

    QString clipText = canvas->copySelectedNotes(canvas->noteFile(),clipboardNoteFile);

    //Get the number of selected notes
    int selectedNotesCount = 0;
    for(Note *note: canvas->noteFile()->notes){
        if(note->isSelected()) selectedNotesCount++;
    }

    //Prepare the coordinates for pasting
    //If there is only one note - center it in the clipboard nf , so it pastes on the mouse
    if(selectedNotesCount==1){
        clipboardNoteFile->makeCoordsRelativeTo(canvas->noteFile()->getFirstSelectedNote()->rect().x(), canvas->noteFile()->getFirstSelectedNote()->rect().y());
    }else{//If there are more - keep the coordinates relative to the mouse
        clipboardNoteFile->makeCoordsRelativeTo(canvas->unprojectX(canvas->current_mouse_x), canvas->unprojectY(canvas->current_mouse_y));
    }

    //Copy all the notes' text to the OS clipboard
    if(!clipText.isEmpty()) misliDesktopGUI->clipboard()->setText(clipText.trimmed());
}

void MisliWindow::addNewFolder()
{
    QString path = QFileDialog::getExistingDirectory(this,"Choose a directory with Misli notes");

    if( !path.isEmpty() ){ //if the dir is non existent or inaccessible cd returns false
        misliDesktopGUI->setOverrideCursor(Qt::WaitCursor);
        setCurrentDir( misliInstance()->addDir(path) );
        misliDesktopGUI->restoreOverrideCursor();
    }
}

void MisliWindow::handleNoteFilesChange()
{
    canvas->setNoteFile(currentDir_m->currentNoteFile);
}

void MisliWindow::handleFoldersMenuClick(QAction *action)
{
    //Check if the click is on the add/remove buttons
    if( (action==ui->actionAdd_new) | (action==ui->actionRemove_current)){
        return;
    }

    //Set the dir
    for(MisliDir *misliDir: misliInstance()->misliDirs()){
            if(misliDir->directoryPath()==action->text()) setCurrentDir(misliDir);
    }
}
void MisliWindow::handleNoteFilesMenuClick(QAction *action)
{
    for(NoteFile *nf: currentDir_m->noteFiles()){
        if(nf->name()==action->text()){
            canvas->setNoteFile(nf);
            return;
        }
    }
}
void MisliWindow::startUpdateCheck()
{
    if(updateCheckDone) return;

    if(ui->actionCheck_for_updates->isChecked()){
        network.get(QNetworkRequest(QUrl("http://misli-web.appspot.com/current_version_info.xml")));
    }
}
void MisliWindow::handleVersionInfoReply(QNetworkReply *reply)
{
    QString replyData = reply->readAll();
    QDomDocument info;
    info.setContent(replyData);

    QString version = info.firstChildElement("info").firstChildElement("version").text();
    if( q_version_string_to_number(version)>q_version_string_to_number(misliDesktopGUI->applicationVersion())){
        ui->menubar->addMenu(&updateMenu);
    }
    updateCheckDone = true;
}
