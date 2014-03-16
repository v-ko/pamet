/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef CANVAS_H
#define CANVAS_H

#include <QWidget>
#include <QMouseEvent>
#include <QLineEdit>
#include <QMenu>
#include <QLabel>

#include "misliwindow.h"
#include "mislidesktopgui.h"
#include "editnotedialogue.h"

class Canvas : public QWidget
{
    Q_OBJECT
public:
    //Functions
    Canvas(MisliWindow *msl_w_);
    ~Canvas();

    QSize sizeHint() const;

    Note *get_note_under_mouse(int x , int y);
    Note *get_note_clicked_for_resize(int x , int y);
    Link *get_link_under_mouse(int x,int y); //returns one link (not necesserily the top one) under the mouse

    MisliDir *misli_dir();
    NoteFile *curr_nf();

    void set_eye_coords_from_curr_nf();
    void save_eye_coords_to_nf();

    void unproject(float screenX, float screenY, float &realX, float &realY);
    void project(float realX, float realY, float &screenX, float &screenY);

    //Variables
    QFont font;
    MisliWindow *misli_w;
    float eye_x,eye_y,eye_z;
    Note *mouse_note;
    QTime last_release_event;

    //--Child objects (for destruction)---
    QLineEdit *searchField;
    QMenu *contextMenu;
    QLabel *infoLabel;
    QTimer *move_func_timeout;

    float move_x, move_y, resize_x, resize_y;
    int XonPush,YonPush,PushLeft,current_mouse_x,current_mouse_y;
    float EyeXOnPush,EyeYOnPush;
    bool ctrl_is_pressed,shift_is_pressed;
    bool timed_out_move,move_on,resize_on;

public slots:
    void move_func();
    void set_linking_on();
    void set_linking_off();
    int paste();
    void jump_to_nearest_note();
    bool doubleClick();

protected:
    void paintEvent(QPaintEvent * event);
    void resize(int width, int height);
    void mousePressEvent(QMouseEvent *event);
    void mouseReleaseEvent(QMouseEvent *event);
    void mouseDoubleClickEvent(QMouseEvent *);
    void wheelEvent(QWheelEvent *event);
    void mouseMoveEvent(QMouseEvent *event);
};

#endif // CANVAS_H
