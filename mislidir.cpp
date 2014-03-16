/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <QDebug>

#include "misliinstance.h"
#include "mislidir.h"
#include "misliwindow.h"
#include "mislidesktopgui.h"

MisliDir::MisliDir(QString nts_dir, MisliInstance* misli_i_ = NULL, bool using_gui_ = true)
{
    misli_i=misli_i_;
    notes_dir=nts_dir;
    using_gui = using_gui_;

    if(misli_i==NULL){ //if there's no instance above there's no GUI for sure , but if there is there still may be no GUI
        using_gui=false;
    }

    if(nts_dir.isEmpty()){
        is_virtual=true;
    }else{
        is_virtual=false;
    }

    is_current=0;

    //----------FS-watch stuff----------------
    fs_watch = new FileSystemWatcher(this);

    hanging_nf_check = new QTimer;
    if(!is_virtual) connect(hanging_nf_check,SIGNAL(timeout()),this,SLOT(check_for_hanging_nfs() ));

    //------Creating the help NF---------------
    if( (!is_virtual) && using_gui ){
        QString qstr;
        qstr=":/help/help_"+ misli_i->misli_dg->language;
        qstr+=".misl";
        note_file.push_back(new NoteFile(this));
        note_file.back()->init("HelpNoteFile",qstr);
    }

    //-----------------
    if(!is_virtual) load_notes_files();
}
MisliDir::~MisliDir()
{
    delete fs_watch;
    delete hanging_nf_check;
    for(unsigned int i=0;i<note_file.size();i++){
        delete note_file[i];
    }
}

void MisliDir::check_for_hanging_nfs()
{
    NoteFile * nf;
    int missing_nf_count=0; //

    for(unsigned int i=0;i<note_file.size();i++){
        nf = note_file[i];
        if(nf->is_deleted_externally){
            //Try to init
            if( nf->init(nf->name,nf->full_file_addr) == 0 ){
                nf->is_deleted_externally = false;
                qDebug()<<"Adding path to fs_watch: "<<nf->full_file_addr;
                fs_watch->addPath(nf->full_file_addr); //when a file is deleted it gets off the fs_watch and we need to re-add it when a unix-type file save takes place
                emit current_nf_switched();

            }else{
                missing_nf_count++;
            }
        }
    }
    if(missing_nf_count==0) hanging_nf_check->stop(); //if none are missing - stop checking
}

NoteFile * MisliDir::nf_by_name(QString name)
{
    if(name=="ClipboardNf"){
        return misli_i->misli_dg->misli_w->clipboard_nf;
    }
    for(unsigned int i=0; i<note_file.size() ; i++){
        if(note_file[i]->name==name){
            return note_file[i];
        }
    }
    //qDebug()<<"NoteFile with name "<<name<<" was not found in dir: "<<notes_dir<<" .";
    return NULL;
}
NoteFile * MisliDir::curr_nf()
{
    for(unsigned int n=0;n<note_file.size();n++){
        if(note_file[n]->is_current){
            return note_file[n];
        }
    }
    return NULL;
}

NoteFile * MisliDir::default_nf_on_startup()
{
    for(unsigned int i=0;i<note_file.size();i++){
        if(note_file[i]->is_displayed_first_on_startup){return note_file[i];}
    }
    return NULL;
}

int MisliDir::make_notes_file(QString name)
{
    QFile ntFile;
    QString file_name_sstr;

    if(nf_by_name(name)!=NULL){
        return -1;
    }

    file_name_sstr+=name+".misl";
    file_name_sstr=QDir(notes_dir).filePath(file_name_sstr);

    ntFile.setFileName(file_name_sstr);

    if(!ntFile.open(QIODevice::WriteOnly)){
        qDebug()<<"Error making new notes file";
        return -1;
    }

    ntFile.write(QByteArray(tr("#Notes database for Misli\n[1]\ntxt=Double-click to edit or make a new note.F1 for help.\nx=-5\ny=-2\nz=0\na=10\nb=4\nfont_size=1\nt_made=2.10.2013 19:10:16\nt_mod=2.10.2013 19:10:16\ntxt_col=0;0;1;1\nbg_col=0;0;1;0.1\nl_id=\nl_txt=").toUtf8()));
    ntFile.close();

    note_file.push_back(new NoteFile(this)); //nov obekt (vajno e pyrvo da go napravim ,za6toto pri dobavqneto na notes se zadava pointer kym note-file-a i toi trqbva da e kym realniq nf vyv vectora
    note_file.back()->init(file_name_sstr);

    return 0;
}

void MisliDir::set_current_note_file(QString name)
{

    if(nf_by_name(name)==NULL){ //check if the note file with that name is present
        return;
    }

    for(unsigned int n=0;n<note_file.size();n++){
        if(note_file[n]->name==name){
            note_file[n]->is_current=true;
        }else{
            note_file[n]->is_current=false;
        }
    }

    emit current_nf_switched();
}

int MisliDir::next_nf() //changes the current note file only to a non-system nf
{
    for(unsigned int i=0;i<(note_file.size()-1);i++){ //for every notefile without the last one
        if( curr_nf()->is_not_system() ){//if we're not on a system nf
            if( (curr_nf()->name==note_file[i]->name) && note_file[i+1]->is_not_system() ){//if it's the current one and the next is not a system one
                set_current_note_file(note_file[i+1]->name);
                return 0;
            }

        }else{//if we're on a system nf
            if( note_file[i+1]->is_not_system() ){ //we switch to a random normal nf
                set_current_note_file(note_file[i+1]->name);
            }
        }
    }

    return 1;
}
int MisliDir::previous_nf()
{
    for(unsigned int i=1;i<note_file.size();i++){ //for every notefile without the last one
        if( curr_nf()->is_not_system() ){//if we're not on a system nf
            if( (curr_nf()->name==note_file[i]->name) && note_file[i-1]->is_not_system() ){//if it's the current one and the next is not a system one
                set_current_note_file(note_file[i-1]->name);
                return 0;
            }
        }else{//if we're on a system nf
            if( note_file[i-1]->is_not_system() ){ //we switch to a random normal nf
                set_current_note_file(note_file[i-1]->name);
            }
        }
    }

    return 1;
}
int MisliDir::delete_nf(QString nfname) //soft delete
{
    NoteFile * nf;

    //Find and delete the notefile
    for(unsigned int i=0;i<note_file.size();i++){
        nf = note_file[i];
        if(nf->name==nfname){
            note_file.erase(note_file.begin()+i);
            break;
        }
    }

    //Switch the current notefile to something valid
    if(find_first_normal_nf()==NULL){
        load_notes_files();
    }else{
        set_current_note_file(find_first_normal_nf()->name);
    }

    reinit_notes_pointing_to_notefiles(); //update a probable link to the deleted nf

    return 0;
}

int MisliDir::load_notes_files()
{
    if(is_virtual) return 0;

    QDir dir(notes_dir);

    if(!dir.exists()){
        qDebug()<<"The notes directory "<<notes_dir<<" given to MisliDir does not exist. Exiting!";
        exit(-2);
    }

    NoteFile *nf;

    QStringList entry_list = dir.entryList();
    QString entry,file_addr;

    int file_found=false;

    for(int i=0;i<entry_list.size();i++){

        entry=entry_list[i]; //get the file list

        if(entry.isEmpty()) break;

        if( entry.endsWith(QString(".misl")) ){ //only for .misl files

            file_addr = dir.absoluteFilePath(entry);

            note_file.push_back(new NoteFile(this));
            nf=note_file.back();

            nf->init(file_addr);
            nf->virtual_save(); //should be only a virtual save for ctrl-z

            file_found=true; //mark that the dir is not empty (of .misl files)
        }

    }

    if(!file_found){ //if n=-1 directory empty , make default notes file

        make_notes_file("notes");

    }

    if(default_nf_on_startup()!=NULL) set_current_note_file(default_nf_on_startup()->name);
    else set_current_note_file(find_first_normal_nf()->name);

    if(using_gui){//else segment
        misli_i->misli_dg->misli_w->nf_before_help=curr_nf()->name;
    }

    reinit_notes_pointing_to_notefiles();

    return 0;
}
int MisliDir::reinit_notes_pointing_to_notefiles()
{
    NoteFile * nf;
    Note *nt;

    for(unsigned int i=0;i<note_file.size();i++){ //for every notefile
        nf = note_file[i];
        for(unsigned int n=0;n<nf->note.size();n++){
            nt=nf->note[n];
            if(nt->type==NOTE_TYPE_REDIRECTING_NOTE){nt->init();}
        }
    }
return 0;
}

void MisliDir::set_curr_nf_as_default_on_startup()
{
    for(unsigned int i=0;i<note_file.size();i++){ //we make sure that there's no second nf marked as default for display
        if (note_file[i]->name!=curr_nf()->name) {
            if(note_file[i]->is_displayed_first_on_startup==true){
                note_file[i]->is_displayed_first_on_startup=false;
                note_file[i]->save();
            }
        }else{
            if(note_file[i]->is_displayed_first_on_startup==false){
                note_file[i]->is_displayed_first_on_startup=true;
                note_file[i]->save();
            }
        }
    }
}

int MisliDir::delete_selected()
{
    int deleted_notes=curr_nf()->delete_selected();
    if(deleted_notes!=0){curr_nf()->save();emit current_nf_updated();}
    return deleted_notes;
}
NoteFile *MisliDir::find_first_normal_nf()
{
    for(unsigned int i=0;i<note_file.size();i++){
        if( note_file[i]->is_not_system() ){
            return note_file[i];
        }
    }

    return 0;
}

void MisliDir::handle_changed_file(QString file)
{
    int err=0;
    qDebug()<<"INTO HANDLE CHANGED FILE";

    NoteFile *nf;

    QFileInfo f(file);
    QString fname;
    fname = f.fileName();
    fname.chop(5); // ".misl".size()==5
    fname=fname.trimmed();

    nf = nf_by_name(fname);

    if(nf==NULL){return;}//avoid segfaults on wrong name

    err = nf->init(nf->name,nf->full_file_addr);

    if( err == 0 ){
        emit current_nf_switched();//Updates the title too (compared to .._updated)
    }else if(err ==-2){ //most times the file is deleted and then replaced on sync , so we need to check back for it later
        nf->is_deleted_externally=true;
        if(curr_nf()==nf){
            emit current_nf_switched(); //to change the title if we're looking at the changed nf
        }
        hanging_nf_check->start(700);
    }
}

