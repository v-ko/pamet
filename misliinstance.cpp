/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "misliinstance.h"
#include "misliwindow.h"

MisliInstance::MisliInstance(QString nts_dir, MisliWindow *msl_w_ = NULL)
{
    //Init
    notes_dir=nts_dir;
    changes_accounted_for=0;
    current_note_file=0;
    last_nf_id=0;
    msl_w=msl_w_;
    if(msl_w==NULL){
        using_external_classes=false;
    }else{
        using_external_classes=true;
        gl_w=msl_w->gl_w;
    }

    //FS-watch stuff
    fs_watch = new FileSystemWatcher(this);
    hanging_nf_check = new QTimer;
    connect(hanging_nf_check,SIGNAL(timeout()),this,SLOT(check_for_hanging_nfs() ));

    error=0;

    //Creating the clipboard_nf (id=-1) which holds the notes on copy operations
    note_file.push_back(NoteFile());
    note_file.back().id=-1;
    note_file.back().name="ClipboardNf";
    note_file.back().misl_i=this;
    note_file.back().note = new NotesVector;
    note_file.back().nf_z = new std::vector<std::string>;

    if(using_external_classes){

        //Creating the help NF
        QString qstr;
        qstr=":/help/help_"+msl_w->language;
        qstr+=".misl";
        note_file.push_back(NoteFile());
        note_file.back().init(this,"HelpNoteFile",qstr,-2);
    }

    init_notes_files();
}

void MisliInstance::check_for_hanging_nfs()
{
    NoteFile * nf;
    int count=0;

    for(unsigned int i=0;i<note_file.size();i++){
        nf = &note_file[i];
        if(nf->deleted){
            //Try to init
            if( nf->init(this,nf->name,nf->full_file_addr,nf->id) == 0 ){
                nf->deleted = false;
                fs_watch->addPath(nf->full_file_addr); //when a file is deleted it gets off the fs_watch and we need to re-add it when a unix-type file save takes place
                emit_current_nf_updated();
            }else{
                count++;
            }
        }
    }
    if(count<=0) hanging_nf_check->stop();
}

void MisliInstance::emit_current_nf_switched()
{
    if(using_external_classes){
        msl_w->switch_current_nf();
    }
}
void MisliInstance::emit_current_nf_updated()
{
    if(using_external_classes){
        msl_w->update_current_nf();
    }
}

NoteFile * MisliInstance::nf_by_id(int id)
{
    for(unsigned int i=0; i<note_file.size() ; i++){
        if(note_file[i].id==id){
            return &note_file[i];
        }
    }
    return NULL;
}
NoteFile * MisliInstance::nf_by_name(QString name)
{
    for(unsigned int i=0; i<note_file.size() ; i++){
        if(note_file[i].name==name){
            return &note_file[i];
        }
    }
    return NULL;
}
NoteFile * MisliInstance::curr_nf()
{
    return nf_by_id(current_note_file);
}
NoteFile * MisliInstance::clipboard_nf()
{
    return nf_by_id(-1);
}

NoteFile * MisliInstance::default_nf_on_startup()
{
    for(unsigned int i=0;i<note_file.size();i++){
        if(note_file[i].is_displayed_first_on_startup){return &note_file[i];}
    }
    return NULL;
}

int MisliInstance::make_notes_file(QString name)
{
    int err=1;
    std::fstream ntFile;

    if(nf_by_name(name)!=NULL){
        return -1;
    }
    err+=chdir(notes_dir.toStdString().c_str());

    name+=".misl";

     ntFile.open(name.toStdString().c_str(),std::ios_base::out);
    if(ntFile.fail()){err++;}

    ntFile<<"#Notes database for Misli"<<'\n';

    ntFile.close();

    if(err!=true){d("error making new notes file");}
    return err;
}

void MisliInstance::set_current_notes(int n)
{

    if(nf_by_id(n)==NULL){
        return;
    }

    current_note_file=n;
    curr_note=nf_by_id(n)->note; //the one for this class

    emit_current_nf_switched();
}

int MisliInstance::next_nf() //changes the current note file only to a non-system nf
{
    for(unsigned int i=0;i<(note_file.size()-1);i++){ //for every notefile without the last one
        if(current_note_file>=0){//if we're not on a system nf
            if( (current_note_file==note_file[i].id) && (note_file[i+1].id>=0) ){//if it's the current one and the next is not a system one
                set_current_notes(note_file[i+1].id);
                return 0;
            }

        }else{//if we're on a system nf
            if(note_file[i+1].id>=0){ //we switch to a random normal nf
                set_current_notes(note_file[i+1].id);
            }
        }
    }

    return 1;
}
int MisliInstance::previous_nf()
{
    for(unsigned int i=1;i<note_file.size();i++){ //for every notefile without the last one
        if(current_note_file>=0){//if we're not on a system nf
            if( (current_note_file==note_file[i].id) && (note_file[i-1].id>=0) ){//if it's the current one and the next is not a system one
                set_current_notes(note_file[i-1].id);
                return 0;
            }
        }else{//if we're on a system nf
            if(note_file[i-1].id>=0){ //we switch to a random normal nf
                set_current_notes(note_file[i-1].id);
            }
        }
    }

    return 1;
}
int MisliInstance::delete_nf(int id) //soft delete
{
    NoteFile * nf;

    //Find and delete the notefile
    for(unsigned int i=0;i<note_file.size();i++){
        nf = &note_file[i];
        if(nf->id==id){
            note_file.erase(note_file.begin()+i);
            break;
        }
    }

    //Switch the current notefile to something valid
    if(find_first_normal_nf()==NULL){
        init_notes_files();
    }else{
        set_current_notes(find_first_normal_nf()->id);
    }

    reinit_redirect_notes(); //update a probable link to the deleted nf

    return 0;
}

int MisliInstance::undo()
{
    std::fstream ntf;
    std::string str;

    //std::vector<std::string> *nfz=curr_nf()->nf_z;

    if(curr_nf()->nf_z->size()>=2){

        ntf.open(curr_nf()->full_file_addr.toStdString().c_str(),std::ios_base::out); //open file
        curr_nf()->nf_z->pop_back(); //pop the current version
        ntf<<curr_nf()->nf_z->back(); //flush the first backup in

        ntf.close();

        curr_nf()->init(this,curr_nf()->name,curr_nf()->full_file_addr,curr_nf()->id);

        set_current_notes(curr_nf()->id); //load the backup
        //curr_nf()->nf_z=nfz;

        emit_current_nf_updated();
        return 0;
    }else{
        return 1;
    }

}
int MisliInstance::copy_selected_notes(NoteFile *source_nf,NoteFile *target_nf) //dumm copy :same places same id-s
{
    Note *nt_in_source,*nt_in_target;
    Link *ln;

    for(unsigned int i=0;i<source_nf->note->size();i++){ //copy notes (only "hard" info)
        nt_in_source =&(*source_nf->note)[i];
        if(nt_in_source->selected){
            target_nf->add_note(nt_in_source);
        }
    }
    for(unsigned int i=0;i<source_nf->note->size();i++){ //add all the links
        nt_in_source=&(*source_nf->note)[i];
        if(nt_in_source->selected){
            nt_in_target = target_nf->get_note_by_id(nt_in_source->id); //get the coplementary note

            //for every link in the source note add a link in the target note
            for(unsigned int l=0;l<nt_in_source->outlink.size();l++){
                ln=&nt_in_source->outlink[l];
                nt_in_target->add_link(ln);
            }

        }
    }
    return 0;
}

int MisliInstance::init_notes_files()
{
    QDir dir(notes_dir);
    NoteFile *nf;

    QStringList entry_list = dir.entryList();
    QString entry,file_addr;

    int file_found=false;

    for(int i=0;i<entry_list.size();i++){

        entry=entry_list[i];

        if(entry.isEmpty()) break;

        if( entry.endsWith(QString(".misl")) ){ //only for .misl files

            file_addr = dir.absoluteFilePath(entry);
            entry.chop(5); // ".misl".size()==5
            entry=entry.trimmed();

            note_file.push_back(NoteFile());
            nf=&note_file.back();

            nf->init(this,entry,file_addr);
            nf->virtual_save(); //should be only a virtual save for ctrl-z

            file_found=true;
        }

    }

    if(!file_found){ //if n=-1 directory empty , make default notes file

        make_notes_file("notes");

        file_addr=notes_dir;
        file_addr+="/";
        file_addr+="notes.misl";

        note_file.push_back(NoteFile()); //nov obekt (vajno e pyrvo da go napravim ,za6toto pri dobavqneto na notes se zadava pointer kym note-file-a i toi trqbva da e kym realniq nf vyv vectora
        nf=&note_file.back();

        nf->init(this,"notes",file_addr.toUtf8().data());
    }

    if(default_nf_on_startup()!=NULL) current_note_file=default_nf_on_startup()->id;
    else current_note_file=find_first_normal_nf()->id;

    nf_before_help=current_note_file;

    set_current_notes(current_note_file);

    reinit_redirect_notes();

    return 0;
}
int MisliInstance::reinit_redirect_notes()
{
    NoteFile * nf;
    Note *nt;

    for(unsigned int i=0;i<note_file.size();i++){
        nf = &note_file[i];
        for(unsigned int n=0;n<nf->note->size();n++){
            nt=&((*nf->note)[n]);
            if(nt->type!=0){nt->init();}
        }
    }
return 0;
}

void MisliInstance::set_curr_nf_as_default_on_startup()
{
    for(unsigned int i=0;i<note_file.size();i++){ //we make sure that there's no second nf marked as default for display
        if (note_file[i].id!=curr_nf()->id) {
            if(note_file[i].is_displayed_first_on_startup==true){
                note_file[i].is_displayed_first_on_startup=false;
                note_file[i].save();
            }
        }
        else{
            if(note_file[i].is_displayed_first_on_startup==false){
                note_file[i].is_displayed_first_on_startup=true;
                note_file[i].save();
            }
        }
    }
}

int MisliInstance::delete_selected()
{
    return curr_nf()->delete_selected();
}
NoteFile *MisliInstance::find_first_normal_nf()
{
    for(unsigned int i=0;i<note_file.size();i++){
        if(note_file[i].id>=0){
            return &note_file[i];
        }
    }

    return 0;
}

void MisliInstance::file_changed(QString file)
{
    NoteFile *nf;
    int err=0;

    for(unsigned int f=0;f<note_file.size();f++){
        nf=&note_file[f];
        if(nf->full_file_addr==file){
            err = nf->init(this,nf->name,nf->full_file_addr,nf->id);
            if( err == 0 ){
                emit_current_nf_updated();
            }else if(err ==-2){
                nf->deleted=true;
                hanging_nf_check->start(700);
            }
            return;
        }
    }
}
