#include "misliwindow.h"
#include "ui_misliwindow.h"

#include "newnfdialogue.h"
#include "editnotedialogue.h"
#include "getdirdialogue.h"
#include "glwidget.h"

MisliWindow::MisliWindow(QApplication* app):
    ui(new Ui::MisliWindow)
{
    a=app;
    ui->setupUi(this);
    notes_rdy=false;
    first_program_start=false;

    gl_w = new GLWidget(this);
    setCentralWidget(gl_w);
    gl_w->updateGL(); //if the first paint isn't called before the texture init for the texts there's a bug with the textures

    dir_w = new GetDirDialogue(this);
    edit_w = new EditNoteDialogue(this);
    newnf_w = new NewNFDialogue(this);

    setWindowTitle("Loading notefiles...");
    setWindowIcon(QIcon(":/img/icon.png"));

    import_settings_and_folders();
}

MisliWindow::~MisliWindow()
{
    delete ui;
}

void MisliWindow::import_settings_and_folders() //loads the settings . Returns 0 on success.
{
    QStringList notes_dir;

    //Settings
    settings = new QSettings;

    if(settings->contains("notes_dir")){
        notes_dir = settings->value("notes_dir").toStringList();
    }

    if(settings->contains("language")){
        language=settings->value("language","en").toString();
    }else{
        language="en";
    }

    for(int i=0;i<notes_dir.size();i++){
        add_dir(notes_dir[i]);
    }
    if(!notes_rdy) {
        add_new_folder();
        first_program_start=true;
    }

    export_settings();
}

void MisliWindow::export_settings()
{
    QStringList notes_dir;
    for(unsigned int i=0;i<misli.size();i++){
        notes_dir.push_back(misli[i]->notes_dir);
    }
    settings->setValue("notes_dir",QVariant(notes_dir));

    settings->setValue("language",QVariant(language));
    settings->sync();
}

void MisliWindow::add_dir(QString path)
{
    MisliInstance * mi= new MisliInstance(path,this);
    misli.push_back(mi);
    if(misli.back()->error!=0){
        misli.pop_back();
        return;
    }
    if(notes_rdy==false){
        notes_rdy=true;
        showMaximized();
    }

    set_current_misli(path);

    //Adding a menu entry
    EmitMyNameAction *act = new EmitMyNameAction(path,ui->menuFolders);
    ui->menuFolders->addAction(act);
    connect(act,SIGNAL(triggered_with_name(QString)),this,SLOT(set_current_misli(QString)));
    act->check_only_me();

    if(first_program_start){ //if it's the first dir we're making go to the help file
        curr_misli()->set_current_notes(-2);
        first_program_start=false;
    }

    export_settings();
}
MisliInstance * MisliWindow::curr_misli()
{
    return misli_by_name(current_misli_name);
}

MisliInstance * MisliWindow::misli_by_name(QString path)
{
    for(unsigned int i=0;i<misli.size();i++){
        if(misli[i]->notes_dir==path){
            return misli[i];
        }
    }
    return NULL;
}
void MisliWindow::set_current_misli(QString path)
{
    current_misli_name=path;
    switch_current_nf();
}

void MisliWindow::undo()
{
    curr_misli()->undo();
}
void MisliWindow::copy()
{
    gl_w->copy();
}
void MisliWindow::paste()
{
    gl_w->paste();
}
void MisliWindow::cut()
{
    gl_w->cut();
}
void MisliWindow::edit_note()
{
    edit_w->edit_note();
}
void MisliWindow::new_note()
{
    edit_w->new_note();
}
void MisliWindow::new_nf()
{
    newnf_w->new_nf();
}
void MisliWindow::make_link()
{
    gl_w->set_linking_on();
}
void MisliWindow::next_nf()
{
    curr_misli()->next_nf();
}
void MisliWindow::prev_nf()
{
    curr_misli()->previous_nf();
}
void MisliWindow::delete_selected()
{
    curr_misli()->delete_selected();
}
void MisliWindow::zoom_out()
{
    gl_w->eye.z+=misli_speed;
    gl_w->updateGL();
}
void MisliWindow::zoom_in()
{
    gl_w->eye.z-=misli_speed;
    gl_w->updateGL();
}

void MisliWindow::toggle_help()
{
    if(curr_misli()->current_note_file!=(-2)){
        curr_misli()->nf_before_help=curr_misli()->current_note_file;
        curr_misli()->set_current_notes(-2);
    }else{
        curr_misli()->set_current_notes(curr_misli()->nf_before_help);
    }
}
void MisliWindow::make_viewpoint_default()
{
    curr_misli()->curr_nf()->make_coords_relative_to(gl_w->eye.x,gl_w->eye.y);
    curr_misli()->curr_nf()->init_notes();
    curr_misli()->curr_nf()->init_links();
    curr_misli()->curr_nf()->save();
    gl_w->eye.x=0;
    gl_w->eye.y=0;
    gl_w->eye.scenex=0;
    gl_w->eye.sceney=0;

}
void MisliWindow::make_nf_default()
{
    curr_misli()->set_curr_nf_as_default_on_startup();
}
void MisliWindow::add_new_folder()
{
    dir_w->show();
}
void MisliWindow::remove_current_folder()
{
    for(unsigned int i=0;i<misli.size();i++){
        if(misli[i]->notes_dir==curr_misli()->notes_dir){

            for(int a=0;a<ui->menuFolders->actions().size();a++){ //remove the appropriate action
                if(ui->menuFolders->actions().at(a)->text()==curr_misli()->notes_dir){
                    ui->menuFolders->removeAction(ui->menuFolders->actions().at(a));
                    break;
                }
            }

            misli.erase(misli.begin()+i);
            break;
        }
    }
    if(misli.size()==0){ //if it was the last dir
        notes_rdy=0;
        add_new_folder();
    }else{ //if there are other dirs
        set_current_misli(misli[0]->notes_dir);
    }
    export_settings();
}
void MisliWindow::switch_current_nf()
{
    QString s;

    if(notes_rdy){
        s=tr("Misli - ");
        s+=curr_misli()->curr_nf()->name;
        setWindowTitle(s);
        gl_w->set_eye_coords_from_curr_nf();
    }
    update_current_nf();
}
void MisliWindow::update_current_nf()
{
    if(notes_rdy){
        gl_w->updateGL();
    }
}

void MisliWindow::set_lang_bg()
{
    language="bg";
    export_settings();

    QMessageBox msg;
    msg.setText("Програмата ще се изключи. При следващото пускане езикът ще е сменен.");
    msg.exec();

    close();
}
void MisliWindow::set_lang_en()
{
    language="en";
    export_settings();

    QMessageBox msg;
    msg.setText("The application will close . On the next start the language will be changed .");
    msg.exec();

    close();
}
void MisliWindow::clear_settings_and_exit()
{
    settings->clear();
    settings->sync();
    exit(0);
}
