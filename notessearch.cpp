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

#include <algorithm>

#include "notessearch.h"

NotesSearch::NotesSearch()
{
}

int NotesSearch::loadNotes(MisliInstance *misliInstance, float initial_probability)
{
    int notes_loaded=0;

    for(MisliDir* misliDir: misliInstance->misliDirs()  ){
        notes_loaded += loadNotes(misliDir,initial_probability);
    }
    return notes_loaded;
}
int NotesSearch::loadNotes(MisliDir *misliDir, float initial_probability)
{
    int notes_loaded=0;
    SearchItem searchItem;

    //Clear all items from this MisliDir if there are any
    QMutableListIterator<SearchItem> searchItemIterator(searchItems);
    while(searchItemIterator.hasNext()){
        searchItem = searchItemIterator.next();
        if(searchItem.md==misliDir) searchItemIterator.remove();
    }

    for(auto nf: misliDir->noteFiles()){
        notes_loaded += loadNotes(nf, misliDir, initial_probability);
    }
    return notes_loaded;
}
int NotesSearch::loadNotes(NoteFile *noteFile, MisliDir* misliDir, float initial_probability)
{
    int notes_loaded=0;
    SearchItem searchItem;

    //Clear all items from this NF if there are any
    QMutableListIterator<SearchItem> searchItemIterator(searchItems);
    while(searchItemIterator.hasNext()){
        searchItem = searchItemIterator.next();
        if(searchItem.nf==noteFile) searchItemIterator.remove();
    }

    //(Re)load all items
    for(Note *nt: noteFile->notes){
        //if(nt->type!=NoteType::textFile){ //don't search through the text files (too large)
        searchItem.nt=nt;
        searchItem.probability=initial_probability;
        searchItem.nf = noteFile;
        searchItem.md = misliDir;
        searchItems.push_back(searchItem);
        notes_loaded++;
        //}
    }
    return notes_loaded;
}

int NotesSearch::rowCount(const QModelIndex &) const
{
    return searchResults.size();
}
QVariant NotesSearch::data(const QModelIndex & index, int role) const
{
    if(role==Qt::DisplayRole) return searchResults.at(index.row()).nt->text();
    return QVariant();
}
void NotesSearch::findByText(QString searchString)
{
    searchResults.clear();
    if(searchString.isEmpty()){
        emit searchComplete("");
        return;
    }

    QString tmp_search_string,tmp_note_string;
    
    searchResults = searchItems;
    QMutableListIterator<SearchItem> searchResultsIterator(searchResults);
    while(searchResultsIterator.hasNext()){
        SearchItem currentItem = searchResultsIterator.next();

        //Full match in the beginning (no capitals)
        tmp_search_string = searchString.toLower();
        tmp_note_string = currentItem.nt->text().toLower();

        //Full match somewhere else (no capitals)
        if(tmp_note_string.startsWith(tmp_search_string)){
            currentItem.probability = currentItem.probability*1; //100% (just for readability)
        }else if(tmp_note_string.contains(tmp_search_string)){
            currentItem.probability = currentItem.probability*0.9; //90%
            continue;
        }else{
            searchResultsIterator.remove();
            //Partial matches
            //if(){}
        }
    }
    std::sort(searchResults.begin(),searchResults.end(),compareItems); //order by probability

    emit dataChanged(index(0,0),index(searchResults.size()-1,0)); //all of the data has changed
}

bool NotesSearch::compareItems(SearchItem first, SearchItem second)
{
    return first.probability>second.probability;
}
