/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "misliwindow.h"
#include "misliinstance.h"
#include "ui_misliwindow.h"

#include "newnfdialogue.h"
#include "editnotedialogue.h"
#include "getdirdialogue.h"
#include "canvas.h"
#include "mislidesktopgui.h"

MisliWindow::MisliWindow(MisliDesktopGui * misli_dg_):
    ui(new Ui::MisliWindow)
{
    misli_dg = misli_dg_;
    
    ui->setupUi(this);
    past_initial_load=false;
    doing_cut_paste=false;

    canvas = new Canvas(this);
    setCentralWidget(canvas);
    canvas->update();//if the first paint isn't called before the texture init for the texts there's a bug with the textures

    setWindowTitle("Loading notefiles...");
    setWindowIcon(QIcon(":/img/icon.png"));

    /*QKeySequence sq1(Qt::Key_Plus);
     QAction *newAct = new QAction(tr("&Nextnff"), this);
     newAct->setShortcut(sq1);
     newAct->setStatusTip(tr("Create a new file"));
     connect(newAct, SIGNAL(triggered()), this, SLOT(next_nf()));
*/
    //Connect signals/slots
    connect(ui->actionSearch,SIGNAL(triggered()),canvas->searchField,SLOT(show()));
    connect(ui->actionSearch,SIGNAL(triggered()),canvas->searchField,SLOT(setFocus()));
    connect(canvas->searchField,SIGNAL(editingFinished()),canvas->searchField,SLOT(hide()));
    connect(canvas->searchField,SIGNAL(editingFinished()),this,SLOT(hide_search_stuff()));
    connect(canvas->searchField,SIGNAL(textChanged(QString)),this,SLOT(find_by_text(QString)));

    connect(ui->actionJump_to_nearest_note,SIGNAL(triggered()),canvas,SLOT(jump_to_nearest_note()));
    connect(ui->actionDetails,SIGNAL(triggered()),this,SLOT(show_note_details_window()));

    //Creating the clipboard_nf (id=-1) which holds the notes on copy operations
    clipboard_dir = new MisliDir("",NULL,0); //create a virtual dir

    clipboard_nf = new NoteFile(clipboard_dir);
    clipboard_nf->name="ClipboardNf";

    grabGesture(Qt::PinchGesture);
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
    /*if (QGesture *swipe = event->gesture(Qt::SwipeGesture))
        swipeTriggered(static_cast<QSwipeGesture *>(swipe));
    else if (QGesture *pan = event->gesture(Qt::PanGesture))
        panTriggered(static_cast<QPanGesture *>(pan));*/
    if (QGesture *pinch = event->gesture(Qt::PinchGesture))
        pinchTriggered(static_cast<QPinchGesture *>(pinch));
    return true;
}

bool MisliWindow::pinchTriggered(QPinchGesture *gesture)
{

    canvas->eye_z =  canvas->eye_z/gesture->scaleFactor();
    canvas->update();
}

MisliInstance * MisliWindow::misli_i()
{
    return misli_dg->misli_i;
}

MisliWindow::~MisliWindow()
{
    delete ui;
    delete clipboard_dir;
    delete clipboard_nf;
}

void MisliWindow::closeEvent(QCloseEvent *){
    misli_dg->settings->setValue("successful_start",QVariant(0));
    misli_dg->settings->sync();
    qDebug()<<"Settings SYNC status(in closeEvent): "<<misli_dg->settings->status();
}

void MisliWindow::export_settings()
{
    QStringList notes_dir;
    for(unsigned int i=0;i<misli_i()->misli_dir.size();i++){
        notes_dir.push_back(misli_i()->misli_dir[i]->notes_dir);
    }
    misli_dg->settings->setValue("notes_dir",QVariant(notes_dir));
    misli_dg->settings->setValue("language",QVariant(language));
    misli_dg->settings->sync();
    qDebug()<<"Settings SYNC status: "<<misli_dg->settings->status();
}

QAction * MisliWindow::get_action_for_name(QString name)
{

    for(int a=0;a<ui->menuFolders->actions().size();a++){ //remove the appropriate action
        if(ui->menuFolders->actions().at(a)->text()==name){
            return ui->menuFolders->actions().at(a);
        }
    }

    return NULL;
}

void MisliWindow::set_current_misli_dir(QString path)
{
    misli_i()->set_current_misli_dir(path);
}

void MisliWindow::undo()
{
    misli_i()->curr_misli_dir()->curr_nf()->undo();
    update_current_nf();
}
int MisliWindow::copy()
{
    int copied_notes=0;
    int x=canvas->current_mouse_x;
    int y=canvas->current_mouse_y;

    while(clipboard_nf->get_lowest_id_note()!=NULL){ //delete all notes in clipnf
        clipboard_nf->delete_note(clipboard_nf->get_lowest_id_note());
    }

    copied_notes=copy_selected_notes(misli_i()->curr_misli_dir()->curr_nf(),clipboard_nf ); //dumb copy the selected notes

    if(copied_notes==0){return -1;} //if nothing is copied - end

    //make coordinates relative
    if(canvas->get_note_under_mouse(x,y)!=NULL){ //to the note under the mouse if there's one
        clipboard_nf->make_coords_relative_to(canvas->get_note_under_mouse(x,y)->x,canvas->get_note_under_mouse(x,y)->y);
    }else {//else make relative to one of the copied notes
        clipboard_nf->make_coords_relative_to(clipboard_nf->get_lowest_id_note()->x,clipboard_nf->get_lowest_id_note()->y);
    }

    return copied_notes;
}
void MisliWindow::paste()
{
    canvas->paste();
}
int MisliWindow::cut()
{
    int notes_affected=0;

    notes_affected+=copy();
    notes_affected+=misli_i()->curr_misli_dir()->delete_selected();

    if(notes_affected!=0){misli_i()->curr_misli_dir()->curr_nf()->save();update_current_nf();}

    return notes_affected;
}
void MisliWindow::edit_note()
{
    misli_dg->edit_w->edit_note();
}
void MisliWindow::new_note()
{
    misli_dg->edit_w->new_note();
}

void MisliWindow::new_nf()
{
    misli_dg->newnf_w->new_nf();
}
void MisliWindow::rename_nf()
{
    misli_dg->newnf_w->rename_nf(misli_i()->curr_misli_dir()->curr_nf());
}
void MisliWindow::delete_nf()
{
    QDir dir(misli_i()->curr_misli_dir()->notes_dir);
    QString qstr=misli_i()->curr_misli_dir()->curr_nf()->full_file_addr;
    QMessageBox msg,msg2;

    msg.setText(tr("This will delete the note file permanetly!"));
    msg.setStandardButtons(QMessageBox::Ok|QMessageBox::Cancel);
    msg.setDefaultButton(QMessageBox::Ok);
    msg.setIcon(QMessageBox::Warning);

    if( (misli_i()->curr_misli_dir()->curr_nf()->name != "ClipboardNf") && (misli_i()->curr_misli_dir()->curr_nf()->name != "HelpNoteFile") ){
        int ret=msg.exec();
        if(ret==QMessageBox::Ok){//if the user confirms
            if(!dir.remove(qstr)){

                msg.setText(tr("Could not delete the file.Check your permissions."));
            }

            misli_i()->curr_misli_dir()->delete_nf(misli_i()->curr_misli_dir()->curr_nf()->name);
        }
    }else{
        msg2.setText(tr("Cannot delete a system note file."));
        msg2.exec();
    }
}
void MisliWindow::make_link()
{
    canvas->set_linking_on();
    canvas->update();
}
void MisliWindow::next_nf()
{
    misli_i()->curr_misli_dir()->next_nf();
}
void MisliWindow::prev_nf()
{
    misli_i()->curr_misli_dir()->previous_nf();
}
void MisliWindow::delete_selected()
{
    misli_i()->curr_misli_dir()->delete_selected();
    canvas->update();
}
void MisliWindow::zoom_out()
{
    canvas->eye_z+=MOVE_SPEED;
    canvas->save_eye_coords_to_nf();
    canvas->update();
}
void MisliWindow::zoom_in()
{
    canvas->eye_z-=MOVE_SPEED;
    canvas->save_eye_coords_to_nf();
    canvas->update();
}

void MisliWindow::toggle_help()
{
    if(misli_i()->curr_misli_dir()->curr_nf()->name!=QString("HelpNoteFile")){
        nf_before_help=misli_i()->curr_misli_dir()->curr_nf()->name;
        misli_i()->curr_misli_dir()->set_current_note_file("HelpNoteFile");
    }else{
        misli_i()->curr_misli_dir()->set_current_note_file(nf_before_help);
    }
}
void MisliWindow::make_viewpoint_default()
{
    misli_i()->curr_misli_dir()->curr_nf()->make_coords_relative_to(canvas->eye_x,canvas->eye_y);
    misli_i()->curr_misli_dir()->curr_nf()->init_notes();
    misli_i()->curr_misli_dir()->curr_nf()->init_links();
    canvas->eye_x=0; //(before the update invoked by save() )
    canvas->eye_y=0;
    misli_i()->curr_misli_dir()->curr_nf()->save();
    update_current_nf();
}
void MisliWindow::make_nf_default()
{
    misli_i()->curr_misli_dir()->set_curr_nf_as_default_on_startup();
}
void MisliWindow::remove_current_folder()
{
    for(unsigned int i=0;i<misli_i()->misli_dir.size();i++){
        if(misli_i()->misli_dir[i]->notes_dir==misli_i()->curr_misli_dir()->notes_dir){
            ui->menuFolders->removeAction(get_action_for_name(misli_i()->curr_misli_dir()->notes_dir));
            misli_i()->misli_dir.erase(misli_i()->misli_dir.begin()+i);
            break;
        }
    }
    if(misli_i()->misli_dir.size()==0){ //if it was the last dir
        recheck_for_dirs();
    }else{ //if there are other dirs
        get_action_for_name(misli_i()->misli_dir[0]->notes_dir)->trigger();
    }
    export_settings();
}
void MisliWindow::switch_current_nf()
{
    QString s;

    if(misli_i()->notes_rdy()){
        s=tr("Misli - ");
        s+=misli_i()->curr_misli_dir()->curr_nf()->name;
        if(misli_i()->curr_misli_dir()->curr_nf()->is_deleted_externally){
            s+=tr("(file is deleted externally)");
        }
        setWindowTitle(s);
        canvas->set_eye_coords_from_curr_nf();
    }
    update_current_nf();
}
void MisliWindow::update_current_nf()
{
    if(misli_i()->notes_rdy()){
        canvas->update();
    }
}

void MisliWindow::set_lang_bg()
{
    misli_dg->settings->setValue("language",QVariant("bg"));
    misli_dg->settings->sync();
    qDebug()<<"Settings SYNC status: "<<misli_dg->settings->status();

    QMessageBox msg;
    msg.setText("Програмата ще се изключи. При следващото пускане езикът ще е сменен.");
    msg.exec();

    close();
}
void MisliWindow::set_lang_en()
{
    misli_dg->settings->setValue("language",QVariant("en"));
    misli_dg->settings->sync();
    qDebug()<<"Settings SYNC status: "<<misli_dg->settings->status();

    QMessageBox msg;
    msg.setText("The application will close . On the next start the language will be changed .");
    msg.exec();

    close();
}
void MisliWindow::clear_settings_and_exit()
{
    misli_dg->settings->clear();
    misli_dg->settings->sync();
    qDebug()<<"Settings SYNC status: "<<misli_dg->settings->status();
    exit(0);
}

void MisliWindow::col_blue()
{
    NoteFile *nf=misli_i()->curr_misli_dir()->curr_nf();
    Note *nt;
    while(nf->get_first_selected_note()!=NULL){
        nt=nf->get_first_selected_note();

        nt->txt_col[0] = 0;
        nt->txt_col[1] = 0;
        nt->txt_col[2] = 1;
        nt->txt_col[3] = 1;

        nt->bg_col[0] = 0;
        nt->bg_col[1] = 0;
        nt->bg_col[2] = 1;
        nt->bg_col[3] = 0.1;

        nt->selected=false;
        nt->draw_pixmap();
    }
    nf->save();
    update_current_nf();
}
void MisliWindow::col_green()
{
    NoteFile *nf=misli_i()->curr_misli_dir()->curr_nf();
    Note *nt;
    while(nf->get_first_selected_note()!=NULL){
        nt=nf->get_first_selected_note();

        nt->txt_col[0] = 0;
        nt->txt_col[1] = 0.64;
        nt->txt_col[2] = 0.235;
        nt->txt_col[3] = 1;

        nt->bg_col[0] = 0;
        nt->bg_col[1] = 1;
        nt->bg_col[2] = 0;
        nt->bg_col[3] = 0.1;

        nt->selected=false;
        nt->draw_pixmap();
    }
    nf->save();
    update_current_nf();
}
void MisliWindow::col_red()
{
    NoteFile *nf=misli_i()->curr_misli_dir()->curr_nf();
    Note *nt;
    while(nf->get_first_selected_note()!=NULL){
        nt=nf->get_first_selected_note();

        nt->txt_col[0] = 1;
        nt->txt_col[1] = 0;
        nt->txt_col[2] = 0;
        nt->txt_col[3] = 1;

        nt->bg_col[0] = 1;
        nt->bg_col[1] = 0;
        nt->bg_col[2] = 0;
        nt->bg_col[3] = 0.1;

        nt->selected=false;
        nt->draw_pixmap();
    }
    nf->save();
    update_current_nf();
}
void MisliWindow::col_black()
{
    NoteFile *nf=misli_i()->curr_misli_dir()->curr_nf();
    Note *nt;
    while(nf->get_first_selected_note()!=NULL){
        nt=nf->get_first_selected_note();

        nt->txt_col[0] = 0;
        nt->txt_col[1] = 0;
        nt->txt_col[2] = 0;
        nt->txt_col[3] = 1;

        nt->bg_col[0] = 0;
        nt->bg_col[1] = 0;
        nt->bg_col[2] = 0;
        nt->bg_col[3] = 0.1;

        nt->selected=false;
        nt->draw_pixmap();
    }
    nf->save();
    update_current_nf();
}

void MisliWindow::move_down()
{
    canvas->eye_y+=MOVE_SPEED;
    QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
    canvas->save_eye_coords_to_nf();
    canvas->update();
}
void MisliWindow::move_up()
{
    canvas->eye_y-=MOVE_SPEED;
    QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
    canvas->save_eye_coords_to_nf();
    canvas->update();
}
void MisliWindow::move_left()
{
    canvas->eye_x-=MOVE_SPEED;
    QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
    canvas->save_eye_coords_to_nf();
    canvas->update();
}
void MisliWindow::move_right()
{
    canvas->eye_x+=MOVE_SPEED;
    QCursor::setPos( mapToGlobal( QPoint( width()/2 , height()/2 )) );
    canvas->save_eye_coords_to_nf();
    canvas->update();
}

void MisliWindow::recheck_for_dirs()
{
    qDebug()<<"Rechecking for dirs.";
    if(misli_i()->misli_dir.size()<=0){
        qDebug()<<"Notes were not present in recheck_for_dirs.";
        hide();
        misli_dg->dir_w->show();
    }else{
        qDebug()<<"Notes are present.";
        if(misli_dg->first_program_start){ //if it's the first dir we're making go to the help file
            qDebug()<<"first_program_start is set to true.";
            misli_dg->misli_i->curr_misli_dir()->set_current_note_file("HelpNoteFile");
            misli_dg->first_program_start=false;
        }

        if(!misli_dg->splash->isHidden()){
            qDebug()<<"Hiding splash screen";
            misli_dg->splash->hide(); //end the splash screen
        }

        if(isHidden()){
            qDebug()<<"Showing main window.";
            showMaximized();
        }
    }

    switch_current_nf();
}
int MisliWindow::copy_selected_notes(NoteFile *source_nf,NoteFile *target_nf) //dumb copy :same places same id-s
{
    Note *nt_in_source,*nt_in_target;
    Link *ln;
    int copied_notes=0;

    QClipboard *clipboard = QApplication::clipboard();
    QString clip_text;

    for(unsigned int i=0;i<source_nf->note.size();i++){ //copy selected notes (only the info that would be in the file)
        nt_in_source = source_nf->note[i];
        if(nt_in_source->selected){
            target_nf->add_note(nt_in_source);
            copied_notes++;
            clip_text+=nt_in_source->text; //Add the note text to the regular clipboard
            clip_text+="\n\n"; //leave space before the next (gets trimmed in the end)
        }
    }
    for(unsigned int i=0;i<source_nf->note.size();i++){ //add all the links
        nt_in_source=source_nf->note[i];
        if(nt_in_source->selected){
            nt_in_target = target_nf->get_note_by_id(nt_in_source->id); //get the note pointed to

            //for every link in the source note add a link in the target note
            for(unsigned int l=0;l<nt_in_source->outlink.size();l++){
                ln=&nt_in_source->outlink[l];
                nt_in_target->add_link(ln);
            }

        }
    }
    clip_text=clip_text.trimmed();
    clipboard->setText(clip_text);
    return copied_notes;
}

void MisliWindow::add_new_folder()
{
    misli_dg->dir_w->show();
}

void MisliWindow::add_menu_entry_for_dir(QString path)
{
    EmitMyNameAction *act = new EmitMyNameAction(path,ui->menuFolders);
    ui->menuFolders->addAction(act);
    connect(act,SIGNAL(triggered_with_name(QString)),misli_i(),SLOT(set_current_misli_dir(QString)));
    act->check_only_me();
}
void MisliWindow::display_results(QString string)
{
    if(string.isEmpty()){display_search_results=true;} //mostly to get rid of the warning unused var

    misli_i()->load_results_in_search_nf();
    display_search_results=true;
    canvas->update();
}
void MisliWindow::hide_search_stuff()
{
    display_search_results=false;
}
void MisliWindow::select_all_notes()
{
    misli_i()->curr_misli_dir()->curr_nf()->select_all_notes();
    canvas->update();
}
void MisliWindow::find_by_text(QString string)
{
    misli_dg->notes_search->load_notes(misli_i(),1);
    misli_dg->notes_search->find_by_text(string);
}
void MisliWindow::show_note_details_window()
{
    Note * nt = misli_i()->curr_misli_dir()->curr_nf()->get_first_selected_note();
    if(nt!=NULL){
        misli_dg->note_w->updateInfo(*nt);
        misli_dg->note_w->show();
        misli_dg->note_w->raise();
        misli_dg->note_w->activateWindow();
    }
}
