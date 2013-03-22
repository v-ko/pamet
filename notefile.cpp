/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <fstream>
#include <QString>
#include <QApplication>
#include <QDesktopWidget>
#include <GL/gl.h>

#include "../../petko10.h"
#include "note.h"
#include "notefile.h"
#include "common.h"
#include "misliinstance.h"
#include "misliwindow.h"

NoteFile::NoteFile()
{
    last_note_id=0;
    is_displayed_first_on_startup=0;
    eye_x=0;
    eye_y=0;
    eye_z=INITIAL_EYE_Z;
    deleted=0;

    note = new NotesVector;
    nf_z = new std::vector<std::string>;
}
int NoteFile::init(MisliInstance *m_i,QString ime,QString path){ //returns the id of the nf

    m_i->last_nf_id++;
    id=m_i->last_nf_id;

    m_i->fs_watch->addPath(path);//if it's a real nf
    init(m_i,ime,path,id);
    return id;
}

int NoteFile::init(MisliInstance *m_i,QString ime,QString path,int id_){  //returns errors

    //Tmp , function stuff
    Link ln;
    Note *nt,*target_nt;

    QFile ntFile(path);
    QString file,tmpqstr;
    QByteArray qbytear;
    QStringList lines,groups,group_names,l_id,qtxt_col,qbg_col;

    int err=0;

    //-------------Note properties---------------------
    int nt_id=0;
    QString txt;
    float x,y,z,a,b,font_size;
    QDateTime t_made,t_mod;
    float txt_col[4],bg_col[4]; //text and background colors

    //----Open file------
    if(!ntFile.open(QIODevice::ReadOnly)){d("error opening ntFile");return -2;}
    qbytear = ntFile.readAll();
    ntFile.close();
    file=file.fromUtf8(qbytear.data());

    file = file.replace("\r",""); //clear the windows standart debree
    lines = file.split(QString("\n"),QString::SkipEmptyParts);

    //------------Class initialisations---------------

    id=id_;
    last_note_id=0;
    misl_i=m_i; //eto tuk se preebava predniq notefile (comment,last note id i ime i note), po-to4no pointer-a na note-ovete v nego (nf) so4i kym preeban obekt ,na koito samo full_file_addr ba4ka

    name=ime;
    full_file_addr=path;
    note->clear();
    comment.clear();

    if(misl_i->using_external_classes){
        eye_z = 0.22 * misl_i->msl_w->a->desktop()->widthMM();
    }

    if(name==QString("HelpNoteFile")){

    }

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
        if(q_get_value_for_key(groups[i],"t_made",tmpqstr)==0){
            t_made=t_made.fromString(tmpqstr,"d.M.yyyy H:m:s");
        }else t_made = t_made.currentDateTime();
        if(q_get_value_for_key(groups[i],"t_mod",tmpqstr)==0){
            t_mod=t_mod.fromString(tmpqstr,"d.M.yyyy H:m:s");
        }else t_mod = t_made.currentDateTime();
        if(q_get_value_for_key(groups[i],"txt_col",qtxt_col)==-1){
            qtxt_col.clear();
            qtxt_col.push_back("0");
            qtxt_col.push_back("0");
            qtxt_col.push_back("1");
            qtxt_col.push_back("1");
        }
        txt_col[0]=qtxt_col[0].toFloat();
        txt_col[1]=qtxt_col[1].toFloat();
        txt_col[2]=qtxt_col[2].toFloat();
        txt_col[3]=qtxt_col[3].toFloat();

        if(q_get_value_for_key(groups[i],"bg_col",qbg_col)==-1){
            qbg_col.clear();
            qbg_col.push_back("0");
            qbg_col.push_back("0");
            qbg_col.push_back("1");
            qbg_col.push_back("0.1");
        }
        bg_col[0]=qbg_col[0].toFloat();
        bg_col[1]=qbg_col[1].toFloat();
        bg_col[2]=qbg_col[2].toFloat();
        bg_col[3]=qbg_col[3].toFloat();

        if(err==0) add_note(misl_i,nt_id,txt,x,y,z,a,b,font_size,t_made,t_mod,txt_col,bg_col);

    }

    for(int i=0;i<groups.size();i++){ //get the links

        nt_id = group_names[i].toInt();
        nt=get_note_by_id(nt_id);

        err += q_get_value_for_key(groups[i],"l_id",l_id);

        for(int l=0;l<l_id.size();l++){ //getting the links in the notes
            ln=Link(); //construct *clean that
            ln.id=l_id[l].toInt(); //vkarvame id
            nt->outlink.push_back(ln); //dobavqme linka

            if(get_note_by_id(ln.id)!=NULL){
                target_nt=get_note_by_id(ln.id); //namirame target note-a na tozi link

                target_nt->inlink.push_back(nt->id); //vkarvame v inlist-a mu syotvetnoto id
            }
        }
    }

find_free_ids();

init_links();

return 0;
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

    sstr<<comment[c].toUtf8().data()<<'\n';

}

if(is_displayed_first_on_startup){
    sstr<<"is_displayed_first_on_startup"<<'\n';
}

for(unsigned int i=0;i<note->size();i++){

    nt=&(*note)[i];

    sstr<<"["<<nt->id<<"]"<<'\n';
    txt=nt->text;
    txt.replace(QString("\n"),QString("\\n"));
    sstr<<"txt="<<txt.toStdString()<<'\n';//
    sstr<<"x="<<nt->x<<'\n';
    sstr<<"y="<<nt->y<<'\n'; //tuk slaga6 miuns za convertiraneto
    sstr<<"z="<<nt->z<<'\n';
    sstr<<"a="<<nt->a<<'\n';
    sstr<<"b="<<nt->b<<'\n';
    sstr<<"font_size="<<nt->font_size<<'\n';
    sstr<<"t_made="<<nt->t_made.toString("d.M.yyyy H:m:s").toStdString()<<'\n';
    sstr<<"t_mod="<<nt->t_mod.toString("d.M.yyyy H:m:s").toStdString()<<'\n';
    sstr<<"txt_col="<<nt->txt_col[0]<<";"<<nt->txt_col[1]<<";"<<nt->txt_col[2]<<";"<<nt->txt_col[3]<<'\n';
    sstr<<"bg_col="<<nt->bg_col[0]<<";"<<nt->bg_col[1]<<";"<<nt->bg_col[2]<<";"<<nt->bg_col[3]<<'\n';

    sstr<<"l_id=";
    for(unsigned int l=0;l<nt->outlink.size();l++){
        sstr<<nt->outlink[l].id<<";";
    }
    sstr<<'\n';

    sstr<<"l_txt=";
    for(unsigned int l=0;l<nt->outlink.size();l++){
        //Remove ";"s from the text to avoid breaking the ini standard
        nt->outlink[l].text.replace(QString(";"),QString(":"));;

        //Save the text
        sstr<<nt->outlink[l].text.toStdString()<<";";
    }
    sstr<<'\n';

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
        misl_i->fs_watch->removePath(full_file_addr);
        ntFile.open(full_file_addr.toStdString().c_str(),std::ios_base::out|std::ios::binary);
        ntFile<<nf_z->back();
        ntFile.close();
        misl_i->fs_watch->addPath(full_file_addr);
    }

return 0;
}
void NoteFile::find_free_ids()
{
    free_id.clear();
    for(int i=0;i<last_note_id;i++){ //for all ids to the last
        if(get_note_by_id(i)==NULL){ //if there's no note on it
            free_id.push_back(i); //add the id to the list
        }
    }
}

Note *NoteFile::add_note_base(MisliInstance *m_i,QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]){ //common parameters for all addnote functions

Note nt;
QDateTime t_default(QDate(2013,3,8),QTime(0,0,0));//date on which I fixed the property ... (I introduced it ~18.11.2012)

if(!t_made.isValid()){t_made=t_default;}
if(!t_mod.isValid()){t_mod=t_default;}

//Hard written stuff
nt.text = text;
nt.x = x;
nt.y = y;
nt.z = z;
nt.a = a;
nt.b = b;
nt.font_size = font_size;
nt.t_made=t_made;
nt.t_mod=t_mod;
nt.txt_col[0]=txt_col[0];
nt.txt_col[1]=txt_col[1];
nt.txt_col[2]=txt_col[2];
nt.txt_col[3]=txt_col[3];
nt.bg_col[0]=bg_col[0];
nt.bg_col[1]=bg_col[1];
nt.bg_col[2]=bg_col[2];
nt.bg_col[3]=bg_col[3];

//Program stuff
nt.selected=false;
nt.misl_i=m_i; //that's a static object we can point to , the nf in the the vector is apparently not
nt.nf_id=id;

note->push_back(nt);

return &(*note)[note->size()-1];

}
Note *NoteFile::add_note(MisliInstance *m_i,int id,QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]){ //import a note (one that has an id)

//=======Dobavqne v programata=========

Note *nt=add_note_base(m_i,text,x,y,z,a,b,font_size,t_made,t_mod,txt_col,bg_col);

nt->id=id;
if(id>last_note_id){last_note_id=id;}

nt->init();

return nt;
}
Note *NoteFile::add_note(MisliInstance *m_i,QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]){ //completely new note (assign new id)

//=======Dobavqne v programata=========

Note *nt=add_note_base(m_i,text,x,y,z,a,b,font_size,t_made,t_mod,txt_col,bg_col);

nt->id=get_new_id();

nt->init();

return nt;
}
Note *NoteFile::add_note(Note *nt)
{
    return add_note(nt->misl_i,nt->id,nt->text,nt->x,nt->y,nt->z,nt->a,nt->b,nt->font_size,nt->t_made,nt->t_mod,nt->txt_col,nt->bg_col);
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
