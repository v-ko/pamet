/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef NOTE_H
#define NOTE_H

#include<QDate>
#include <vector>
#include <GL/gl.h>
#include <QGLPixelBuffer>
#include "link.h"

class NoteFile;
class MisliInstance;

class Note{
    public:
//------Koito se zapisvat/4etat v/ot file-a------------
int id;
float x,y,z;//poziciq
float a, b; //6irinata na kutiqta i viso4inata
QString text;
double font_size;
bool selected;
QDateTime t_made,t_mod;
float txt_col[4],bg_col[4]; //text and background colors
std::vector<Link> outlink;
std::vector<int> inlink;

//------Koito sa samo za programata----------------
QString short_text;
double move_orig_x;
double move_orig_y;
double rx1,ry1,rx2,ry2;
int nf_id;
MisliInstance *misl_i;
GLuint texture;
int type; //1=redirecting , 0=normal

//-----Funkcii-------------
Note();
int init();
int init_links();
int correct_links();
int link_to_selected();

int add_link(Link *ln);

int delete_inlink_for_id(int);
int delete_link(int); //no need for one that accepts Link* !

};
typedef std::vector<Note> NotesVector;


#endif // NOTE_H
