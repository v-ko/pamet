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

#include "notessearch.h"

NotesSearch::NotesSearch()
{
    
}

int NotesSearch::load_notes(MisliInstance *misli_i_, float initial_probability)
{
    int notes_loaded=0;
    misli_i=misli_i_;
    
    search_results.clear();
    for(unsigned int i=0;i<misli_i->misli_dir.size();i++){
        notes_loaded += load_notes(misli_i->misli_dir[i],initial_probability);
    }
    return notes_loaded;
}
int NotesSearch::load_notes(MisliDir *misli_dir_, float initial_probability)
{
    int notes_loaded=0;
    //misli_i=NULL;
    misli_dir=misli_dir_;
    
    //search_results.clear();
    for(unsigned int i=0;i<misli_dir->note_file.size();i++){
        if(misli_dir->note_file[i]->name != "HelpNoteFile"){
            notes_loaded += load_notes(misli_dir->note_file[i],initial_probability);
        }
    }
    return notes_loaded;
}
int NotesSearch::load_notes(NoteFile *note_file_, float initial_probability)
{
    int notes_loaded=0;
    SearchResult sr;
    
    //misli_i=NULL;
    //misli_dir=NULL;
    note_file=note_file_;
    
    //search_results.clear();
    for(unsigned int i=0;i<note_file->note.size();i++){
        if(note_file->note[i]->type!=NOTE_TYPE_TEXT_FILE_NOTE){ //don't search through the text files (too large)
            sr.nt=note_file->note[i];
            sr.probability=initial_probability;
            search_results.push_back(sr);
            notes_loaded++;
        }
    }
    return notes_loaded;
}

void NotesSearch::find_by_text(QString string)
{
    if(string.isEmpty()){
        search_results.clear();
        emit search_complete("");
        return;
    }

    QString tmp_search_string,tmp_note_string;
    
    for(unsigned int i=0;i<search_results.size();i++){
        
        //Full match in the beginning (no capitals)
        tmp_search_string=string.toLower();
        tmp_note_string=search_results[i].nt->text.toLower();
        
        if(tmp_note_string.startsWith(tmp_search_string)){
            //search_results[i].probability=search_results[i].probability*1; //100%
            continue;
        }else
            //Full match somewhere else (no capitals)
            if(tmp_note_string.contains(tmp_search_string)){
                search_results[i].probability=search_results[i].probability*0.9; //90%
                continue;
            }else search_results[i].probability=0;
                //Partial matches
                //if(){}
    }
    
    order_by_probability();
    
    emit search_complete(string);
}

void NotesSearch::order_by_probability()
{
    std::vector<SearchResult> sr;

    int best_prob,pos;
    SearchResult sr_best;
    
    sr=search_results;
    search_results.clear();
    
    while(sr.size()>0){ //while there are notes in to order
        
        best_prob=0;
        
        for(unsigned int i=0;i<sr.size();i++){ //find best result
            if(sr[i].probability>=best_prob){
                best_prob=sr[i].probability;
                sr_best = sr[i];
                pos=i;
            }
        }
        
        if(sr[pos].probability>0) search_results.push_back(sr_best);
        sr.erase(sr.begin()+pos);
    }

}
