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
#include <QComboBox>
#include <QListView>

#ifdef Q_OS_ANDROID
#include <QtAndroidExtras/QtAndroid>
#endif

#include "misliwindow.h"
#include "../misliinstance.h"

#include "editnotedialogue.h"
#include "../canvas.h"
#include "mislidesktopgui.h"

MisliWindow::MisliWindow(MisliDesktopGui * misli_dg_):
    ui(new Ui::MisliWindow),
    timelineWidget(this),
    updateMenu(tr("Update available"))
{
    ui->setupUi(this);
    setWindowIcon(QIcon(":/img/icon.png"));

    misliDesktopGUI = misli_dg_;
    nfBeforeHelp = nullptr;
    updateCheckDone = false;

    //---Init notes search stuff---
    notes_search = new NotesSearch(this, 1);
    notes_search->moveToThread(&misliDesktopGUI->workerThread);
    notes_search->loadNotes();
    ui->searchListView->setModel(notes_search);
    QItemSelectionModel *selectionModel = ui->searchListView->selectionModel();
    //Handle search result selection (lambda)
    connect(selectionModel, &QItemSelectionModel::selectionChanged, this,
            [&](const QItemSelection &, const QItemSelection &){
        const QModelIndex index = ui->searchListView->selectionModel()->currentIndex();
        NotesSearch::SearchItem searchItem = notes_search->searchResults.at(index.row());
        //Set the last noteFile for the Back function if appropriate
        //if( (searchItem.md==currentDir()) && (searchItem.nf!=canvas->noteFile()) ){

        //}
        currentCanvas()->setCurrentDir(searchItem.md);
        currentCanvas_m->setNoteFile(searchItem.nf);
        if(searchItem.nf->notes.contains(searchItem.nt)){
            currentCanvas_m->centerEyeOnNote(searchItem.nt);
            ui->searchListView->clearSelection();
        }else{//If the note was deleted
            notes_search->findByText(ui->searchLineEdit->text());
        }
    });
    //Add combobox items for the search scopes
    ui->searchScopeComboBox->addItem(tr("all notes"));
    ui->searchScopeComboBox->addItem(tr("the current dir"));
    ui->searchScopeComboBox->addItem(tr("the current note file"));
    ui->searchScopeComboBox->setCurrentIndex(1);
    connect(ui->searchScopeComboBox,static_cast<void(QComboBox::*)(int)>(&QComboBox::currentIndexChanged), [&](){
        notes_search->findByText(ui->searchLineEdit->text());
    });

    //---Init widgets and widnows---
    ui->mainLayout->addWidget(ui->tabWidget);
    edit_w = new EditNoteDialogue(this);
    Canvas *cv = new Canvas(this);
    currentCanvas_m = cv;
    qDebug()<<"ADDING TAB";
    ui->tabWidget->addTab(cv, "");
    Canvas * cv1 = dynamic_cast<Canvas*>(ui->tabWidget->currentWidget());
    if ( cv1 == cv ){
        qDebug()<<"SUCCESS";
    }else{
        qDebug()<<"FAIL";
    }
    ui->tabWidget->addTab(&timelineWidget,"/timeline(beta)");
    ui->searchLineEdit->hide();
    ui->searchListView->hide();
    ui->searchScopeComboBox->hide();
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
    connect(ui->actionJump_to_nearest_note,SIGNAL(triggered()),currentCanvas_m,SLOT(jumpToNearestNote()));
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
    connect(ui->jumpToNearestNotePushButton,&QPushButton::clicked,currentCanvas_m,&Canvas::jumpToNearestNote);
    connect(ui->actionAdd_new,&QAction::triggered,this,&MisliWindow::addNewFolder);
    connect(ui->addMisliDirPushButton,&QPushButton::clicked,this,&MisliWindow::addNewFolder);
    connect(ui->menuFolders,&QMenu::triggered,this,&MisliWindow::handleFoldersMenuClick);
    connect(ui->menuSwitch_to_another_note_file,&QMenu::triggered,this,&MisliWindow::handleNoteFilesMenuClick);
    connect(ui->makeNoteFilePushButton,&QPushButton::clicked,this,&MisliWindow::newNoteFile);
    connect(ui->actionRename_notefile,&QAction::triggered,this,&MisliWindow::renameNoteFile);
    connect(ui->actionMake_this_view_point_default_for_the_notefile,&QAction::triggered,this,&MisliWindow::makeViewpointDefault);
    connect(ui->actionCopy,&QAction::triggered,this,&MisliWindow::copySelectedNotesToClipboard);
    connect(ui->actionPaste,&QAction::triggered,currentCanvas_m,&Canvas::paste);

    //Download update action (lambda)
    connect(ui->actionDownload_it,&QAction::triggered,currentCanvas_m,[&](){
        QDesktopServices::openUrl(QUrl("http://sourceforge.net/projects/misli/"));
    });

    //Delete selected (lambda)
    connect(ui->actionDelete_selected,&QAction::triggered,currentCanvas_m,[&](){
        if(timelineTabIsActive()){
            timelineWidget.timeline->archiveModule.noteFile.deleteSelected();
        }else{
            currentCanvas_m->noteFile()->deleteSelected();
        }
    });
    //Undo (lambda)
    connect(ui->actionUndo,&QAction::triggered,[&](){
        currentCanvas_m->noteFile()->undo();
    });
    //Redo (lambda)
    connect(ui->actionRedo,&QAction::triggered,[&](){
        currentCanvas_m->noteFile()->redo();
    });
    //Cut (lambda)
    connect(ui->actionCut,&QAction::triggered,[&](){
        copySelectedNotesToClipboard();
        currentCanvas_m->noteFile()->deleteSelected();
    });
    //Paste note from clipboard
    connect(ui->actionCreate_note_from_the_clipboard_text,&QAction::triggered,[&](){
        if( currentCanvas_m->mimeDataIsCompatible( misliDesktopGUI->clipboard()->mimeData() ) ){
                misliDesktopGUI->setOverrideCursor(Qt::WaitCursor);
                currentCanvas_m->pasteMimeData(misliDesktopGUI->clipboard()->mimeData());
                misliDesktopGUI->restoreOverrideCursor();
        }
    });
    //Make link (lambda)
    connect(ui->actionMake_link,&QAction::triggered,[&](){
        if(currentCanvas_m->noteFile()->getFirstSelectedNote()!=nullptr){
            currentCanvas_m->linkingIsOn = true;
            currentCanvas_m->update();
        }
    });
    //Make current view point height default (lambda)
    connect(ui->actionSet_this_height_as_default,&QAction::triggered,[&](){
        currentDir()->setDefaultEyeZ(currentCanvas_m->noteFile()->eyeZ);
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
        currentCanvas_m->noteFile()->eyeY+=MOVE_SPEED;
        QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
        currentCanvas_m->update();
    });
    //Move up (lambda)
    connect(ui->actionMove_up,&QAction::triggered,[&](){
        currentCanvas_m->noteFile()->eyeY-=MOVE_SPEED;
        QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
        currentCanvas_m->update();
    });
    //Move left (lambda)
    connect(ui->actionMove_left,&QAction::triggered,[&](){
        if(ui->tabWidget->currentWidget()==currentCanvas_m){
            currentCanvas_m->noteFile()->eyeX-=MOVE_SPEED;
            QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
            currentCanvas_m->update();
        }else if(ui->tabWidget->currentWidget()==&timelineWidget){
            timelineWidget.timeline->positionInMSecs -= timelineWidget.timeline->viewportSizeInMSecs/60;
            timelineWidget.timeline->update();
        }

    });
    //Move right (lambda)
    connect(ui->actionMove_right,&QAction::triggered,[&](){
        if(ui->tabWidget->currentWidget()==currentCanvas_m){
            currentCanvas_m->noteFile()->eyeX+=MOVE_SPEED;
            QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
            currentCanvas_m->update();
        }else if(ui->tabWidget->currentWidget()==&timelineWidget){
            timelineWidget.timeline->positionInMSecs += timelineWidget.timeline->viewportSizeInMSecs/60;
            timelineWidget.timeline->update();
        }
    });
    //Select all notes (lambda)
    connect(ui->actionSelect_all_notes,&QAction::triggered,[&](){
        currentCanvas_m->noteFile()->selectAllNotes();
    });
    //Select all red notes (lambda)
    connect(ui->actionSelect_all_red_notes,&QAction::triggered,[&](){
        NoteFile *nf = currentCanvas_m->noteFile();
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
        currentCanvas_m->handleMousePress(Qt::LeftButton);
        currentCanvas_m->handleMouseRelease(Qt::LeftButton);
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
        if(!misliInstance()->misliDirs().contains(currentDir())){
            currentCanvas()->setCurrentDir(nullptr); //Auto set dir
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
        ui->tabWidget->setCurrentIndex(0);
    });
    //Switch to tab 2
    connect(ui->actionGotoTab2, &QAction::triggered, this, [&](){
        ui->tabWidget->setCurrentIndex(1);
    });
    //Switch to the last note file
    connect(ui->actionSwitch_to_the_last_note_file, &QAction::triggered, [&](){
        if(currentCanvas()->lastNoteFile!=nullptr) currentCanvas()->setNoteFile(currentCanvas()->lastNoteFile);
    });
    //Export notes as web pages (lambda)
    connect(ui->actionExport_all_as_web_notes,&QAction::triggered,[&](){
        QDir webDir(currentDir()->folderPath+"/web");
        if(!webDir.exists()) webDir.mkpath(webDir.absolutePath());

        QImage img(1000,1000, QImage::Format_ARGB32);//hacky workaround to get the text length adjust
        QPainter p(&img);

        QFile jsFile(":/misli_web/static/misli.js"), styleFile(":/misli_web/static/style.css");
        if(!jsFile.open(QIODevice::ReadOnly)) qDebug("Could not load misli.js resource");
        if(!styleFile.open(QIODevice::ReadOnly)) qDebug("Could not load misli.js resource");
        QString jsContents = jsFile.readAll(), styleContents = styleFile.readAll();
        jsFile.close();
        styleFile.close();

        for(NoteFile *nf: currentDir()->noteFiles()){
            QFile file(webDir.absoluteFilePath(nf->name()+".html"));
            file.open(QIODevice::WriteOnly);
            QTextStream stream(&file);
            stream<<"<!DOCTYPE html>\n"
                    "<html>\n"
                    "    <head>\n"
                    "        <style>\n";
                    //"        <link rel='stylesheet' href='static/style.css'>\n"
            stream<<styleContents;
            stream<<"        </style>\n"
                    "    </head>\n"
                    "<body style=\"overflow: hidden\">\n"
                    "\t<canvas id=\"misliCanvas\">Your browser does not support the HTML5 canvas tag.</canvas>\n"
                    "\t<!-- GENERATED -->\n";
            for(Note *nt: nf->notes){

                if(!nt->tags.contains("for_export_v1")) continue;

                nt->checkForDefinitions();
                nt->drawNote(p); //hacky workaround to get the text length adjust
                stream<<"\t<a";
                //Specify link address if the note redirects
                if(nt->type==NoteType::webPage){
                    stream<<" href=\""+nt->addressString+"\"";
                }
                stream<<" class=\"note\" id=\""<<"n"<<nt->id<<"\" style=\"";
                //Specify background color
                if(nt->backgroundColor()!=QColor::fromRgbF(0,0,1,0.1)){
                    stream<<"background-color: rgba("<<nt->backgroundColor().red()<<","<<nt->backgroundColor().green()<<","<<nt->backgroundColor().blue()<<","<<nt->backgroundColor().alphaF()<<");";
                }
                //Specify text color
                if(nt->backgroundColor()!=QColor::fromRgbF(0,0,1,1)){
                    stream<<"color: rgba("<<nt->textColor().red()<<","<<nt->textColor().green()<<","<<nt->textColor().blue()<<","<<nt->textColor().alphaF()<<");";
                }
                //Specify border
                if( (nt->type==NoteType::redirecting) | (nt->type==NoteType::webPage) ){
                    stream<<"border: 1px solid rgba("<<nt->textColor().red()<<","<<nt->textColor().green()<<","<<nt->textColor().blue()<<","<<nt->textColor().alphaF()<<");";
                }
                //Close off
                stream<<"\">"<<nt->textForDisplay()<<"</a>\n";
            }

            //stream<<"<script type='text/javascript' src='static/misli.js' ></script>\n"
            stream<<"\n<script>\n";
            stream<<jsContents;
            stream<<"\t//GENERATED\n";
            for(Note *nt: nf->notes){
                if(!nt->tags.contains("for_export_v1")) continue;
                stream<<"\tnewNote("<<"\"n"<<nt->id<<"\","<<nt->rect().left()<<","<<nt->rect().top()<<","<<nt->rect().width()<<","<<nt->rect().height()<<","<<nt->fontSize<<");\n";
                for(Link ln: nt->outlinks){
                    stream<<"\tnewLink("<<ln.line.x1()<<","<<ln.line.y1()<<","<<ln.line.x2()<<","<<ln.line.y2()<<");\n";
                }
            }

            stream<<"updateCanvas();"
                    "</script>\n"
                    "\n"
                    "</body>\n"
                    "</html>";

            stream.flush();
            file.close();
        }
    });
    //Toggle the tags view (handled mostly in Canvas::paintEvent()
    connect(ui->actionToggle_tags_view, &QAction::toggled, [&](){
        currentCanvas_m->update();
    });
    //Tag the selected notes
    connect(ui->actionToggle_tag, &QAction::triggered, [&](){
        int tagsChanged = 0;
        for(Note * nt: currentCanvas_m->noteFile()->notes){
            if(nt->isSelected()){
                tagsChanged++;
                if(nt->tags.contains("for_export_v1")){
                    nt->tags.removeOne("for_export_v1");
                }else{
                    nt->tags.append("for_export_v1");
                }
            }
        }
        if(tagsChanged>0) currentCanvas()->currentNoteFile->save();
    });
   /* // Migrate to JSON
    connect(ui->actionMigrate_to_JSON_format, &QAction::triggered, [&](){
        use_json = true;

        for(auto md: misliInstance()->misliDirs()){
            for(auto nf: md->noteFiles()){
                nf->save();
            }
        }
    });*/

    //---------------------Creating the virtual note files----------------------
    clipboardNoteFile = new NoteFile;
    clipboardNoteFile->filePath_m = "clipboardNoteFile";
    helpNoteFile = new NoteFile;
    helpNoteFile->setPathAndLoad(":/help/help_"+misliDesktopGUI->language()+".misl");

    //Add Android permission request
    #ifdef Q_OS_ANDROID
    qDebug()<<"Checking permission";
    QtAndroid::PermissionResult r = QtAndroid::checkPermission("android.permission.WRITE_EXTERNAL_STORAGE");
    if(r == QtAndroid::PermissionResult::Denied) {
        qDebug()<<"Permission denied, requesting from user.";
        QtAndroid::requestPermissionsSync( QStringList() << "android.permission.WRITE_EXTERNAL_STORAGE" );
        r = QtAndroid::checkPermission("android.permission.WRITE_EXTERNAL_STORAGE");
        if(r == QtAndroid::PermissionResult::Denied) {
             qDebug()<<"Permission denied for external storage";
        }
    }else{
        qDebug()<<"Permission granted";
    }
    #endif

    grabGesture(Qt::PinchGesture);

    //BRUTE FORCE BUG SQUASHING (graphics glitch in ui.tabWidget)
    ui->tabWidget->setCurrentIndex(1);
    ui->tabWidget->setCurrentIndex(0);
}

MisliWindow::~MisliWindow()
{
    delete ui;
    delete clipboardNoteFile;
    delete helpNoteFile;
    delete currentCanvas_m;
    delete edit_w;
    delete notes_search;
}

bool MisliWindow::timelineTabIsActive()
{
    if(ui->tabWidget->currentWidget()==&timelineWidget){
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
    return currentCanvas()->currentDir();
}


bool MisliWindow::event(QEvent *event)
{
    if (event->type() == QEvent::Gesture) {
        return gestureEvent(static_cast<QGestureEvent*>(event));
    }

    return QWidget::event(event);
}

void MisliWindow::keyPressEvent(QKeyEvent *event)
{
    QWidget::keyPressEvent(event);
    if(event->modifiers() & Qt::ControlModifier){
        currentCanvas_m->ctrlUpdateHack=true;
    }

    update();
}
void MisliWindow::keyReleaseEvent(QKeyEvent *event)
{
    QWidget::keyReleaseEvent(event);
    currentCanvas_m->ctrlUpdateHack=false;
    update();
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
    currentCanvas_m->noteFile()->eyeZ =  currentCanvas_m->noteFile()->eyeZ/gesture->scaleFactor();
    currentCanvas_m->update();
}

MisliInstance * MisliWindow::misliInstance()
{
    return misliDesktopGUI->misliInstance;
}

void MisliWindow::newNoteFromClipboard()
{
    edit_w->x_on_new_note=currentCanvas_m->mousePos().x(); //cursor position relative to the gl widget
    edit_w->y_on_new_note=currentCanvas_m->mousePos().y();
    edit_w->edited_note=nullptr;
    edit_w->setTextEditText( QApplication::clipboard()->text() );
    edit_w->inputDone();
}

void MisliWindow::newNoteFile()
{
    QString name = QInputDialog::getText(this,tr("Making a new notefile"),tr("Enter a name for the notefile:"));
    if(name.isEmpty()) return;


    int ret = currentDir()->makeNotesFile( name );
    if(  ret != 0 ) {
        QMessageBox::warning(this,tr("Could not make the notefile"),tr("Error making notefile , exclude bad symbols from the name (; < >  ... )"));
        return;
    }

    currentDir()->reinitNotesPointingToNotefiles();

    //Add a link in the current nf that points to the new nf
    NoteFile *newNF = currentDir()->noteFiles_m.back();
    Note *new_note = new Note(currentCanvas()->currentNoteFile->getNewId(), "this_note_points_to:" + newNF->name());
    new_note->setRect(QRectF(currentCanvas_m->unproject(currentCanvas_m->mousePos()), QSizeF(4, 2)));
    new_note->requestAutoSize = true;
    currentCanvas()->currentNoteFile->addNote(new_note);

    //Add a link in the new nf to the parent nf
    new_note = new Note(currentCanvas()->currentNoteFile->getNewId(), "this_note_points_to:" + currentCanvas()->currentNoteFile->name());
    new_note->setRect(QRectF(0, 0, 1, 1));
    new_note->requestAutoSize = true;

    currentCanvas_m->setNoteFile(newNF);
    newNF->addNote(new_note);
}
void MisliWindow::renameNoteFile()
{
    QString name = QInputDialog::getText(this,tr("Making a new notefile"),tr("Enter a name for the notefile:"));
    NoteFile * nf = currentCanvas_m->noteFile();

    if(currentDir()->noteFileByName(name)!=nullptr){
        QMessageBox::warning(this,tr("Could not make the notefile"),tr("A notefile with this name exists."));
        return;
    }

//    if(use_json){
//        name = name + ".json";
//    }else{
//        name = name + ".misl";
//    }

    QString file_addr=QDir(currentDir()->folderPath).filePath(name);
    QString old_name=nf->name();

    QFile file(nf->filePath());


    if( file.copy(file_addr) ){ //Copy to a nf with the new name
        currentDir()->fs_watch->removePath(nf->filePath());//deal with fs_watch
        nf->filePath_m = file_addr;
        nf->save();
        nf->setPathAndLoad(nf->filePath());
        file.remove();

        //Now change all the notes that point to this one too
        for(NoteFile *nf2: currentDir()->noteFiles_m){
            for(Note *nt: nf2->notes){
                if(nt->type==NoteType::redirecting){
                    if(nt->textForDisplay_m==old_name){
                        nt->changeText("this_note_points_to:"+name);
                    }
                }
            }
        }

        currentCanvas_m->setNoteFile(nf);
    }else{
        misliDesktopGUI->showWarningMessage(tr("Error while renaming file."));
    }
}
void MisliWindow::deleteNoteFileFromFS()
{
    QDir dir(currentDir()->folderPath);

    //Warn the user
    int ret = QMessageBox::warning(this,tr("Warning"),tr("This will delete the note file permanetly!"),QMessageBox::Ok,QMessageBox::Cancel);
    //If the user confirms
    if(ret==QMessageBox::Ok){
        QString filePath = currentCanvas_m->noteFile()->filePath(); //It gets deleted with the soft delete
        currentDir()->softDeleteNF(currentCanvas_m->noteFile()); //Before the hard delete (fs_watch gets disabled there)
        if(!dir.remove(filePath)){
            QMessageBox::information(this,tr("FYI"),tr("Could not delete the file from the file system.Check your permissions."));
        }

    }
}
void MisliWindow::nextNoteFile()
{
    for(int i=0;i<(currentDir()->noteFiles_m.size()-1);i++){ //for every notefile without the last one
        if( (currentCanvas_m->noteFile()->name()==currentDir()->noteFiles_m[i]->name()) ){
            currentCanvas_m->setNoteFile(currentDir()->noteFiles_m[i+1]);
            break;
        }
    }
}
void MisliWindow::previousNoteFile()
{
    for(int i=1;i<(currentDir()->noteFiles_m.size());i++){ //for every notefile without the last one
        if( (currentCanvas_m->noteFile()->name()==currentDir()->noteFiles_m[i]->name()) ){
            currentCanvas_m->setNoteFile(currentDir()->noteFiles_m[i-1]);
            break;
        }
    }
}

void MisliWindow::zoomOut()
{
    currentCanvas_m->noteFile()->eyeZ+=MOVE_SPEED;
    currentCanvas_m->update();
}
void MisliWindow::zoomIn()
{
    currentCanvas_m->noteFile()->eyeZ-=MOVE_SPEED;
    currentCanvas_m->update();
}

void MisliWindow::toggleHelp()
{
    if(currentCanvas_m->noteFile()!=helpNoteFile){
        nfBeforeHelp = currentCanvas_m->noteFile();
        currentCanvas_m->setNoteFile(helpNoteFile);
    }else{
        currentCanvas_m->setNoteFile(nfBeforeHelp);
    }
}
void MisliWindow::makeViewpointDefault()
{
    currentCanvas_m->noteFile()->makeCoordsRelativeTo(currentCanvas_m->noteFile()->eyeX,currentCanvas_m->noteFile()->eyeY);
    currentCanvas_m->noteFile()->arrangeLinksGeometry();
    currentCanvas_m->noteFile()->eyeX=0;
    currentCanvas_m->noteFile()->eyeY=0;
    currentCanvas_m->noteFile()->save();
    currentCanvas_m->update();
}
void MisliWindow::makeNoteFileDefault()
{
    for(NoteFile* nf: currentDir()->noteFiles_m){
        if(nf==currentCanvas_m->noteFile()){
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
    misliInstance()->removeDir(currentDir());
    if(misliInstance()->misliDirs().isEmpty()){
        currentCanvas()->setCurrentDir(nullptr);
    }else{
        currentCanvas()->setCurrentDir(misliInstance()->misliDirs().last());
    }
}
void MisliWindow::updateTitle()
{
    QString title;

    //title=tr("Misli - ");
    if(currentCanvas_m->noteFile()==nullptr){
        title+=tr("No note files present");
    }else{
        title += currentCanvas_m->noteFile()->name();
        if(!currentCanvas_m->noteFile()->isReadable){
            title+=tr("(file is not readable)");
        }
    }

    ui->tabWidget->setTabText(ui->tabWidget->indexOf(currentCanvas_m), title);
}

void MisliWindow::colorSelectedNotes(float txtR, float txtG, float txtB, float txtA, float backgroundR, float backgroundG, float backgroundB, float backgroundA)
{
    Note *nt;
    while(currentCanvas_m->noteFile()->getFirstSelectedNote()!=nullptr){
        nt=currentCanvas_m->noteFile()->getFirstSelectedNote();

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
    while(currentCanvas_m->noteFile()->getFirstSelectedNote()!=nullptr){
        nt=currentCanvas_m->noteFile()->getFirstSelectedNote();

        nt->setColors(nt->textColor(),QColor(0,0,0,0));
        nt->setSelected(false);
    }
}

void MisliWindow::updateNoteFilesListMenu()
{
    ui->menuSwitch_to_another_note_file->clear();
    if(currentDir()==nullptr) return;
    for(NoteFile *nf: currentDir()->noteFiles_m){
        QAction *action = ui->menuSwitch_to_another_note_file->addAction(nf->name());
        action->setCheckable(true);
        if(nf==currentCanvas_m->noteFile()) action->setChecked(true);
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
        QAction *action = ui->menuFolders->addAction(misliDir->folderPath);
        action->setCheckable(true);
        if(misliDir==currentDir()) action->setChecked(true);
    }
}

void MisliWindow::copySelectedNotesToClipboard() //It's not a lambda because it's used also in cut, and other
{
    //Avoid clearing the clipboard when there's nothing selected for copy
    if(currentCanvas_m->noteFile()->getFirstSelectedNote()==nullptr) return;

    //Clear the clipboard note file
    clipboardNoteFile->selectAllNotes();
    clipboardNoteFile->deleteSelected();

    QString clipText = currentCanvas_m->copySelectedNotes(currentCanvas_m->noteFile(),clipboardNoteFile);

    //Get the number of selected notes
    int selectedNotesCount = 0;
    for(Note *note: currentCanvas_m->noteFile()->notes){
        if(note->isSelected()) selectedNotesCount++;
    }

    //Prepare the coordinates for pasting
    //If there is only one note - center it in the clipboard nf , so it pastes on the mouse
    if(selectedNotesCount==1){
        QPointF p = currentCanvas_m->noteFile()->getFirstSelectedNote()->rect().topLeft();
        clipboardNoteFile->makeCoordsRelativeTo(p.x(), p.y());
    }else{//If there are more - keep the coordinates relative to the mouse
        QPointF p = currentCanvas_m->unproject(currentCanvas_m->mousePos());
        clipboardNoteFile->makeCoordsRelativeTo(p.x(), p.y());
    }

    //Copy all the notes' text to the OS clipboard
    if(!clipText.isEmpty()) misliDesktopGUI->clipboard()->setText(clipText.trimmed());
}

void MisliWindow::addNewFolder()
{
    QString path = QFileDialog::getExistingDirectory(this,"Choose a directory with Misli notes");

    if( !path.isEmpty() ){ //if the dir is non existent or inaccessible cd returns false
        misliDesktopGUI->setOverrideCursor(Qt::WaitCursor);
        currentCanvas()->setCurrentDir( misliInstance()->addDir(path) );
        misliDesktopGUI->restoreOverrideCursor();
    }
}

void MisliWindow::handleNoteFilesChange()
{
    currentCanvas_m->setNoteFile(currentCanvas()->currentNoteFile);
}

void MisliWindow::handleFoldersMenuClick(QAction *action)
{
    //Check if the click is on the add/remove buttons
    if( (action==ui->actionAdd_new) | (action==ui->actionRemove_current)){
        return;
    }

    //Set the dir
    for(MisliDir *misliDir: misliInstance()->misliDirs()){
            if(misliDir->folderPath==action->text()) currentCanvas()->setCurrentDir(misliDir);
    }
}
void MisliWindow::handleNoteFilesMenuClick(QAction *action)
{
    for(NoteFile *nf: currentDir()->noteFiles()){
        if(nf->name()==action->text()){
            currentCanvas_m->setNoteFile(nf);
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
    //FIXME handle failed connections
    QString replyData = reply->readAll();
    QDomDocument info;
    info.setContent(replyData);

    QString version = info.firstChildElement("info").firstChildElement("version").text();
    if( q_version_string_to_number(version)>q_version_string_to_number(misliDesktopGUI->applicationVersion())){
        ui->menubar->addMenu(&updateMenu);
    }
    updateCheckDone = true;
}
Canvas * MisliWindow::currentCanvas(){
    return currentCanvas_m;
}
void MisliWindow::on_tabWidget_currentChanged(int index)
{
    QWidget *cw = ui->tabWidget->currentWidget();
    Canvas *cv = dynamic_cast<Canvas*>(cw);
    if(cv != nullptr) {
        qDebug()<<"TEST COMPLETED";
        currentCanvas_m = cv;
    }else{
        qDebug()<<"ERROR ON CHANGING CURRENT CANVAS. TODO : REVIEW THIS CODE";
        return;
    }

    currentCanvas()->setCurrentDir(nullptr); //Auto set current dir

    updateTitle();
}

void MisliWindow::on_tabWidget_tabBarClicked(int index)
{

}
