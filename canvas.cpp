/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "canvas.h"
#include "misliwindow.h"

Canvas::Canvas(MisliWindow *msl_w_)
{

    //Random
    msl_w=msl_w_;
    mouse_note=NULL;
    PushLeft=0;
    timed_out_move=0;
    move_on=0;
    resize_on=0;

    eye_x=0;
    eye_y=0;
    eye_z=INITIAL_EYE_Z;

    //Setting the timer for the move_func
    move_func_timeout = new QTimer(this);
    move_func_timeout->setSingleShot(1);
    connect(move_func_timeout, SIGNAL(timeout()), this, SLOT(move_func()));

    setMouseTracking(1);

}

QSize Canvas::sizeHint() const
{
    return QSize(1000, 700);
}

NotesVector * Canvas::curr_note()
{
    if(msl_w->notes_rdy){
        return msl_w->curr_misli()->curr_nf()->note;
    }
    else {
        d("tyrsi current note dokato nqma gotovi zapiski");
        exit (6666);
    }
}

MisliInstance * Canvas::misl_i()
{
    if(msl_w->notes_rdy){
        return msl_w->curr_misli();
    }
    else {
        d("tyrsi current note dokato nqma gotovi zapiski");
        exit (6666);
    }
}

void Canvas::set_eye_coords_from_curr_nf()
{
    eye_x=misl_i()->curr_nf()->eye_x;
    eye_y=misl_i()->curr_nf()->eye_y;
    eye_z=misl_i()->curr_nf()->eye_z;
}

void Canvas::save_eye_coords_to_nf()
{
    misl_i()->curr_nf()->eye_x=eye_x;
    misl_i()->curr_nf()->eye_y=eye_y;
    misl_i()->curr_nf()->eye_z=eye_z;
}

void Canvas::project(float realX, float realY, float &screenX, float &screenY)
{
    //The matrix transformations (same as the world transform)
    realX -= eye_x;
    realY -= eye_y;

    realX = realX/(eye_z*0.01); //realX = realX*(1/(eye_z*0.01))
    realY = realY/(eye_z*0.01);

    realX = realX*10;
    realY = realY*10;

    screenX = realX + width()/2;
    screenY = realY + height()/2;
}

void Canvas::unproject(float screenX, float screenY, float &realX, float &realY)
{
    screenX -= width()/2;
    screenY -= height()/2;

    screenX = screenX/10;
    screenY = screenY/10;

    screenX = screenX*(eye_z*0.01); //screenX = screenX/(1/(eye_z*0.01))
    screenY = screenY*(eye_z*0.01);

    realX = screenX + eye_x;
    realY = screenY + eye_y;
}

void Canvas::paintEvent(QPaintEvent *event)
{if(event->isAccepted()){} //remove the "unused variable warning..

    if(!msl_w->notes_rdy){
        return;
    }

    QPainter p(this);
    Note *nt;
    float x,y,rx,ry,nt_size_x,nt_size_y,x_projected,y_projected,ry_projected,rx_projected,r_tmp_x,r_tmp_y,resize_r_projected;
    float shadow_x,shadow_y,shadow_size_x,shadow_size_y,shadow_rx,shadow_ry;
    float ln_x1,ln_y1,ln_x2,ln_y2;

    p.setRenderHint(QPainter::Antialiasing, true);
    p.fillRect(0,0,width(),height(),QColor(255,255,255,255)); //clear background

    for(unsigned int i=0;i<curr_note()->size();i++){

        nt=&(*curr_note())[i];

        x=nt->x;//text coordinates
        y=nt->y;
        rx=nt->rx; //coordinates of the rectangle encapsulating the note
        ry=nt->ry;

        if(move_on && nt->selected){ //"pick the note up" by making it larger
            project(rx,ry,shadow_rx,shadow_ry);
            project(x,y,shadow_x,shadow_y);
            project(rx+0.3,ry,r_tmp_x,r_tmp_y);
            shadow_size_x = shadow_rx - shadow_x;
            shadow_size_y = shadow_ry - shadow_y;

            x-=0.3;
            y-=0.3;
            rx-=0.3;
            ry-=0.3;

            //Draw the shadow
            p.setPen(QColor(0,0,0,0));
            p.setBrush(QBrush(QColor(200,200,200,255))); //gray
            p.drawRect(shadow_x,shadow_y,shadow_size_x,shadow_size_y);
        }

        project(rx,ry,rx_projected,ry_projected);
        project(x,y,x_projected,y_projected);
        project(rx+0.3,ry,r_tmp_x,r_tmp_y);
        nt_size_x = rx_projected - x_projected;
        nt_size_y = ry_projected - y_projected;
        resize_r_projected = r_tmp_x - rx_projected;

        //Draw the note (only if it's on screen (to avoid lag) )
        if(QRectF(x_projected,y_projected,nt_size_x,nt_size_y).intersects(QRectF(0,0,width(),height()))){
            p.drawPixmap(x_projected,y_projected,nt->pixm->scaled(QSize(nt_size_x,nt_size_y),Qt::IgnoreAspectRatio,Qt::SmoothTransformation));
        }

        //If the note is redirecting draw a border to differentiate it
        if(nt->type==1){
            p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));
            p.setBrush(QBrush(Qt::NoBrush));
            p.drawRect(x_projected,y_projected,nt_size_x,nt_size_y);
        }

        //If it's selected - overpaint with yellow
        if(nt->selected){
            p.setPen(QColor(0,0,0,0));
            p.setBrush(QBrush(QColor(255,255,0,127))); //half-transparent yellow
            p.drawRect(x_projected,y_projected,nt_size_x,nt_size_y); //the yellow marking box

            p.setBrush(QBrush(QColor(nt->bg_col[0]*255,nt->bg_col[1]*255,nt->bg_col[2]*255, 60 ))); //same as BG but transparent
            p.drawEllipse(QPointF(rx_projected,ry_projected),resize_r_projected,resize_r_projected); //the circle for resize
        }


        for(unsigned int n=0;n<nt->outlink.size();n++){ //for every outlink

            Link *ln=&nt->outlink[n];

            project(ln->x1,ln->y1,ln_x1,ln_y1);
            project(ln->x2,ln->y2,ln_x2,ln_y2);

            //set color
            p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));

            //Draw the base line
            p.drawLine(ln_x1,ln_y1,ln_x2,ln_y2);

            if(ln->selected){ //overpaint with yellow if it's selected
                p.setPen(QColor(255,255,0,127)); //set color
                p.drawLine(ln_x1,ln_y1,ln_x2,ln_y2);
            }

            //Draw the arrow head

            p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));

            p.save(); //pushMatrix() (not quite but ~)
                p.translate(ln_x2,ln_y2);
                p.rotate(GetAng(ln_x2,ln_y2+10,ln_x2,ln_y2,ln_x1,ln_y1));

                p.drawLine(0,0,-5,10); //both lines for the arrow
                p.drawLine(0,0,5,10);

                if(ln->selected){ //overpaint when selected
                    p.setPen(QColor(255,255,0,127));
                    p.drawLine(0,0,-5,10); //both lines for the arrow
                    p.drawLine(0,0,5,10);
                }
            p.restore();//pop matrix
        } //next link
    } //next note

}//return

void Canvas::mousePressEvent(QMouseEvent *event)
{
    if(!msl_w->notes_rdy){return;}

    update();//don't put at the end , return get's called earlier in some cases

    int x = event->x();
    int y = event->y();

    if(event->modifiers()==Qt::ControlModifier){ctrl_is_pressed=1;}else ctrl_is_pressed=0;
    if(event->modifiers()==Qt::ShiftModifier){shift_is_pressed=1;}else shift_is_pressed=0;

    if (event->button()==Qt::LeftButton) { //on left button

        //----Save na globalni promenlivi za dr funkcii-----
        XonPush = x;
        YonPush = y;
        PushLeft=1;
        EyeXOnPush=eye_x;
        EyeYOnPush=eye_y;
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

        // -----------RESIZE---------------
        nt_for_resize=get_note_clicked_for_resize(x,y);
        if (nt_for_resize!=NULL){
            nt_for_resize->selected=1;
            resize_on=1;
            resize_x=nt_for_resize->x;
            resize_y=nt_for_resize->y;
            return;
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



    }

}
void Canvas::mouseReleaseEvent(QMouseEvent *event)
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
            misl_i()->canvas->save_eye_coords_to_nf();
        }
    }
    update();

}
void Canvas::mouseDoubleClickEvent(QMouseEvent *event)
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
update();
}

void Canvas::wheelEvent(QWheelEvent *event)
{
    if(!msl_w->notes_rdy){return;}

    int numDegrees = event->delta() / 8;
    int numSteps = numDegrees / 15;

    eye_z-=MOVE_SPEED*numSteps;
    eye_z = stop(eye_z,1,1000);

    update();

    //glutPostRedisplay();

}
void Canvas::mouseMoveEvent(QMouseEvent *event)
{
    //d("report move");
    if(!msl_w->notes_rdy){return;}

    float scr_x,scr_y,scr2_x,scr2_y,nt_x,nt_y,m_x,m_y,d_x,d_y,t_x,t_y;

    int x = event->x();
    int y = event->y();

    current_mouse_x=x;
    current_mouse_y=y;

    if(PushLeft){
        if(move_on){

            for(unsigned int i=0;i<curr_note()->size();i++){
                if((*curr_note())[i].selected){
                    project((*curr_note())[i].move_orig_x+move_x,(*curr_note())[i].move_orig_y+move_y,scr_x,scr_y);//poziciq na mi6kata pri natiskaneto (pri mnogo obekti vseki si ima teoreti4na takava,za tova ne se polzva x_on_push)
                    scr2_x=scr_x+x-XonPush;//poziciq na mi6kata v momenta (pak teoreti4na za vseki obekt, realna za tozi ot koito e trygnalo mesteneto)
                    scr2_y=scr_y+y-YonPush;
                    unproject(scr2_x,scr2_y,nt_x , nt_y); //namirame realnata poziciq na mi6kata
                    (*curr_note())[i].x=nt_x-move_x; //ot neq vadim move za namirane na ygyla na kutiqta na note-a
                    (*curr_note())[i].y=nt_y-move_y;
                    (*curr_note())[i].init();
                    (*curr_note())[i].correct_links(); //korigirame linkovete
                }
            }

        }else if(resize_on){

            for(unsigned int i=0;i<curr_note()->size();i++){
                if((*curr_note())[i].selected){

                    unproject(x,y,m_x,m_y);
                    d_x=m_x - resize_x;
                    d_y=m_y - resize_y;

                    (*curr_note())[i].a=stop(d_x,3,1000);

                    (*curr_note())[i].b=stop(d_y,1.3,1000);
                    (*curr_note())[i].init();
                    (*curr_note())[i].correct_links(); //korigirame linkovete
                }
            }

        }else{

            float xrel=x-XonPush,yrel=y-YonPush;
            eye_x=EyeXOnPush-xrel*0.1*(eye_z*0.01); //xrel*1/(1/(eye_z*0.01))
            eye_y=EyeYOnPush-yrel*0.1*(eye_z*0.01);
        }
    }else{ // left button is not pushed
        if(mouse_note!=NULL){

                unproject(x,y,t_x,t_y);
                mouse_note->x=t_x+0.02;
                mouse_note->y=t_y-0.02;
                mouse_note->init();
                mouse_note->correct_links();
            }
    } update();
//return;
}

Note *Canvas::get_note_under_mouse(int mx , int my){

float x,y,rx,ry;

for(unsigned int i=0;i<curr_note()->size();i++){

    x=(*curr_note())[i].x; //koordinati na poleto
    y=(*curr_note())[i].y;
    rx=(*curr_note())[i].rx;
    ry=(*curr_note())[i].ry;

    project(x,y,x,y); //yglite na kutiqta
    project(rx,ry,rx,ry);


    if( point_intersects_with_rectangle(float(mx),float(my),x,y,rx,ry)) {
        return &(*curr_note())[i];
    }

}

return NULL;
}
Note *Canvas::get_note_clicked_for_resize(int mx , int my){

float x,y,rx,ry,ryy,radius_x,scr_radius,r;
Note nt;
for(unsigned int i=0;i<curr_note()->size();i++){

    nt=(*curr_note())[i];
    x=nt.x; //koordinati na poleto
    y=nt.y;
    rx=nt.rx;
    ry=nt.ry;
    //rz=nt.z;

    radius_x=rx + CLICK_RADIUS;

    project(x,y,x,y); //yglite na kutiqta
    project(rx,ry,rx,ry);
    project(radius_x,(*curr_note())[i].ry,radius_x,ryy); //to4ka ot radiusa na kryga za resize koqto 6te polzvame da vidim kolko e radiusa na ekrana

    scr_radius=mod(radius_x-rx); //radiusa na kryga na ekrana
    r=mod(dottodot(rx,ry,float(mx),float(my)));

    if(r<=scr_radius){ //ako mi6kata e v kryga za resize(razst ot neq do ygyla na kutiqta e po-malko ot radiusa na kryga)
        return &(*curr_note())[i]; //za da ne se opitva da mesti ili selectira i t.n.
    }

}

return NULL;
}
Link *Canvas::get_link_under_mouse(int x,int y){ //returns one link (not necesserily the top one) onder the mouse

Link *ln;
float a,b,c,h,m_x,m_y;

unproject(x,y,m_x,m_y);

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

void Canvas::move_func(){ //ako sled opredelenoto vreme mi6kata e na sy6toto mqsto i time_out_move ne e izkl (pri vdigane na butona) se vdiga flag-a za move

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
update();

}
void Canvas::set_linking_on()
{
    int x = current_mouse_x;
    int y = current_mouse_y;
    float t_x,t_y;
    float txt_col[] = {0,0,1,1};
    float bg_col[] = {0,0,1,0.1};

    if(misl_i()->curr_nf()->get_first_selected_note()!=NULL && mouse_note==NULL){
        mouse_note=misl_i()->curr_nf()->add_note(misl_i(),"L",t_x,t_y,0,1,1,1,QDateTime(QDate(1,1,1)),QDateTime(QDate(1,1,1)),txt_col,bg_col);
        unproject(x,y,t_x,t_y);
        mouse_note->x=t_x;
        mouse_note->y=t_y;
        mouse_note->link_to_selected();
    }
}
void Canvas::set_linking_off()
{
    misl_i()->curr_nf()->delete_note(mouse_note);
    mouse_note=NULL;
}

int Canvas::copy()
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
int Canvas::cut()
{
    int err=0;

    err+=copy();
    err+=msl_w->curr_misli()->delete_selected();

    return err;
}
int Canvas::paste()
{
    NoteFile *nf=msl_w->curr_misli()->clipboard_nf();
    Note *nt;
    Link *ln;
    float x,y;
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
    unproject(x,y,x,y); //translate them to real GL coords
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
