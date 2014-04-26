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

#ifndef NOTEFILE_H
#define NOTEFILE_H

#include "note.h"
#include <string>

class MisliDir;

class NoteFile { // all notes and supporting elements (info) for a note file

public:
    //Functions
    NoteFile(MisliDir * misli_dir_);
    ~NoteFile();

    Note *get_first_selected_note();
    Note *get_lowest_id_note();
    Note *get_note_by_id(int id);
    void select_all_notes();
    void clear_note_selection();
    void clear_link_selection();
    void make_coords_relative_to(double x,double y);
    void make_all_ids_negative();
    int get_new_id();

    Note *add_note_base(QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]);
    Note *add_note(int id,QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]);
    Note *add_note(QString text,double x,double y,double z,double a,double b,double font_size,QDateTime t_made,QDateTime t_mod,float txt_col[],float bg_col[]);
    Note *add_note(Note* nt);

    int delete_note(Note *);
    int delete_note(unsigned int);
    int delete_selected();

    QString init(QString path);
    int init(QString ime, QString path);
    int init(NoteFile* nf);
    int init_links();
    int init_notes();
    int virtual_save();
    int hard_save();
    int save();
    int undo();
    void find_free_ids();
    bool is_not_system();
    bool isEmpty();

    //Variables
    QString name;
    NotesVector note; //all the notes are stored here
    int last_note_id;
    std::vector<QString> comment; //the comments in the file
    std::vector<int> free_id; //free note id-s
    QString full_file_addr; //note file path
    MisliDir *misli_dir; //pointer to the parent
    float eye_x,eye_y,eye_z; //camera position for the GUI cases
    std::vector<std::string> nf_z; //history of the notefile (for undo)
    bool is_displayed_first_on_startup;
    bool is_deleted_externally;
    bool is_current;
    bool is_locked;
};

#endif // NOTEFILE_H
