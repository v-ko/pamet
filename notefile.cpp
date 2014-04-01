/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <fstream>
#include <QString>
#include <QDesktopWidget>
#include <QDebug>

#include "petko10.h"
#include "note.h"
#include "notefile.h"
#include "common.h"
#include "misliinstance.h"
#include "misli_desktop/misliwindow.h"
#include "misli_desktop/mislidesktopgui.h"

NoteFile::NoteFile(MisliDir *misli_dir_)
{
    misli_dir=misli_dir_;

    //Clear the variables
    last_note_id=0;
    is_displayed_first_on_startup=0;
    eye_x=0;
    eye_y=0;

    eye_z=INITIAL_EYE_Z;

    if(misli_dir!=NULL){
        if(misli_dir->misli_i!=NULL){
            eye_z=misli_dir->misli_i->misli_dg->settings->value("eye_z").toFloat();
        }
    }

    is_deleted_externally=0;
    is_current=false;
}
NoteFile::~NoteFile()
{
    for(unsigned int i=0;i<note.size();i++){
        delete note[i];
    }
}

QString NoteFile::init(QString path) //returns the id of the nf
{
    qDebug()<<"Initializing nf: "<<path;

    //if(misli_dir->using_gui){ //adjusting the height based on display size
    //    eye_z = 0.22 * misli_dir->misli_i->misli_dg->desktop()->widthMM();
    //} //this was a try at auto-adjusting height according to screen size - fail

    if(!misli_dir->is_virtual) {
        //qDebug()<<"Adding path to fs_watch: "<<path;
        misli_dir->fs_watch->addPath(path); //if it's a real nf
    }

    //----extract file name--------
    QFileInfo f(path);
    QString fname;
    fname = f.fileName();
    fname.chop(5); // ".misl".size()==5
    fname=fname.trimmed();

    //----Init-----
    init(fname,path);

    return fname;
}

int NoteFile::init(QString ime, QString path)   //returns negative on errors
{
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
    if(!ntFile.open(QIODevice::ReadOnly)){
        qDebug()<<"Error opening notefile: "<<path;
        return -2;
    }
    //----Check for abnormally large files------
    if(ntFile.size()>100000){
        qDebug()<<"Note file "<<ime<<" is more than 10MB.Skipping.";
        return -3;
    }
    qbytear = ntFile.readAll();
    //qDebug()<<qbytear;
    ntFile.close();
    file=file.fromUtf8(qbytear.data());



    file = file.replace("\r",""); //clear the windows standart debree
    //qDebug()<<file;
    lines = file.split(QString("\n"),QString::SkipEmptyParts);

    //------------Class initialisations---------------

    last_note_id=0;
    //misli_dir=misli_dir_; //eto tuk se preebava predniq notefile (comment,last note id i ime i note), po-to4no pointer-a na note-ovete v nego (nf) so4i kym preeban obekt ,na koito samo full_file_addr ba4ka

    name=ime;
    full_file_addr=path;
    select_all_notes();
    delete_selected();
    comment.clear();

    //=================The parser========================== da e funkciq

    //-------Get the comments and tags--------
    for(int i=0;i<lines.size();i++){ //for every line of text
        //qDebug()<<lines[i];
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
        //qDebug()<<groups[i];
            txt.replace(QString("\\n"),QString("\n"));
            //qDebug()<<txt;
        err += q_get_value_for_key(groups[i],"x",x);
        err += q_get_value_for_key(groups[i],"y",y);
        err += q_get_value_for_key(groups[i],"z",z);
        err += q_get_value_for_key(groups[i],"a",a);
        a = stop(a,MIN_NOTE_A,MAX_NOTE_A); //values should be btw 1-1000
        err += q_get_value_for_key(groups[i],"b",b);
        b = stop(b,MIN_NOTE_B,MAX_NOTE_B);
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

        if(err==0) add_note(nt_id,txt,x,y,z,a,b,font_size,t_made,t_mod,txt_col,bg_col);

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

    qDebug()<<"Init done.";
    return 0;
}
int NoteFile::init_links(){ //init all the links in the note_file notes

    for(unsigned int i=0;i<note.size();i++)
    {
        note[i]->init_links();
    }

return 0;
}

int NoteFile::init_notes(){ //init all the links in the note_file notes

    for(unsigned int i=0;i<note.size();i++)
    {
        note[i]->init();
    }

return 0;
}

int NoteFile::virtual_save(){ //save the notes to their file

    Note *nt;
    QString txt;

    std::stringstream sstr;

    for(unsigned int c=0;c<comment.size();c++)//adding the comments
    {
        sstr<<comment[c].toUtf8().data()<<'\n';
    }

    if(is_displayed_first_on_startup){
        sstr<<"is_displayed_first_on_startup"<<'\n';
    }

    for(unsigned int i=0;i<note.size();i++){

        nt=note[i];

        sstr<<"["<<nt->id<<"]"<<'\n';
        txt=nt->text;
        txt.replace(QString("\n"),QString("\\n"));
        sstr<<"txt="<<txt.toUtf8().data()<<'\n';//
        sstr<<"x="<<nt->x<<'\n';
        sstr<<"y="<<nt->y<<'\n'; //tuk slaga6 miuns za convertiraneto
        sstr<<"z="<<nt->z<<'\n';
        sstr<<"a="<<nt->a<<'\n';
        sstr<<"b="<<nt->b<<'\n';
        sstr<<"font_size="<<nt->font_size<<'\n';
        sstr<<"t_made="<<nt->t_made.toString("d.M.yyyy H:m:s").toUtf8().data()<<'\n';
        sstr<<"t_mod="<<nt->t_mod.toString("d.M.yyyy H:m:s").toUtf8().data()<<'\n';
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
            sstr<<nt->outlink[l].text.toUtf8().data()<<";";
        }
        sstr<<'\n';

    }

    nf_z.push_back(sstr.str());
    if(nf_z.size()>MAX_UNDO_STEPS){ //max undo steps
        nf_z.erase(nf_z.begin()); //erase the oldest
    }

    return 0;
}
int NoteFile::hard_save()
{
    std::fstream ntFile;

    if( is_not_system() ){ //for example for the copyPasteCut note file
        if(!misli_dir->is_virtual) misli_dir->fs_watch->removePath(full_file_addr);
        ntFile.open(full_file_addr.toUtf8().data(),std::ios_base::out|std::ios::binary);
        ntFile<<nf_z.back();
        ntFile.close();
        if(!misli_dir->is_virtual) {
            //qDebug()<<"Adding path to fs_watch: "<<full_file_addr;
            misli_dir->fs_watch->addPath(full_file_addr);
        }
        //qDebug()<<misli_dir->fs_watch->files();
    }

    return 0;
}
int NoteFile::save() //save the notes to their file
{
    virtual_save();
    hard_save();

    return 0;
}
int NoteFile::undo()
{
    std::fstream ntf;

    if(nf_z.size()>=2){

        nf_z.pop_back(); //pop the current version
        hard_save();

        init(name,full_file_addr);

        misli_dir->set_current_note_file(name); //load the backup

        return 0;
    }else{
        return 1;
    }

}
void NoteFile::find_free_ids()
{
    free_id.clear();
    for(int i=1;i<last_note_id;i++){ //for all ids to the last (exclude zero! when copying negative ids are used)
        if(get_note_by_id(i)==NULL){ //if there's no note on it
            free_id.push_back(i); //add the id to the list
        }
    }
}

Note *NoteFile::add_note_base(QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]){ //common parameters for all addnote functions

    Note *nt = new Note;
    QDateTime t_default(QDate(2013,3,8),QTime(0,0,0));//date on which I fixed the property ... (I introduced it ~18.11.2012)

    if(!t_made.isValid()){t_made=t_default;}
    if(!t_mod.isValid()){t_mod=t_default;}

    //Hard written stuff
    nt->text = text;
    nt->x = x;
    nt->y = y;
    nt->z = z;
    nt->a = a;
    nt->b = b;
    nt->font_size = font_size;
    nt->t_made=t_made;
    nt->t_mod=t_mod;
    nt->txt_col[0]=txt_col[0];
    nt->txt_col[1]=txt_col[1];
    nt->txt_col[2]=txt_col[2];
    nt->txt_col[3]=txt_col[3];
    nt->bg_col[0]=bg_col[0];
    nt->bg_col[1]=bg_col[1];
    nt->bg_col[2]=bg_col[2];
    nt->bg_col[3]=bg_col[3];

    //Program stuff
    nt->selected=false;
    nt->misli_dir=misli_dir; //that's a static object we can point to , the nf in the the vector is apparently not
    nt->nf_name=name;

    note.push_back(nt);

    return note.back();
}
Note *NoteFile::add_note(int id,QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]){ //import a note (one that has an id)

    //=======Dobavqne v programata=========
    //qDebug()<<text;
    Note *nt=add_note_base(text,x,y,z,a,b,font_size,t_made,t_mod,txt_col,bg_col);

    nt->id=id;
    if(id>last_note_id){last_note_id=id;}

    nt->init();

    return nt;
}
Note *NoteFile::add_note(QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]){ //completely new note (assign new id)

//=======Dobavqne v programata=========

Note *nt=add_note_base(text,x,y,z,a,b,font_size,t_made,t_mod,txt_col,bg_col);

nt->id=get_new_id();

nt->init();

return nt;
}
Note *NoteFile::add_note(Note *nt)
{
    Note * nt2 = add_note(nt->id,nt->text,nt->x,nt->y,nt->z,nt->a,nt->b,nt->font_size,nt->t_made,nt->t_mod,nt->txt_col,nt->bg_col);
    nt2->misli_dir=nt->misli_dir; //presesrve that , this function is used for copying , not adding
    nt2->nf_name=name;
    return nt2;
}

int NoteFile::delete_note(unsigned int position) //delete note at the given vector position
{
    Note *nt=note[position];
    Note *source_nt;

    //delete associated links
    for(unsigned int i=0;i<nt->inlink.size();i++){ //remove the out-links from the note

        source_nt=get_note_by_id(nt->inlink[i]); //find the note that the link comes from
        if(source_nt!=NULL){
            for(unsigned int l=0;l<source_nt->outlink.size();l++){ //find the link to remove from that note

                if(source_nt->outlink[l].id==nt->id){ source_nt->outlink.erase(source_nt->outlink.begin()+l); } //remove the link if it has the id of the link we're deleting

            }
        }

    }

    for(unsigned int i=0;i<nt->outlink.size();i++){ //removing the in-links on the remote notes that the outlinks correspond to

        source_nt=get_note_by_id(nt->outlink[i].id); //find the note the outlink points to
        if(source_nt!=NULL){
            for(unsigned int l=0;l<source_nt->inlink.size();l++){ //there we find the inlink we want to remove

                if(source_nt->inlink[l]==nt->id){ source_nt->inlink.erase(source_nt->inlink.begin()+l); } //remove the inlink if it has the id of the outlink we're deleting

            }
        }
    }

    delete nt;
    note.erase(note.begin()+position);

return 0;
}
int NoteFile::delete_note(Note *nt)
{
    unsigned int position;
    bool note_found=false;

    for(unsigned int i=0;i<note.size();i++){ //find actual position by comparing pointers directly
        if(nt==note[i]){position=i;note_found=true;}
    }

    if(!note_found){d("at delete_note : trying to delete a note that doesn't belong to this notefile");exit(66);}

    return delete_note(position);
}
int NoteFile::delete_selected() //deletes all marked selected and returns their number
{
    int deleted_items=0;

    while(get_first_selected_note()!=NULL){ //delete selected notes
    delete_note( get_first_selected_note() );
    deleted_items++;
    }

    for(unsigned int i=0;i<note.size();i++){ //for every note
        for(unsigned int l=0;l<note[i]->outlink.size();l++){ //for every outlink in the note
            if(note[i]->outlink[l].selected==true){ //if it's selected
                note[i]->delete_link(l); //delete it
                deleted_items++;
                l=0; //when a link is deleted the items in the vector get shifted and we must restart the loop in order to correctly delete a second selected link in the same note
                i--;
                break;
            }
        }
    }

    return deleted_items;
}

Note *NoteFile::get_first_selected_note(){ //returns first (in the vector arrangement) selected note

    for(unsigned int i=0;i<note.size();i++){
            if(note[i]->selected){return note[i];}
    }

return NULL;
}

Note *NoteFile::get_lowest_id_note()
{
    if(note.size()==0){return NULL;}

    int lowest_id=note[0]->id; //we assume the first note
    for(unsigned int i=1;i<note.size();i++){ //for the rest of the notes
        if( note[i]->id<lowest_id ){
            lowest_id=note[i]->id;
        }
    }
    return get_note_by_id(lowest_id);
}
Note *NoteFile::get_note_by_id(int id){ //returns the note with the given id

    for(unsigned int i=0;i<note.size();i++){

        if( note[i]->id==id ){return note[i];} //ako id-to syvpada vyrni pointera kym toq note

    }
    //qDebug()<<"Note with id: "<<id<<" not found.";
    return NULL;
}
void NoteFile::select_all_notes()
{
    for(unsigned int i=0;i<note.size();i++)
    {
        note[i]->selected=true;
    }
}

void NoteFile::clear_note_selection(){ //clears all notes' selection property to false

    for(unsigned int i=0;i<note.size();i++)
    {
        note[i]->selected=false;
    }

}
void NoteFile::clear_link_selection(){

for(unsigned int i=0;i<note.size();i++){
    for(unsigned int l=0;l<note[i]->outlink.size();l++){
        note[i]->outlink[l].selected=false;
    }
}

}
void NoteFile::make_coords_relative_to(double x,double y)
{
    Note *nte;

    for(unsigned int i=0;i<note.size();i++){ //for every note

        nte=note[i];

        nte->x-=x;
        nte->y-=y;
    }
}

void NoteFile::make_all_ids_negative()
{
    Note *nt;
    Link *ln;

    for(unsigned int n=0;n<note.size();n++){ //for every note
        nt=note[n];
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
bool NoteFile::is_not_system()
{
    if( ( name!=QString("ClipboardNf") ) && ( name!=QString("HelpNoteFile") )){
        return true;
    }else{
        return false;
    }
}
bool NoteFile::isEmpty()
{
    if(note.size()==0) return true;
    else return false;
}
