/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <fstream>
#include <QString>
#include <GL/gl.h>

#include "../../petko10.h"
#include "note.h"
#include "notefile.h"
#include "common.h"
#include "misliinstance.h"

NoteFile::NoteFile()
{
    last_note_id=0;
    is_displayed_first_on_startup=0;
    eye_x=0;
    eye_y=0;
    eye_z=100;
}
int NoteFile::init(MisliInstance *m_i,QString ime,QString path){

    m_i->last_nf_id++;
    id=m_i->last_nf_id;

    return init(m_i,ime,path,id);
}

int NoteFile::init(MisliInstance *m_i,QString ime,QString path,int id_){

    //Tmp , function stuff
    Link ln;
    Note *nt,*target_nt;

    QFile ntFile(path);
    QString file,tmpqstr;
    QByteArray qbytear;
    QStringList lines,groups,group_names,l_id;

    int err;

    //-------------Note properties---------------------
    int nt_id=0;
    QString txt;
    float x,y,z,a,b,font_size;
    QDate dt_made,dt_mod;

    //------------Class initialisations---------------
    id=id_;
    last_note_id=0;
    misl_i=m_i; //eto tuk se preebava predniq notefile (comment,last note id i ime i note), po-to4no pointer-a na note-ovete v nego (nf) so4i kym preeban obekt ,na koito samo full_file_addr ba4ka

    name=ime;
    full_file_addr=path;

    note = new NotesVector;
    nf_z = new std::vector<std::string>;

    //----Open file------
    if(!ntFile.open(QIODevice::ReadOnly)){d("error opening ntFile");exit(434);}
    qbytear = ntFile.readAll();
    ntFile.close();
    file=file.fromUtf8(qbytear.data());
    lines = file.split("\n",QString::SkipEmptyParts);


    //=================The parser========================== da e funkciq

    //-------Get the comments and tags--------
    for(int i=0;i<lines.size();i++){ //for every line of text
        if(lines[i].startsWith("#")){//if it's a comment
            comment.push_back(lines[i]);
        }
        if(lines[i].startsWith("is_displayed_first_on_startup")){
            is_displayed_first_on_startup=true;
            continue;
        }
    }


    //------Extract the groups(notes)----------
    if(q_get_groups(file,group_names,groups)!=1){d("error when extracting the groups");exit(43);}


    for(int i=0;i<groups.size();i++){ //get the notes

        nt_id = group_names[i].toInt();

        err += q_get_value_for_key(groups[i],"txt",txt);
            txt.replace(QString("\\n"),QString("\n"));
        err += q_get_value_for_key(groups[i],"x",x);
        err += q_get_value_for_key(groups[i],"y",y);
        err += q_get_value_for_key(groups[i],"z",z);
        err += q_get_value_for_key(groups[i],"a",a);
        err += q_get_value_for_key(groups[i],"b",b);
        err += q_get_value_for_key(groups[i],"font_size",font_size);
        err += q_get_value_for_key(groups[i],"dt_made",tmpqstr);
            dt_made=dt_made.fromString(tmpqstr,"d.M.yyyy");
        err += q_get_value_for_key(groups[i],"dt_mod",tmpqstr);
            dt_mod=dt_mod.fromString(tmpqstr,"d.M.yyyy");

        add_note(misl_i,nt_id,txt,x,y,z,a,b,font_size,dt_made,dt_mod);

    }

    for(int i=0;i<groups.size();i++){ //get the notes

        nt_id = group_names[i].toInt();
        nt=get_note_by_id(nt_id);

        err += q_get_value_for_key(groups[i],"l_id",l_id);

        for(int l=0;l<l_id.size();l++){ //getting the links in the notes
            ln=Link(); //construct *clean that
            ln.id=l_id[l].toInt(); //vkarvame id
            nt->outlink.push_back(ln); //dobavqme linka

            target_nt=get_note_by_id(ln.id); //namirame target note-a na tozi link

            target_nt->inlink.push_back(nt->id); //vkarvame v inlist-a mu syotvetnoto id
        }
    }

find_free_ids();

init_links();

return id;
}
int NoteFile::init_links(){ //init all the links in the note_file notes

    for(unsigned int i=0;i<note->size();i++){

        (*note)[i].init_links();

    }

return 0;
}

int NoteFile::init_notes(){ //init all the links in the note_file notes

    for(unsigned int i=0;i<note->size();i++){

        (*note)[i].init();

    }

return 0;
}

int NoteFile::virtual_save(){ //save the notes to their file

Note *nt;
QString txt;

std::stringstream sstr;

for(unsigned int c=0;c<comment.size();c++){ //adding the comments

    sstr<<comment[c].toUtf8().data()<<std::endl;

}

if(is_displayed_first_on_startup){
    sstr<<"is_displayed_first_on_startup"<<std::endl;
}

for(unsigned int i=0;i<note->size();i++){

    nt=&(*note)[i];

    sstr<<"["<<nt->id<<"]"<<std::endl;
    txt=nt->text;
    txt.replace(QString("\n"),QString("\\n"));
    sstr<<"txt="<<nt->text.toStdString()<<std::endl;//
    sstr<<"x="<<nt->x<<std::endl;
    sstr<<"y="<<nt->y<<std::endl;
    sstr<<"z="<<nt->z<<std::endl;
    sstr<<"a="<<nt->a<<std::endl;
    sstr<<"b="<<nt->b<<std::endl;
    sstr<<"font_size="<<nt->font_size<<std::endl;
    sstr<<"dt_made="<<nt->dt_made.toString("d.M.yyyy").toStdString()<<std::endl;
    sstr<<"dt_mod="<<nt->dt_mod.toString("d.M.yyyy").toStdString()<<std::endl;

    sstr<<"l_id=";
    for(unsigned int l=0;l<nt->outlink.size();l++){
        sstr<<nt->outlink[l].id<<";";
    }
    sstr<<std::endl;

    sstr<<"l_txt=";
    for(unsigned int l=0;l<nt->outlink.size();l++){
        //Remove ";"s from the text to avoid breaking the ini standard
        nt->outlink[l].text.replace(QString(";"),QString(":"));;

        //Save the text
        sstr<<nt->outlink[l].text.toStdString()<<";";
    }
    sstr<<std::endl;

}

nf_z->push_back(sstr.str());
if(nf_z->size()>MAX_UNDO_STEPS){ //max undo steps
    nf_z->erase(nf_z->begin()); //erase the oldest
}

misl_i->emit_current_nf_updated();

return 0;
}
int NoteFile::save(){ //save the notes to their file

    std::fstream ntFile;

    virtual_save();

    if(id>=0){ //for example for the copyPasteCut nf
        ntFile.open(full_file_addr.toStdString().c_str(),std::ios_base::out);
        ntFile<<nf_z->back();
        ntFile.close();
    }

return 0;
}
void NoteFile::find_free_ids()
{
    for(int i=0;i<last_note_id;i++){ //for all ids to the last
        if(get_note_by_id(i)==NULL){ //if there's no note on it
            free_id.push_back(i); //add the id to the list
        }
    }
}

Note *NoteFile::add_note_base(MisliInstance *m_i,QString text,double x,double y,double z,double a,double b,double font_size,QDate dt_made,QDate dt_mod){ //common parameters for all addnote functions

Note nt;
QDate dt_default(2013,2,23);//date on which I fixed the property ... (I introduced it ~18.11.2012)

if(!dt_made.isValid()){dt_made=dt_default;}
if(!dt_mod.isValid()){dt_mod=dt_default;}

//Hard written stuff
nt.text = text;
nt.x = x;
nt.y = y;
nt.z = z;
nt.a = a;
nt.b = b;
nt.font_size = font_size;
nt.dt_made=dt_made;
nt.dt_mod=dt_mod;

//Program stuff
nt.selected=false;
nt.misl_i=m_i; //that's a static object we can point to , the nf in the the vector is apparently not
nt.nf_id=id;
glGenTextures(1,&nt.texture);

note->push_back(nt);

return &(*note)[note->size()-1];

}
Note *NoteFile::add_note(MisliInstance *m_i,int id,QString text,double x,double y,double z,double a,double b,double font_size,QDate dt_made,QDate dt_mod){ //import a note (one that has an id)

//=======Dobavqne v programata=========

Note *nt=add_note_base(m_i,text,x,y,z,a,b,font_size,dt_made,dt_mod);

nt->id=id;
if(id>last_note_id){last_note_id=id;}

nt->init();

return nt;
}
Note *NoteFile::add_note(MisliInstance *m_i,QString text,double x,double y,double z,double a,double b,double font_size,QDate dt_made,QDate dt_mod){ //completely new note (assign new id)

//=======Dobavqne v programata=========

Note *nt=add_note_base(m_i,text,x,y,z,a,b,font_size,dt_made,dt_mod);

nt->id=get_new_id();

nt->init();

return nt;
}
Note *NoteFile::add_note(Note *nt)
{
    return add_note(nt->misl_i,nt->id,nt->text,nt->x,nt->y,nt->z,nt->a,nt->b,nt->font_size,nt->dt_made,nt->dt_mod);
}

int NoteFile::delete_note(unsigned int position){ //delete note at the given vector position

Note *nt=&(*note)[position];
Note *source_nt;
bool note_found=false;

for(unsigned int i=0;i<note->size();i++){ //namirame poziciqta 4rez direktno sravnqvane na pointeri
    if(nt==&(*note)[i]){position=i;note_found=true;}
}

if(!note_found){d("at delete_note : trying to delete a note that doesn't belong to this notefile");exit(66);}

//delete associated links
for(unsigned int i=0;i<nt->inlink.size();i++){ //mahame out-linkovete koito so4at kym tozi

    source_nt=get_note_by_id(nt->inlink[i]); //namirame note-a ot koito idva link-a
    for(unsigned int l=0;l<source_nt->outlink.size();l++){ //v nego namirame link-a za mahane

        if(source_nt->outlink[l].id==nt->id){ source_nt->outlink.erase(source_nt->outlink.begin()+l); } //mahame link-a ako e s id-to na link-a koito delete-vame

    }

}

for(unsigned int i=0;i<nt->outlink.size();i++){ //mahame in-linkovete kym koito so4at out linkovete na tozi koito iskame da del-nem

    source_nt=get_note_by_id(nt->outlink[i].id); //namirame note-a kym koito otiva link-a
    for(unsigned int l=0;l<source_nt->inlink.size();l++){ //v nego namirame link-a za mahane

        if(source_nt->inlink[l]==nt->id){ source_nt->inlink.erase(source_nt->inlink.begin()+l); } //mahame link-a ako e s id-to na link-a koito delete-vame

    }

}

note->erase(note->begin()+position);

save();

return 0;
}
int NoteFile::delete_note(Note *nt){

unsigned int position;
Note *source_nt;
bool note_found=false;

for(unsigned int i=0;i<note->size();i++){ //namirame poziciqta 4rez direktno sravnqvane na pointeri
    if(nt==&(*note)[i]){position=i;note_found=true;}
}

if(!note_found){d("at delete_note : trying to delete a note that doesn't belong to this notefile");exit(66);}

//delete associated links
for(unsigned int i=0;i<nt->inlink.size();i++){ //mahame out-linkovete koito so4at kym tozi

    source_nt=get_note_by_id(nt->inlink[i]); //namirame note-a ot koito idva link-a
    for(unsigned int l=0;l<source_nt->outlink.size();l++){ //v nego namirame link-a za mahane

        if(source_nt->outlink[l].id==nt->id){ source_nt->outlink.erase(source_nt->outlink.begin()+l); } //mahame link-a ako e s id-to na link-a koito delete-vame

    }

}

for(unsigned int i=0;i<nt->outlink.size();i++){ //mahame in-linkovete kym koito so4at out linkovete na tozi koito iskame da del-nem

    source_nt=get_note_by_id(nt->outlink[i].id); //namirame note-a kym koito otiva link-a
    for(unsigned int l=0;l<source_nt->inlink.size();l++){ //v nego namirame link-a za mahane

        if(source_nt->inlink[l]==nt->id){ source_nt->inlink.erase(source_nt->inlink.begin()+l); } //mahame link-a ako e s id-to na link-a koito delete-vame

    }

}

note->erase(note->begin()+position);

save();

return 0;
}
int NoteFile::delete_selected() //deletes all marked selected and returns their number
{
    int deleted_items=0;

    while(get_first_selected_note()!=NULL){ //delete selected notes
    delete_note( get_first_selected_note() );
    deleted_items++;
    }

    for(unsigned int i=0;i<note->size();i++){ //for every note
        for(unsigned int l=0;l<(*note)[i].outlink.size();l++){ //for every outlink in the note
            if((*note)[i].outlink[l].selected==true){ //if it's selected
                (*note)[i].delete_link(l); //delete it
                deleted_items++;
                l=0; //when a link is deleted the items in the vector get shifted and we must restart the loop in order to correctly delete a second selected link in the same note
                i--;
                break;
            }
        }
    }

    save();

    misl_i->gl_w->updateGL();

return deleted_items;
}

Note *NoteFile::get_first_selected_note(){ //returns first (in the vector arrangement) selected note

    for(unsigned int i=0;i<note->size();i++){
            if((*note)[i].selected){return &(*note)[i];}
    }

return NULL;
}

Note *NoteFile::get_lowest_id_note()
{
    if(note->size()==0){return NULL;}

    int lowest_id=(*note)[0].id; //we assume the first note
    for(unsigned int i=1;i<note->size();i++){ //for the rest of the notes
        if( (*note)[i].id<lowest_id ){
            lowest_id=(*note)[i].id;
        }
    }
    return get_note_by_id(lowest_id);
}
Note *NoteFile::get_note_by_id(int id){ //returns the note with the given id

for(unsigned int i=0;i<note->size();i++){

    if( (*note)[i].id==id ){return &(*note)[i];} //ako id-to syvpada vyrni pointera kym toq note

}

return NULL;
}
void NoteFile::clear_note_selection(){ //clears all notes' selection property to false

for(unsigned int i=0;i<note->size();i++){

    (*note)[i].selected=false;

}

}
void NoteFile::clear_link_selection(){

for(unsigned int i=0;i<note->size();i++){
    for(unsigned int l=0;l<(*note)[i].outlink.size();l++){
        (*note)[i].outlink[l].selected=false;
    }
}

}
void NoteFile::make_coords_relative_to(double x,double y)
{
    Note *nte;

    for(unsigned int i=0;i<note->size();i++){ //for every note

        nte=&(*note)[i];

        nte->x-=x;
        nte->y-=y;
    }
}

int NoteFile::get_new_id()
{
    int idd;

    if(free_id.size()!=0){
        idd =free_id.front();
        free_id.erase(free_id.begin());
    }else {
        last_note_id++;
        idd=last_note_id;
    }
    return idd;
}

void NoteFile::set_to_current()
{
    misl_i->set_current_notes(id);
}
