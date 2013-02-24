/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "misliinstance.h"

MisliInstance::MisliInstance(int md,QString nts_dir)
{
    //Make objects
    dir_w = new GetDirDialogue(this);
    edit_w = new EditNoteWindow(this);
    get_nf_name_w = new GetNFName(this);
    nt_w = new NotesWindow(this);
    gl_w=nt_w->gl_w;
    help_w = new HelpWindow;

    //Connect signals-slots
    connect(this,SIGNAL(no_notes_dir()),dir_w,SLOT(show()));

    connect(this,SIGNAL(settings_ready()),this,SLOT(init_notes_files()));

    connect(this,SIGNAL(notes_ready()),this,SLOT(set_notes_ready()));
    connect(this,SIGNAL(notes_ready()),this,SLOT(reinit_redirect_notes()));

    //Init
    mode = md;
    notes_dir=nts_dir;
    current_note_file=0;
    last_nf_id=0;
    notes_rdy=0;
    gl_w->updateGL(); //if the first paint isn't called before the texture init for the texts there's a bug with the textures
    check_settings();

    //Creating the clipboard_nf (id=-1) which holds the notes on copy operations
    note_file.push_back(null_note_file);
    note_file.back().id=-1;
    note_file.back().name=strdup("ClipboardNf");
    note_file.back().misl_i=this;
    note_file.back().full_file_addr=NULL;
    note_file.back().note = new NotesVector;
    note_file.back().nf_z = new std::vector<std::string>;

}

void MisliInstance::set_notes_ready()
{
    if(mode!=0){
        nt_w->showMaximized();
        notes_rdy=1;
    }
}

void MisliInstance::settings_ready_publ()
{
    emit settings_ready();
}

NoteFile * MisliInstance::nf_by_id(int id)
{
    for(unsigned int i=0; i<note_file.size() ; i++){
        if(note_file[i].id==id){
            return &note_file[i];
        }
    }
    //d("vyrna se 0 na nf_by_id");
    return NULL;
}
NoteFile * MisliInstance::nf_by_name(const char * ime)
{
    for(unsigned int i=0; i<note_file.size() ; i++){
        if(!strcmp(note_file[i].name,ime)){
            return &note_file[i];
        }
    }
    //d("vyrna se 0 na nf_by_name");
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

int MisliInstance::check_settings() //loads the settings . Returns 0 on success.
{
    //Settings
    settings = new QSettings;

    QString path=settings->value("notes_dir","no_dir").toString(); //get notes dir from settings
    if(path=="no_dir" && notes_dir.isEmpty()){
        emit no_notes_dir();
        return 1;
    }

    if(!notes_dir.isEmpty()){ //manual override if the string at class init isn't null
         path=notes_dir;
    }

    QDir dir(path);

    if( !dir.exists() ){
        emit no_notes_dir();
        d("The notes directory specified in the settings file doesn't exist");
        return 1;
    }else {
        notes_dir=dir.absolutePath();
        emit settings_ready();
    }

    return 0;
}

int MisliInstance::make_notes_file(const char * name)
{
    std::fstream ntFile;
    std::stringstream ss;
    std::string filename;
    int err=1;

    err+=chdir(notes_dir.toStdString().c_str());

    ss<<name<<".misl";
    filename=ss.str();

    ntFile.open(filename.c_str(),std::ios_base::out);
    if(ntFile.fail()){err++;}

    ntFile<<"#Notes database for Misli"<<std::endl;

    ntFile.close();

    if(err!=true){d("error making new notes file");}
    return err;
}
void MisliInstance::set_eye_coords(double x, double y, double z)
{
    eye.x=x;
    eye.y=y;
    eye.z=z;
    eye.scenex=x;
    eye.sceney=y;
    eye.scenez=0;
}
void MisliInstance::save_eye_coords_to_nf()
{
    curr_nf()->eye_x=eye.x;
    curr_nf()->eye_y=eye.y;
    curr_nf()->eye_z=eye.z;
}

void MisliInstance::set_current_notes(int n)
{
    if(n<0) return; //in order to not show system files to the user
    QString txt;
    current_note_file=n;
    curr_note=nf_by_id(n)->note; //the one for this class
    gl_w->curr_note=curr_note; //the one in gl_w (it's separate to keep the code shorter there)
    //emit curr_nf_changed();
    set_eye_coords(curr_nf()->eye_x,curr_nf()->eye_y,curr_nf()->eye_z);
    txt="Misli - ";
    //d(curr_nf()->name);
    txt+=curr_nf()->name;

    nt_w->setWindowTitle(txt);
}

int MisliInstance::next_nf()
{
    for(unsigned int i=0;i<(note_file.size()-1);i++){ //for every notefile without the last one
        if(current_note_file==note_file[i].id){//if it's the current one
            set_current_notes(note_file[i+1].id);
            gl_w->updateGL();
            return 0;
        }
    }

    return 1;
}
int MisliInstance::previous_nf()
{
    for(unsigned int i=1;i<(note_file.size());i++){ //for every notefile without the firs one
        if(current_note_file==note_file[i].id){//if it's the current one
            set_current_notes(note_file[i-1].id);
            gl_w->updateGL();
            return 0;
        }
    }

    return 1;
}

int MisliInstance::undo()
{
    std::fstream ntf;
    std::string str;

    std::vector<std::string> *nfz=curr_nf()->nf_z;

    if(curr_nf()->nf_z->size()>=2){

        ntf.open(curr_nf()->full_file_addr,std::ios_base::out); //open file
        curr_nf()->nf_z->pop_back(); //pop the current version
        ntf<<curr_nf()->nf_z->back(); //flush the first backup in

        ntf.close();


        //note_file.push_back(null_note_file);
        //new_nf=&note_file.back();

        set_current_notes(curr_nf()->init(this,curr_nf()->name,curr_nf()->full_file_addr)); //load the backup
        curr_nf()->nf_z=nfz;

        gl_w->updateGL();
        return 0;
    }else{return 1;}

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
int MisliInstance::copy()
{
    int err=0;
    int x=gl_w->mapFromGlobal( QCursor::pos() ).x();
    int y=gl_w->mapFromGlobal( QCursor::pos() ).y();

    while(clipboard_nf()->get_lowest_id_note()!=NULL){ //delete all notes in clipboard_nf()
        clipboard_nf()->delete_note(clipboard_nf()->get_lowest_id_note());
    }

    err+=copy_selected_notes(curr_nf(),clipboard_nf() ); //dumm copy the selected notes

    //make coordinates relative
    if(gl_w->get_note_under_mouse(x,y)!=NULL){ //to the note under the mouse if there's one
        clipboard_nf()->make_coords_relative_to(gl_w->get_note_under_mouse(x,y)->x,gl_w->get_note_under_mouse(x,y)->y);
    }else {
        clipboard_nf()->make_coords_relative_to(clipboard_nf()->get_lowest_id_note()->x,clipboard_nf()->get_lowest_id_note()->y);
    }

    return err;
}
int MisliInstance::cut()
{
    int err=0;

    err+=copy();
    err+=delete_selected();

    return err;
}
int MisliInstance::paste()
{
    NoteFile *nf=clipboard_nf();
    Note *nt;
    Link *ln;
    double x,y;
    int old_id;

    //Make all the id-s negative (and select all notes)
    for(unsigned int n=0;n<nf->note->size();n++){ //for every note
        nt=&(*nf->note)[n];
        nt->id = -nt->id;
        nt->selected=1;//for the copy later

        for(unsigned int l=0;l<nt->outlink.size();l++){
            ln=&nt->outlink[l];
            ln->id= -ln->id;
        }
        for(unsigned int in=0;in<nt->inlink.size();in++){ //for every inlink
            nt->inlink[in]= -nt->inlink[in]; //if it has the old id - set it up with the new one
        }
    }

    //Make coordinates relative to the mouse
    x=gl_w->mapFromGlobal( QCursor::pos() ).x(); //get mouse coords
    y=gl_w->mapFromGlobal( QCursor::pos() ).y();
    gl_w->unproject_to_plane(0,x,y,x,y); //translate them to real GL coords
    nf->make_coords_relative_to(-x,-y);

    //Copy the notes over to the target
    copy_selected_notes(clipboard_nf(),curr_nf());

    //return clipboard notes' coordinates to 0
    nf->make_coords_relative_to(x,y);

    nf=curr_nf();

    //Replace the negative id-s with real ones
    for(unsigned int n=0;n<nf->note->size();n++){ //for every note
        nt=&(*nf->note)[n];
        old_id = nt->id;
        nt->id = nf->get_new_id();

        //Fix the id-s in the links
        for(unsigned int i=0;i<nf->note->size();i++){ //for every note
            for(unsigned int l=0;l<(*nf->note)[i].outlink.size();l++){ //for every outlink
                ln=&(*nf->note)[i].outlink[l];
                if(ln->id==old_id){ ln->id=nt->id ; } //if it has the old id - set it up with the new one
            }
            for(unsigned int in=0;in<(*nf->note)[i].inlink.size();in++){ //for every inlink
                if((*nf->note)[i].inlink[in]==old_id){ (*nf->note)[i].inlink[in]=nt->id ; } //if it has the old id - set it up with the new one
            }
        }
        nt->init();
        nt->init_links();
    }

    nf->save();
    gl_w->updateGL();
    return 0;
}
int MisliInstance::init_notes_files()
{
    QDir dir(notes_dir);
    NoteFile *nf;

    QStringList strl = dir.entryList();
    std::vector<QString> entry_list = strl.toVector().toStdVector(); //I know vectors ,so why not
    QString entry,file_addr;

    int n=-1;
    for(unsigned int i=0;i<entry_list.size();i++){

        entry=entry_list[i];

        if(entry.size()==0) break;

        if( entry.endsWith(QString(".misl")) ){ //only for .misl files

            n++;

            file_addr=dir.absoluteFilePath(entry);
            entry=q_get_text_between(entry.toUtf8().data(),0,'.',200);
            entry=entry.trimmed();

            note_file.push_back(null_note_file);  //new object . It's important to make it first , because when the
                                                //notes get added they get a pointer to their parent note file and if
                                                //that's nf it gets destructed on function end..then Seg.F.
            nf=&note_file.back();

            nf->init(this,entry.toUtf8().data(),file_addr.toUtf8().data());
            nf->save(); //should be only virtual save for ctrl-z

        }

    }

    if(n==-1){ //if n=-1 directory empty , make default notes file

        make_notes_file("notes");

        file_addr=notes_dir;
        file_addr+="/";
        file_addr+="notes.misl";

        note_file.push_back(null_note_file); //nov obekt (vajno e pyrvo da go napravim ,za6toto pri dobavqneto na notes se zadava pointer kym note-file-a i toi trqbva da e kym realniq nf vyv vectora
        nf=&note_file.back();

        nf->init(this,"notes",file_addr.toUtf8().data());
    }

    if(default_nf_on_startup()!=NULL){current_note_file=default_nf_on_startup()->id;} //if a default is set - use it
    set_current_notes(current_note_file);
    emit notes_ready();

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
            if(note_file[i].is_displayed_first_on_startup!=false){
                note_file[i].is_displayed_first_on_startup=false;
                note_file[i].save();
            }
        }
        else{
            if(note_file[i].is_displayed_first_on_startup!=true){
                note_file[i].is_displayed_first_on_startup=true;
                note_file[i].save();
            }
        }
    }
}

void MisliInstance::make_this_the_default_viewpoint()
{
    curr_nf()->make_coords_relative_to(eye.x,eye.y);
    curr_nf()->init_notes();
    curr_nf()->init_links();
    curr_nf()->save();
    eye.x=0;
    eye.y=0;
    eye.scenex=0;
    eye.sceney=0;
}

int MisliInstance::delete_selected()
{
    return curr_nf()->delete_selected();
}
