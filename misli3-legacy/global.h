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

#ifndef COMMON_H
#define COMMON_H

#include <qglobal.h>

#define MISLI_VERSION "3.0.0"

#define CLICK_RADIUS 0.3
#define MOVE_SPEED 3
#define MOVE_FUNC_TIMEOUT 300 //milisecs to hold the mouse on a note to move it
#define MAX_UNDO_STEPS 100 //should be memory consumption based
#define INITIAL_EYE_Z 90 //default height of the viewpoint
#define NOTE_SPACING 0.02
#define RESIZE_CIRCLE_RADIUS 1
#define ALIGNMENT_LINE_LENGTH 6
#define A_TO_B_NOTE_SIZE_RATIO 5
#define SEARCH_RESULT_HEIGHT 50 //in pixels
#define MAX_TEXT_FOR_DISPLAY_SIZE 10000
#define MAX_NOTE_A 80
#define MAX_NOTE_B 80
#define MIN_NOTE_A 1.5
#define MIN_NOTE_B 1.5
#define SNAP_GRID_INTERVAL_SIZE 0.5
#define MOVE_FUNC_TOLERANCE 12 //in pixels
#define MAX_FONT_SIZE 100
#define MAX_URI_LENGTH 2048
#define TIME_FORMAT "d.M.yyyy H:m:s"

const qint64 days = 24*60*60*1000;
const qint64 months = 30*days;
const qint64 years = 12*months;

extern bool use_json;

#endif // COMMON_H
