/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef COMMON_H
#define COMMON_H

#include "note.h"
#include "notefile.h"
#include "../../petko10.h"
#include "../../petko10q.h"

#define move_z 2
#define FONT_TRANSFORM_FACTOR 15 //quality of the font textures (really only matters for close distance) interval [10;40] or smth like that
#define CLICK_RADIUS 0.3
#define MAX_STRING_LENGTH 2000
#define MAX_LINE_LENGTH 2020
#define misli_speed 2 //stypka pri dvijenie napred-nazad
#define MOVE_FUNC_TIMEOUT 300 //milisecs to hold the mouse on a note to move it
#define MAX_UNDO_STEPS 30

extern int EkranX;
extern int EkranY;
extern int XonPush,YonPush,PushLeft; //poziciq na mi6kata pri natiskane na buton
extern float EyeXOnPush,EyeYOnPush;
extern int current_mouse_x,current_mouse_y;
extern bool ctrl_is_pressed,shift_is_pressed;
extern bool timed_out_move,move_on,resize_on;
//extern int current_note_file;
extern float note_x,note_y;

extern Eye eye;
//,*edited_note
extern Note null_note,*mouse_note,*help_note;
extern NoteFile null_note_file;
extern Link null_link;

#endif // COMMON_H
