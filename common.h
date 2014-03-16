/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef COMMON_H
#define COMMON_H

#define move_z 2
#define FONT_TRANSFORM_FACTOR 15 //quality of the font textures (really only matters for close distance) interval [10;40] or smth like that
#define CLICK_RADIUS 0.3
#define MOVE_SPEED 2 //stypka pri dvijenie napred-nazad
#define MOVE_FUNC_TIMEOUT 300 //milisecs to hold the mouse on a note to move it
#define MAX_UNDO_STEPS 30 //should be memory consumption based
#define INITIAL_EYE_Z 90
#define NOTE_SPACING 0.006
#define RESIZE_CIRCLE_RADIUS 1
#define ALIGNMENT_LINE_LENGTH 6
#define A_TO_B_NOTE_SIZE_RATIO 5
#define SEARCH_RESULT_HEIGHT 50 //in pixels
#define MAX_NOTE_TEXT_SIZE 7000
#define MAX_NOTE_A 150
#define MAX_NOTE_B 150
#define MIN_NOTE_A 1.3
#define MIN_NOTE_B 1.3
#define MOVE_FUNC_TOLERANCE 12 //in pixels

#define NOTE_TYPE_NORMAL_NOTE 0
#define NOTE_TYPE_REDIRECTING_NOTE 1
#define NOTE_TYPE_TEXT_FILE_NOTE 2
#define NOTE_TYPE_PICTURE_NOTE 3
#define NOTE_TYPE_SYSTEM_CALL_NOTE 4


#endif // COMMON_H
