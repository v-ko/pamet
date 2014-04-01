/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "misliinstance.h"
#include "misli_desktop/misliwindow.h"
#include "ui_misliwindow.h"
#include "misli_desktop/mislidesktopgui.h"
#include "canvas.h"

MisliInstance::MisliInstance(MisliDesktopGui *misli_dg_)
{
    misli_dg = misli_dg_;
    //misli_w=NULL; //It gets constructed afterwards

    if(misli_dg==NULL){
        using_gui=false;
    }else{
        using_gui=true;
    }

    settings = new QSettings;

    search_notes_dir = new MisliDir("",this,using_gui);
    search_nf = new NoteFile(search_notes_dir);
}
MisliInstance::~MisliInstance()
{
    for(unsigned int i=0;i<misli_dir.size();i++){
        delete misli_dir[i];
    }
    delete search_notes_dir;
    delete search_nf;
    delete settings;
}

bool MisliInstance::notes_rdy()
{
    if(misli_dir.size()>0){
        return true;
    }else{
        return false;
    }
}

void MisliInstance::add_dir(QString path)
{
    MisliDir * md= new MisliDir(path,this,using_gui);
    misli_dir.push_back(md);

    //Will uncomment it if I actually start using MisliInstance::error
    /*if(misli_dir.back()->error!=0){ //if the dir was loaded with errors - remove it
        qDebug()<<"Removing dir added with errors: "<<misli_dir.back()->notes_dir;
        misli_dir.pop_back();
        return;
    }*/

    if(using_gui){
        connect(md,SIGNAL(current_nf_switched()),misli_dg->misli_w,SLOT(switch_current_nf()));
        connect(md,SIGNAL(current_nf_updated()),misli_dg->misli_w,SLOT(update_current_nf()));
    }

    set_current_misli_dir(path);

    emit notes_dir_added(path);//to add a menu entry
}

int MisliInstance::load_all_dirs()
{
    int loaded_dirs=0;
    QStringList notes_dirs;

    //------Extract the directory paths from the settings----------
    if(settings->contains("notes_dir")){
        notes_dirs = settings->value("notes_dir").toStringList();
        qDebug()<<"Extracted notes dirs from settings:"<<notes_dirs;
    }

    //-------Load the directories------------------------
    if(notes_dirs.size()>0){
        for(int i=0;i<notes_dirs.size();i++){
            add_dir(notes_dirs[i]);
            loaded_dirs++;
        }
    }

    emit notes_dir_changed();
    emit load_all_dirs_finished();
    moveToThread(misli_dg->thread());//move back so there's no problems with the paint() accessing data while something else is editing the NFs

    return loaded_dirs;
}

void MisliInstance::set_current_misli_dir(QString path)
{
    for(unsigned int i=0;i<misli_dir.size();i++){
        if(misli_dir[i]->notes_dir==path){ //find the dir with path and set it as current
            misli_dir[i]->is_current=true;
        }else{
            misli_dir[i]->is_current=false; //all others are not current
        }
    }

    emit notes_dir_changed();
}
MisliDir * MisliInstance::curr_misli_dir()
{
    for(unsigned int i=0;i<misli_dir.size();i++){
        if(misli_dir[i]->is_current){
            return misli_dir[i];
        }
    }
    return NULL;
}

void MisliInstance::move_back_to_main_thread()
{
    moveToThread(misli_dg->thread());
}

int MisliInstance::load_results_in_search_nf()
{
    if(!using_gui){return 0;}

    Note *nt;

    search_nf->select_all_notes();
    search_nf->delete_selected();

    for(unsigned int i=0;i<misli_dg->notes_search->search_results.size();i++){
        nt = search_nf->add_note(misli_dg->notes_search->search_results[i].nt);
        //preserve the original nf name in order to track it
        nt->nf_name = misli_dg->notes_search->search_results[i].nt->nf_name;
        nt->a=misli_dg->misli_w->canvas->searchField->width()/FONT_TRANSFORM_FACTOR;
        nt->b=SEARCH_RESULT_HEIGHT/FONT_TRANSFORM_FACTOR;
        nt->calculate_coordinates(); //circumvent the "!using GUI" skipping on init()
        nt->check_text_for_links(curr_misli_dir());
        nt->adjust_text_size();
        nt->draw_pixmap();
    }
    return 0;
}
