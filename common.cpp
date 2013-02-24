/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "common.h"

int EkranX=1000;
int EkranY=700;
int XonPush,YonPush,PushLeft=0; //poziciq na mi6kata pri natiskane na buton
float EyeXOnPush,EyeYOnPush;
int current_mouse_x=0,current_mouse_y=0;
bool ctrl_is_pressed=0,shift_is_pressed=0;
bool timed_out_move=0,move_on=0,resize_on=0;

Eye eye;
Note null_note,*mouse_note=NULL,*help_note=NULL;
NoteFile null_note_file;
Link null_link;
MisliInstance *curr_misl_i;

