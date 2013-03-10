/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <math.h>
#include <GL/gl.h>
#include <GL/glu.h>

#include <QtGui>
#include <QtOpenGL>

#include "glwidget.h"
#include "misliwindow.h"

#ifndef GL_MULTISAMPLE
#define GL_MULTISAMPLE  0x809D
#endif

GLWidget::GLWidget(MisliWindow *msl_w_)
    : QGLWidget(QGLFormat(QGL::SampleBuffers))
{

    //Random
    msl_w=msl_w_;
    mouse_note=NULL;
    PushLeft=0;
    timed_out_move=0;
    move_on=0;
    resize_on=0;

    eye.x=0;
    eye.y=0;
    eye.z=100;
    eye.scenex=0;
    eye.sceney=0;
    eye.scenez=0;
    eye.upx=0;
    eye.upy=1;
    eye.upz=0;

    //Setting the timer for the move_func
    move_func_timeout = new QTimer(this);
    move_func_timeout->setSingleShot(1);
    connect(move_func_timeout, SIGNAL(timeout()), this, SLOT(move_func()));

    setMouseTracking(1);

}

GLWidget::~GLWidget()
{
}
QSize GLWidget::sizeHint() const
{
    return QSize(1000, 700);
}

NotesVector * GLWidget::curr_note()
{
    if(msl_w->notes_rdy){
        return msl_w->curr_misli()->curr_nf()->note;
    }
    else {
        d("tyrsi current note dokato nqma gotovi zapiski");
        exit (6666);
    }
}

MisliInstance * GLWidget::misl_i()
{
    if(msl_w->notes_rdy){
        return msl_w->curr_misli();
    }
    else {
        d("tyrsi current note dokato nqma gotovi zapiski");
        exit (6666);
    }
}

void GLWidget::set_eye_coords_from_curr_nf()
{
    eye.x=misl_i()->curr_nf()->eye_x;
    eye.y=misl_i()->curr_nf()->eye_y;
    eye.z=misl_i()->curr_nf()->eye_z;
    eye.scenex=misl_i()->curr_nf()->eye_x;
    eye.sceney=misl_i()->curr_nf()->eye_y;
    eye.scenez=0;
}

void GLWidget::save_eye_coords_to_nf()
{
    misl_i()->curr_nf()->eye_x=eye.x;
    misl_i()->curr_nf()->eye_y=eye.y;
    misl_i()->curr_nf()->eye_z=eye.z;
}

void GLWidget::initGLenv() //set environment variables
{
    glClearColor(1,1,1,1);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);//for proper transparency
    glTexEnvi( GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE );
    glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST ); //not sure if that has any effect
    glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST );

}
void GLWidget::setupGLenv() //start the blend and multisampling
{
    glEnable( GL_MULTISAMPLE ); //needed (some times enabled by default)
    GLint bufs;
    GLint samples;
    glGetIntegerv(GL_SAMPLE_BUFFERS, &bufs);
    glGetIntegerv(GL_SAMPLES, &samples);
    qDebug("We have %d buffers and %d samples", bufs, samples);

    glEnable( GL_BLEND );
    //glEnable(GL_DEPTH_TEST);
}

void GLWidget::initializeGL() //the init is distributed so that function is ommited
{
    initGLenv();
    setupGLenv();
}

void GLWidget::setupViewport(int width, int height)
{
    glViewport(0, 0, width, height);

    glMatrixMode(GL_PROJECTION); //otvarqme proekcionnata matrica
    glLoadIdentity(); //iz4istvame q (edin vid clear na proekcionnata ) . Identity matricata e s diagonal edinici i prazni ostanali poleta

    gluPerspective( AngleOfSight, float(width)/float(height), 1, 1000); //da sloja promenlivi za near i far

    glMatrixMode(GL_MODELVIEW); //matrica obrabotva6ta modela
}

void GLWidget::paintGL()
{
    if(!msl_w->notes_rdy){
        //glClearColor(1, 1, 1, 1);
        //glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        return;
    }


    //glEnable( GL_DEPTH_TEST );

    Note *nt;
    float a,b,x,y,z,rx1,ry1,rx2,ry2;

    GLUquadricObj *qobj= gluNewQuadric();
    gluQuadricDrawStyle(qobj,GLU_FILL);

    setupViewport(width(),height());

    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    gluLookAt ( eye.x , eye.y, eye.z, eye.scenex, eye.sceney, eye.scenez, eye.upx, eye.upy, eye.upz );//gluLookAp sets the matrix up in such a way as to compensate the position of the imaginary camera with model transformations

    glClearColor(1, 1, 1, 1);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    //Save the matrices for use in the project/unproject functions
    glGetDoublev(GL_MODELVIEW_MATRIX, modelview);
    glGetDoublev(GL_PROJECTION_MATRIX, projection);
    glGetIntegerv(GL_VIEWPORT, viewport);

    for(unsigned int i=0;i<curr_note()->size();i++){

        nt=&(*curr_note())[i];

        x=nt->x;//text coordinates
        y=nt->y;
        z=nt->z;
        a=nt->a;//box dimentions
        b=nt->b;
        rx1=nt->rx1; //coordinates of the rectangle encapsulating the note
        ry1=nt->ry1;
        rx2=nt->rx2;
        ry2=nt->ry2;

        //Make the drawable elements
        if(z!=0){ //the "shade" of the note on the z=0 plane
            glColor4f(0.8,0.8,0.8,1);
            glRectf(rx1,ry1,rx2,ry2);
        }

        glColor4f(nt->bg_col[0],nt->bg_col[1],nt->bg_col[2],nt->bg_col[3]);
        glPushMatrix();
            glTranslatef(0,0,z);
            glRectf(rx1,ry1,rx2,ry2);

            if(nt->selected){
                glColor4f(1,1,0,1);
                glRectf(rx1,ry1,rx2,ry2); //the yellow marking box

                glPushMatrix(); //bottom right
                    glTranslatef(rx2,ry2,0);
                    glColor4f(0,0,1,0.1);
                    gluDisk(qobj,0,CLICK_RADIUS,30,1); //the circle for resize
                glPopMatrix();
            }

        glPopMatrix();

        if(nt->type==1){ //if the note is redirecting
            glColor4f(nt->txt_col[0],nt->txt_col[1],nt->txt_col[2],0.5);
            glBegin(GL_LINES);
                glVertex3f(nt->rx1,nt->ry1,z);
                glVertex3f(nt->rx2,nt->ry1,z);

                glVertex3f(nt->rx2,nt->ry1,z);
                glVertex3f(nt->rx2,nt->ry2,z);

                glVertex3f(nt->rx2,nt->ry2,z);
                glVertex3f(nt->rx1,nt->ry2,z);

                glVertex3f(nt->rx1,nt->ry2,z);
                glVertex3f(nt->rx1,nt->ry1,z);
            glEnd();
        }

        //glColor4f(0,0,1,0.5);

        //Draw the textures with the text
        //glDisable( GL_DEPTH_TEST );
        glEnable( GL_TEXTURE_2D );


        glBindTexture(GL_TEXTURE_2D,nt->texture);
        glPushMatrix();
            glTranslatef(x,y,z);
            //glMatrixMode(GL_TEXTURE_MATRIX);

            glBegin(GL_QUADS);   // position the texture to fill the rectangle
                glTexCoord2f(0,0); glVertex2f(0,-b);
                glTexCoord2f(0,1); glVertex2f(0,0);
                glTexCoord2f(1,1); glVertex2f(a,0);
                glTexCoord2f(1,0); glVertex2f(a,-b);
            glEnd();
        glPopMatrix();


        glDisable(GL_TEXTURE_2D);
        //glEnable( GL_DEPTH_TEST );

        //Drawing the links
        //glEnable( GL_DEPTH_TEST );
        for(unsigned int n=0;n<nt->outlink.size();n++){

            Link *ln=&nt->outlink[n];

            glColor4f(nt->txt_col[0],nt->txt_col[1],nt->txt_col[2],0.5);

            //Begin drawing
            glBegin(GL_LINES);
                //Draw the base line
                glVertex3f(ln->x1,ln->y1,ln->z1);
                glVertex3f(ln->x2,ln->y2,ln->z2);

                if(ln->selected){ //overpaint with yellow if it's selected
                        glColor4f(1,1,0,0.5);
                        glVertex3f(ln->x1,ln->y1,ln->z1);
                        glVertex3f(ln->x2,ln->y2,ln->z2);
                    }
            glEnd();

            glPushMatrix();
                glTranslatef(ln->x2,ln->y2,ln->z2); //translate and rotate that put the arrow where it needs to be
                glRotatef(GetAng(ln->x2,ln->y2+10,ln->x2,ln->y2,ln->x1,ln->y1),0,0,1);

                glColor4f(nt->txt_col[0],nt->txt_col[1],nt->txt_col[2],0.5);
                //Draw the arrow (head of the link)
                glBegin(GL_LINES);
                    glVertex3f(0,0,0);
                    glVertex3f(-0.5,1,0);
                    glVertex3f(0,0,0);
                    glVertex3f(0.5,1,0);
                glEnd();
                if(ln->selected){ //overpaint when selected
                    glColor4f(1,1,0,0.5);
                    glBegin(GL_LINES);
                        glVertex3f(0,0,0);
                        glVertex3f(-0.5,1,0);
                        glVertex3f(0,0,0);
                        glVertex3f(0.5,1,0);
                    glEnd();
                }

            glPopMatrix();

        } //next link
        //glDisable( GL_DEPTH_TEST );

    } //next note


//return
}
void GLWidget::resizeGL(int width, int height)
{
    setupViewport(width,height);
}

void GLWidget::mousePressEvent(QMouseEvent *event)
{
    if(!msl_w->notes_rdy){return;}

    updateGL();//don't put at the end , return get's called earlier in some cases

    int x = event->x();
    int y = event->y();

    if(event->modifiers()==Qt::ControlModifier){ctrl_is_pressed=1;}else ctrl_is_pressed=0;
    if(event->modifiers()==Qt::ShiftModifier){shift_is_pressed=1;}else shift_is_pressed=0;

        if (event->button()==Qt::LeftButton) { //on left button


                //----save na globalni promenlivi za dr funkcii-----
                XonPush = x;
                YonPush = y;
                PushLeft=1;
                EyeXOnPush=eye.x;
                EyeYOnPush=eye.y;
                timed_out_move=0;

                Note *nt_under_mouse;
                Note *nt_for_resize;
                Link *ln_under_mouse;

                if (mouse_note!=NULL) { // ------------LINKING ON KEY----------

                    nt_under_mouse=get_note_under_mouse(x,y);
                    if(nt_under_mouse!=NULL){
                        set_linking_off();
                        nt_under_mouse->link_to_selected();
                        misl_i()->curr_nf()->save();
                        return;
                    }else{ //if there's no note under the mouse
                        set_linking_off();
                        return;
                    }

                }



                //----------SELECT------------
                nt_under_mouse = get_note_under_mouse(x,y);

                if( (!ctrl_is_pressed) && (!shift_is_pressed) ) { //ako ne e natisnat ctrl iz4istvame selection-a
                    misl_i()->curr_nf()->clear_note_selection();
                    misl_i()->curr_nf()->clear_link_selection();
                }

                ln_under_mouse = get_link_under_mouse(x,y); //Za linkove
                if (ln_under_mouse!=NULL){
                    ln_under_mouse->selected=1;
                }

                if (nt_under_mouse!=NULL){ //Za notes

                    if(nt_under_mouse->selected){
                        nt_under_mouse->selected=0;
                    }else {
                        nt_under_mouse->selected=1;
                    }

                    move_x=x-nt_under_mouse->x;
                    move_y=y-nt_under_mouse->y;
                    //nt_under_mouse->move_orig_x=nt_under_mouse->x; //za da moje da se mestqt pove4e ednovremenno trqbva da im se pazi pyrvona4alnata poziciq prez mesteneto
                    //nt_under_mouse->move_orig_y=nt_under_mouse->y;

                    if(shift_is_pressed){
                        nt_under_mouse->selected=1;
                        for(unsigned int i=0;i<nt_under_mouse->outlink.size();i++){ //select all child notes
                            misl_i()->nf_by_id(nt_under_mouse->nf_id)->get_note_by_id(nt_under_mouse->outlink[i].id)->selected=1;
                        }
                    }

                    timed_out_move=1;
                    move_func_timeout->start(MOVE_FUNC_TIMEOUT);

                }

                // -----------RESIZE---------------
                nt_for_resize=get_note_clicked_for_resize(x,y);
                if (nt_for_resize!=NULL){
                    nt_for_resize->selected=1;
                    resize_on=1;
                    resize_x=nt_for_resize->x;
                    resize_y=nt_for_resize->y;
                    return;
                }

        }



}
void GLWidget::mouseReleaseEvent(QMouseEvent *event)
{
    if(!msl_w->notes_rdy){return;}

    if (event->button()==Qt::LeftButton) { //on left button


        PushLeft = 0;

        if(move_on){
            move_on=0;
            for(unsigned int i=0;i<curr_note()->size();i++){
                if((*curr_note())[i].selected){
                    (*curr_note())[i].z=0;
                    (*curr_note())[i].init();
                    (*curr_note())[i].correct_links(); //korigirame linkovete
                }
            }
            misl_i()->curr_nf()->save(); //save na novite pozicii

        }else if (resize_on){

            for(unsigned int i=0;i<curr_note()->size();i++){
                if((*curr_note())[i].selected){
                    (*curr_note())[i].correct_links(); //korigirame linkovete
                }
            }
            misl_i()->curr_nf()->save(); //save na novite razmeri
            resize_on=0;
        }
        else { //normal move about the canvas
            misl_i()->gl_w->save_eye_coords_to_nf();
        }
    }
    updateGL();

}
void GLWidget::mouseDoubleClickEvent(QMouseEvent *event)
{
    if(!msl_w->notes_rdy){return;}

    Note *nt;

    if (event->button()==Qt::LeftButton) { //on left button doubleclick

        nt = get_note_under_mouse(event->x(),event->y());

        if(nt!=NULL){ //if we've clicked on a note
            if(nt->type==1){ //if it's a valid redirecting note
                if(msl_w->curr_misli()->nf_by_name(nt->short_text)!=NULL)
                msl_w->curr_misli()->set_current_notes(msl_w->curr_misli()->nf_by_name(nt->short_text)->id); //change notefile
            }
        }
        else {//if not on note
            msl_w->edit_w->new_note();
        }
    }
updateGL();
}

void GLWidget::wheelEvent(QWheelEvent *event)
{
    if(!msl_w->notes_rdy){return;}

    int numDegrees = event->delta() / 8;
    int numSteps = numDegrees / 15;

    eye.z-=MOVE_SPEED*numSteps;

    updateGL();

    //glutPostRedisplay();

}
void GLWidget::mouseMoveEvent(QMouseEvent *event)
{
    //d("report move");
    if(!msl_w->notes_rdy){return;}

    double scr_x,scr_y,scr_z,scr2_x,scr2_y,nt_x,nt_y,m_x,m_y,d_x,d_y,t_x,t_y;

    int x = event->x();
    int y = event->y();

    current_mouse_x=x;
    current_mouse_y=y;

    if(PushLeft){
        if(move_on){

            for(unsigned int i=0;i<curr_note()->size();i++){
                if((*curr_note())[i].selected){
                    project_from_plane((*curr_note())[i].move_orig_x+move_x,(*curr_note())[i].move_orig_y+move_y,0,scr_x,scr_y,scr_z);//poziciq na mi6kata pri natiskaneto (pri mnogo obekti vseki si ima teoreti4na takava,za tova ne se polzva x_on_push)
                    scr2_x=scr_x+x-XonPush;//poziciq na mi6kata v momenta (pak teoreti4na za vseki obekt, realna za tozi ot koito e trygnalo mesteneto)
                    scr2_y=scr_y+y-YonPush;
                    unproject_to_plane(0,scr2_x,scr2_y,nt_x , nt_y); //namirame realnata poziciq na mi6kata
                    (*curr_note())[i].x=nt_x-move_x; //ot neq vadim move za namirane na ygyla na kutiqta na note-a
                    (*curr_note())[i].y=nt_y-move_y;
                    (*curr_note())[i].init();
                    (*curr_note())[i].correct_links(); //korigirame linkovete
                }
            }

        }else if(resize_on){

            for(unsigned int i=0;i<curr_note()->size();i++){
                if((*curr_note())[i].selected){

                    unproject_to_plane(0,x,y,m_x,m_y);
                    d_x=m_x-resize_x;
                    d_y=resize_y-m_y;

                    (*curr_note())[i].a=stop(d_x,3,1000);

                    (*curr_note())[i].b=stop(d_y,1.3,1000);
                    (*curr_note())[i].init();
                    (*curr_note())[i].correct_links(); //korigirame linkovete
                }
            }

        }else{

        float xrel=x-XonPush,yrel=y-YonPush;
        float s1=(float(size().height())/2)/tan(float(AngleOfSight)/2*pi/180); //razstoqnie do ekrana (t.e. ekvivalenta na ekrana v koord sistema)
        float s=eye.scenez - eye.z; //razstoqnie do realnata ravnina
            eye.x=EyeXOnPush+xrel*s/s1;
            eye.y=EyeYOnPush-yrel*s/s1;
            eye.scenex=eye.x;
            eye.sceney=eye.y;
        }
    }else{ // left button is not pushed
        if(mouse_note!=NULL){

                unproject_to_plane(0,x,y,t_x,t_y);
                mouse_note->x=t_x+0.02;
                mouse_note->y=t_y-0.02;
                mouse_note->init();
                mouse_note->correct_links();
            }
    } updateGL();
//return;
}

Note *GLWidget::get_note_under_mouse(int x , int y){

GLdouble rx1,ry1,rx2,ry2,rz;

for(unsigned int i=0;i<curr_note()->size();i++){

    rx1=(*curr_note())[i].rx1; //koordinati na poleto
    ry1=(*curr_note())[i].ry1;
    rx2=(*curr_note())[i].rx2;
    ry2=(*curr_note())[i].ry2;
    rz=(*curr_note())[i].z;

    project_from_plane(rx1,ry1,rz,rx1,ry1,rz); //yglite na kutiqta
    project_from_plane(rx2,ry2,rz,rx2,ry2,rz);


    if( point_intersects_with_rectangle(float(x),float(y),rx1,ry1,rx2,ry2)) {
        return &(*curr_note())[i];
    }

}

return NULL;
}
Note *GLWidget::get_note_clicked_for_resize(int x , int y){

GLdouble rx1,ry1,rx2,ry2,ryy,rz,rrz,radius_x,scr_radius,r;
Note nt;
for(unsigned int i=0;i<curr_note()->size();i++){

    rx1=(*curr_note())[i].rx1; //koordinati na poleto
    ry1=(*curr_note())[i].ry1;
    rx2=(*curr_note())[i].rx2;
    ry2=(*curr_note())[i].ry2;
    rz=(*curr_note())[i].z;
nt=(*curr_note())[i];
    radius_x=rx2+double(CLICK_RADIUS);

    project_from_plane(rx1,ry1,rz,rx1,ry1,rrz); //yglite na kutiqta
    project_from_plane(rx2,ry2,rz,rx2,ry2,rz);
    project_from_plane(radius_x,(*curr_note())[i].ry2,(*curr_note())[i].z,radius_x,ryy,rz); //to4ka ot radiusa na kryga za resize koqto 6te polzvame da vidim kolko e radiusa na ekrana

    scr_radius=mod(radius_x-rx2); //radiusa na kryga na ekrana
    r=mod(dottodot(rx2,ry2,float(x),float(y)));

    if(r<=scr_radius){ //ako mi6kata e v kryga za resize(razst ot neq do ygyla na kutiqta e po-malko ot radiusa na kryga)
        return &(*curr_note())[i]; //za da ne se opitva da mesti ili selectira i t.n.
    }

}

return NULL;
}
Link *GLWidget::get_link_under_mouse(int x,int y){ //returns one link (not necesserily the top one) onder the mouse

Link *ln;
double a,b,c,h,m_x,m_y;

unproject_to_plane(0,x,y,m_x,m_y);

for(unsigned int i=0;i<curr_note()->size();i++){
    for(unsigned int l=0;l<(*curr_note())[i].outlink.size();l++){
        ln=&(*curr_note())[i].outlink[l];
        a=dottodot3(ln->x1,ln->y1,ln->z1,ln->x2,ln->y2,ln->z2);
        b=dottodot3(m_x,m_y,0,ln->x2,ln->y2,ln->z2);
        c=dottodot3(m_x,m_y,0,ln->x1,ln->y1,ln->z1);
        h=distance_to_line(m_x,m_y,0,ln->x1,ln->y1,ln->z1,ln->x2,ln->y2,ln->z2);
        if( ( c<a && b<a ) && h<=CLICK_RADIUS*2 ){
            return ln;
        }

    }
}

return NULL;

}

void GLWidget::move_func(){ //ako sled opredelenoto vreme mi6kata e na sy6toto mqsto i time_out_move ne e izkl (pri vdigane na butona) se vdiga flag-a za move

    int x=current_mouse_x;
    int y=current_mouse_y;

    if( (timed_out_move && PushLeft ) && ( (XonPush==x) && (YonPush==y) ) ){

        get_note_under_mouse(x,y)->selected=1; //to pickup a selected note with control pressed (not to deselect it)
        move_on=1;
        for(unsigned int i=0;i<curr_note()->size();i++){
            if((*curr_note())[i].selected){
                    (*curr_note())[i].z=move_z;
                    (*curr_note())[i].correct_links(); //korigirame linkovete
            }
        }
    }

timed_out_move=0;
updateGL();

}
void GLWidget::set_linking_on()
{
    int x = current_mouse_x;
    int y = current_mouse_y;
    double t_x,t_y;
    float txt_col[] = {0,0,1,1};
    float bg_col[] = {0,0,1,0.1};

    if(misl_i()->curr_nf()->get_first_selected_note()!=NULL && mouse_note==NULL){
        mouse_note=misl_i()->curr_nf()->add_note(misl_i(),"L",t_x,t_y,0,1,1,1,QDateTime(QDate(1,1,1)),QDateTime(QDate(1,1,1)),txt_col,bg_col);
        unproject_to_plane(0,x,y,t_x,t_y);
        mouse_note->x=t_x;
        mouse_note->y=t_y;
        mouse_note->link_to_selected();
    }
}
void GLWidget::set_linking_off()
{
    misl_i()->curr_nf()->delete_note(mouse_note);
    mouse_note=NULL;
}

int GLWidget::unproject_to_plane(float z,float x_on_scr,float y_on_scr,float &x,float &y){ //pravi gluUnproject na to4ka [x_on_scr,y_on_scr] v/u ploskostta (paralelna na x->,y-> ) v dylbo4ina z

GLdouble x1,x2,y1,y2,z1,z2;
GLfloat winX,winY;

float a,c;

winX = (float)x_on_scr;
winY = (float)viewport[3] - (float)y_on_scr;

gluUnProject( winX, winY, 0, modelview, projection, viewport, &x1, &y1, &z1);
gluUnProject( winX, winY, 1, modelview, projection, viewport, &x2, &y2, &z2);

GetFunc(0,0,z1,x1,z2,x2,a,c);
x=z*a + c;
GetFunc(0,0,z1,y1,z2,y2,a,c);
y=z*a + c;

return 0;
}
int GLWidget::unproject_to_plane(float z,float x_on_scr,float y_on_scr,double &x,double &y){ //pravi gluUnproject na to4ka [x_on_scr,y_on_scr] v/u ploskostta (paralelna na x->,y-> ) v dylbo4ina z

GLdouble x1,x2,y1,y2,z1,z2;
GLfloat winX,winY;

float a,c;

winX = (float)x_on_scr;
winY = (float)viewport[3] - (float)y_on_scr;

gluUnProject( winX, winY, 0, modelview, projection, viewport, &x1, &y1, &z1);
gluUnProject( winX, winY, 1, modelview, projection, viewport, &x2, &y2, &z2);

GetFunc(0,0,z1,x1,z2,x2,a,c);
x=z*a + c;
GetFunc(0,0,z1,y1,z2,y2,a,c);
y=z*a + c;

return 0;
}
int GLWidget::project_from_plane(double x_on_plane,double y_on_plane,double z_plane,double &x,double &y,double &z){

gluProject(x_on_plane,y_on_plane,z_plane,modelview, projection, viewport,&x,&y,&z); //namirame kak se proektira kutiqta na note-a na ekrana

y = viewport[3]-y;

return 0;
}

int GLWidget::copy()
{
    NoteFile *clipnf=msl_w->curr_misli()->clipboard_nf();
    int err=0;
    int x=current_mouse_x;
    int y=current_mouse_y;

    while(clipnf->get_lowest_id_note()!=NULL){ //delete all notes in clipnf
        clipnf->delete_note(clipnf->get_lowest_id_note());
    }

    err+=msl_w->curr_misli()->copy_selected_notes(msl_w->curr_misli()->curr_nf(),clipnf ); //dumm copy the selected notes

    //make coordinates relative
    if(get_note_under_mouse(x,y)!=NULL){ //to the note under the mouse if there's one
        clipnf->make_coords_relative_to(get_note_under_mouse(x,y)->x,get_note_under_mouse(x,y)->y);
    }else {
        clipnf->make_coords_relative_to(clipnf->get_lowest_id_note()->x,clipnf->get_lowest_id_note()->y);
    }

    return err;
}
int GLWidget::cut()
{
    int err=0;

    err+=copy();
    err+=msl_w->curr_misli()->delete_selected();

    return err;
}
int GLWidget::paste()
{
    NoteFile *nf=msl_w->curr_misli()->clipboard_nf();
    Note *nt;
    Link *ln;
    double x,y;
    int old_id;

    //Make all the id-s negative (and select all notes)
    for(unsigned int n=0;n<nf->note->size();n++){ //for every note
        nt=&(*nf->note)[n];
        nt->id = -nt->id;
        nt->selected=1;//for the copy later

        for(unsigned int l=0;l<nt->outlink.size();l++){
            ln=&nt->outlink[l];
            ln->id= -ln->id;
        }
        for(unsigned int in=0;in<nt->inlink.size();in++){ //for every inlink
            nt->inlink[in]= -nt->inlink[in]; //if it has the old id - set it up with the new one
        }
    }

    //Make coordinates relative to the mouse
    x=current_mouse_x; //get mouse coords
    y=current_mouse_y;
    unproject_to_plane(0,x,y,x,y); //translate them to real GL coords
    nf->make_coords_relative_to(-x,-y);

    //Copy the notes over to the target
    msl_w->curr_misli()->copy_selected_notes(nf,msl_w->curr_misli()->curr_nf());

    //return clipboard notes' coordinates to 0
    nf->make_coords_relative_to(x,y);

    nf=msl_w->curr_misli()->curr_nf();

    //Replace the negative id-s with real ones
    for(unsigned int n=0;n<nf->note->size();n++){ //for every note
        nt=&(*nf->note)[n];
        old_id = nt->id;
        nt->id = nf->get_new_id();

        //Fix the id-s in the links
        for(unsigned int i=0;i<nf->note->size();i++){ //for every note
            for(unsigned int l=0;l<(*nf->note)[i].outlink.size();l++){ //for every outlink
                ln=&(*nf->note)[i].outlink[l];
                if(ln->id==old_id){ ln->id=nt->id ; } //if it has the old id - set it up with the new one
            }
            for(unsigned int in=0;in<(*nf->note)[i].inlink.size();in++){ //for every inlink
                if((*nf->note)[i].inlink[in]==old_id){ (*nf->note)[i].inlink[in]=nt->id ; } //if it has the old id - set it up with the new one
            }
        }
        nt->init();
        nt->init_links();
    }

    nf->save();
    return 0;
}
