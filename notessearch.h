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

#ifndef NOTESSEARCH_H
#define NOTESSEARCH_H

#include <QObject>

#include "misliinstance.h"

class NotesSearch : public QObject
{
    Q_OBJECT
public:
    //Functions
    NotesSearch();
    int load_notes(MisliInstance * misli_i_,float initial_probability);
    int load_notes(MisliDir * misli_dir_,float initial_probability);
    int load_notes(NoteFile * note_file_,float initial_probability);
    
signals:
    void search_complete(QString string);
    
public slots:
    void find_by_text(QString string);
    void order_by_probability();
    
    //Variables    
private:
    MisliInstance * misli_i;
    MisliDir *misli_dir;
    NoteFile *note_file;
    


public:
    struct SearchResult{
        Note *nt;
        float probability;
    };

    std::vector<SearchResult> search_results;
    
};

#endif // NOTESSEARCH_H
