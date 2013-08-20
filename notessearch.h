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
