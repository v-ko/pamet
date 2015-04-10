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

#ifndef NOTE_H
#define NOTE_H

#include <vector>

#include <QDate>
#include <QImage>

#include "link.h"

class NoteFile;
class MisliDir;

class Note{

public:
    //------Variables that are read/written on the file------------
    int id;

    float x,y,z;//coordinates
    float a, b; //width and height of the box

    QString text;

    float font_size;
    QDateTime t_made,t_mod;
    float txt_col[4],bg_col[4]; //text and background colors
    std::vector<Link> outlink;
    std::vector<int> inlink;

    //------Variables needed only for the program----------------
    QString text_for_shortening;
    QString text_for_display; //this gets drawn in the note
    QString address_string;

    float move_orig_x,move_orig_y,rx,ry;
    float pixm_real_size_x; //pixmap real size
    float pixm_real_size_y;

    QString nf_name;
    MisliDir *misli_dir;

    QImage *img;
    Qt::AlignmentFlag alignment;

    int type; //1=redirecting , 0=normal

    bool selected;
    bool has_more_than_one_row;
    bool text_is_shortened;
    bool auto_sizing_now;

    //-----Functions-------------
    Note();
    ~Note();

    int calculate_coordinates();
    int store_coordinates_before_move();
    int adjust_text_size();
    int check_text_for_links(MisliDir *md);
    int check_for_file_definitions();
    int check_text_for_system_call_definition();
    int draw_pixmap();
    int init();
    void auto_size();
    void center_eye_on_me();

    int init_links();
    int correct_links();
    int link_to_selected();

    int add_link(Link *ln);

    int delete_inlink_for_id(int);
    int delete_link(int); //no need for one that accepts Link* !

    void beRed();
    void beGreen();

};
typedef std::vector<Note*> NotesVector;


#endif // NOTE_H
