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

#include "canvas.h"
#include "misli_desktop/misliwindow.h"
#include "notessearch.h"
#include "ui_misliwindow.h"

Canvas::Canvas(MisliWindow *msl_w_)
{

    //Random
    misli_w=msl_w_;
    mouse_note=NULL;
    PushLeft=0;
    timed_out_move=0;
    move_on=0;
    resize_on=0;

    eye_x=0;
    eye_y=0;
    eye_z=misli_w->misli_dg->settings->value("eye_z").toFloat();

    contextMenu = new QMenu(this);

    infoLabel = new QLabel(this);
    infoLabel->setFont(QFont("Halvetica",15));

    searchField = new QLineEdit(this);
    searchField->move(0,0);
    searchField->resize(200,searchField->height());
    searchField->hide();

    //Setting the timer for the move_func
    move_func_timeout = new QTimer(this);
    move_func_timeout->setSingleShot(1);
    connect(move_func_timeout, SIGNAL(timeout()), this, SLOT(move_func()));

    setMouseTracking(1);

}
Canvas::~Canvas()
{
    delete searchField;
    delete contextMenu;
    delete infoLabel;
    delete move_func_timeout;
}

QSize Canvas::sizeHint() const
{
    return QSize(1000, 700);
}
MisliDir * Canvas::misli_dir()
{
    if(misli_w->misli_i()->notes_rdy()){
        return misli_w->misli_i()->curr_misli_dir();
    }
    else {
        d("The program searches for a current note while !notes_rdy()");
        exit (6666);
    }
}
NoteFile * Canvas::curr_nf()
{
    return misli_w->misli_i()->curr_misli_dir()->curr_nf();
}

void Canvas::set_eye_coords_from_curr_nf()
{
    eye_x=curr_nf()->eye_x;
    eye_y=curr_nf()->eye_y;
    eye_z=curr_nf()->eye_z;
}
void Canvas::save_eye_coords_to_nf()
{
    curr_nf()->eye_x=eye_x;
    curr_nf()->eye_y=eye_y;
    curr_nf()->eye_z=eye_z;
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

    screenX = realX + float(width())/2;
    screenY = realY + float(height())/2;
}
void Canvas::unproject(float screenX, float screenY, float &realX, float &realY)
{
    screenX -= float(width())/2;
    screenY -= float(height())/2;

    screenX = screenX/10;
    screenY = screenY/10;

    screenX = screenX*(eye_z*0.01); //screenX = screenX/(1/(eye_z*0.01))
    screenY = screenY*(eye_z*0.01);

    realX = screenX + eye_x;
    realY = screenY + eye_y;
}

void Canvas::paintEvent(QPaintEvent *event)
{
    if(event->isAccepted()){} //remove the "unused variable" warning..

    if(!misli_w->misli_i()->notes_rdy()){
        return;
    }

    QPainter p(this);
    Note *nt;
    float x,y,rx,ry,nt_size_x,nt_size_y,x_projected,y_projected,ry_projected,rx_projected,resize_r_projected;
    float r_tmp_x,r_tmp_y,r_tmp_x2,r_tmp_y2;
    float ln_x1,ln_y1,ln_x2,ln_y2;
    float frame_ratio,pixmap_ratio;
    int displayed_notes=0;

    p.setRenderHint(QPainter::Antialiasing, true); //better antialiasing
    p.fillRect(0,0,width(),height(),QColor(255,255,255,255)); //clear background

    for(unsigned int i=0;i<curr_nf()->note.size();i++){ //for every note

        nt=curr_nf()->note[i];

        x=nt->x;//text coordinates
        y=nt->y;
        rx=nt->rx; //coordinates of the rectangle encapsulating the note
        ry=nt->ry;

        project(rx,ry,rx_projected,ry_projected);
        project(x,y,x_projected,y_projected);

        if( (move_on | resize_on) && nt->selected){ //Draw additional lines to help alignment

            //Set the color
            p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));

            //Draw the lines
            project(x,y-ALIGNMENT_LINE_LENGTH,r_tmp_x,r_tmp_y);
            project(x,ry+ALIGNMENT_LINE_LENGTH,r_tmp_x2,r_tmp_y2);
            p.drawLine(QPointF(r_tmp_x2,r_tmp_y2),QPointF(r_tmp_x,r_tmp_y));

            project(x-ALIGNMENT_LINE_LENGTH,y,r_tmp_x,r_tmp_y);
            project(rx+ALIGNMENT_LINE_LENGTH,y,r_tmp_x2,r_tmp_y2);
            p.drawLine(QPointF(r_tmp_x2,r_tmp_y2),QPointF(r_tmp_x,r_tmp_y));

            project(rx,y-ALIGNMENT_LINE_LENGTH,r_tmp_x,r_tmp_y);
            project(rx,ry+ALIGNMENT_LINE_LENGTH,r_tmp_x2,r_tmp_y2);
            p.drawLine(QPointF(r_tmp_x2,r_tmp_y2),QPointF(r_tmp_x,r_tmp_y));

            project(x-ALIGNMENT_LINE_LENGTH,ry,r_tmp_x,r_tmp_y);
            project(rx+ALIGNMENT_LINE_LENGTH,ry,r_tmp_x2,r_tmp_y2);
            p.drawLine(QPointF(r_tmp_x2,r_tmp_y2),QPointF(r_tmp_x,r_tmp_y));
        }


        project(rx+RESIZE_CIRCLE_RADIUS,ry,r_tmp_x,r_tmp_y);
        nt_size_x = rx_projected - x_projected;
        nt_size_y = ry_projected - y_projected;
        resize_r_projected = r_tmp_x - rx_projected;

        //Draw the note (only if it's on screen (to avoid lag) )
        if(QRectF(x_projected,y_projected,nt_size_x,nt_size_y).intersects(QRectF(0,0,width(),height()))){
            displayed_notes++;
            if( (nt->type==NOTE_TYPE_PICTURE_NOTE) && (nt->text_for_display.size()==0) ){
                frame_ratio = nt->a/nt->b;
                pixmap_ratio = nt->img->width()/nt->img->height();
                if( frame_ratio > pixmap_ratio ){ //if the width for the note frame is proportionally bigger than the pictures width
                    p.drawImage(QPointF(x_projected+(nt_size_x-nt_size_y*pixmap_ratio)/2,y_projected),nt->img->scaled(QSize(nt_size_y*pixmap_ratio,nt_size_y),Qt::IgnoreAspectRatio,Qt::SmoothTransformation));//we resize the note using the height of the frame and a calculated width
                }else if( frame_ratio < pixmap_ratio ){
                    p.drawImage(QPointF(x_projected,y_projected+(nt_size_y-nt_size_x*pixmap_ratio)/2),nt->img->scaled(QSize(nt_size_x,nt_size_x/pixmap_ratio),Qt::IgnoreAspectRatio,Qt::SmoothTransformation));//we resize the note using the width of the frame and a calculated height
                }else{
                    p.drawImage(QPointF(x_projected,y_projected),nt->img->scaled(QSize(nt_size_x,nt_size_y),Qt::IgnoreAspectRatio,Qt::SmoothTransformation));
                }
            }else{
                p.drawImage(QPointF(x_projected,y_projected),nt->img->scaled(QSize(nt_size_x,nt_size_y),Qt::IgnoreAspectRatio,Qt::SmoothTransformation));
            }

            //If the note is redirecting draw a border to differentiate it
            if( (nt->type==NOTE_TYPE_REDIRECTING_NOTE) | (nt->type==NOTE_TYPE_SYSTEM_CALL_NOTE) ){
                p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));
                p.setBrush(QBrush(Qt::NoBrush));
                p.drawRect(QRectF(x_projected,y_projected,nt_size_x,nt_size_y));
            }

            //If it's selected - overpaint with yellow
            if(nt->selected){
                p.setPen(QColor(0,0,0,0));
                p.setBrush(QBrush(QColor(255,255,0,127))); //half-transparent yellow
                p.drawRect(QRectF(x_projected,y_projected,nt_size_x,nt_size_y)); //the yellow marking box

                p.setBrush(QBrush(QColor(nt->bg_col[0]*255,nt->bg_col[1]*255,nt->bg_col[2]*255, 60 ))); //same as BG but transparent
                p.drawEllipse(QPointF(rx_projected,ry_projected),resize_r_projected,resize_r_projected); //the circle for resize
            }

        }

        for(unsigned int n=0;n<nt->outlink.size();n++){ //for every outlink

            Link *ln=&nt->outlink[n];

            project(ln->x1,ln->y1,ln_x1,ln_y1);
            project(ln->x2,ln->y2,ln_x2,ln_y2);

            //Draw the base line
            if(ln->selected){ //overpaint with yellow if it's selected
                p.setPen(QColor(150,150,0,255)); //set color
                p.drawLine(QLineF(ln_x1,ln_y1,ln_x2,ln_y2));
            }else{
                p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));
                p.drawLine(ln_x1,ln_y1,ln_x2,ln_y2);
            }

            //Draw the arrow head
            p.save(); //pushMatrix() (not quite but ~)
                p.translate(ln_x2,ln_y2);
                p.rotate(GetAng(ln_x2,ln_y2+10,ln_x2,ln_y2,ln_x1,ln_y1));

                if(ln->selected){ //overpaint when selected
                    p.setPen(QColor(150,150,0,255));
                    p.drawLine(QLineF(0,0,-5,10)); //both lines for the arrow
                    p.drawLine(QLineF(0,0,5,10));
                }else{
                    p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));
                    p.drawLine(QLineF(0,0,-5,10)); //both lines for the arrow
                    p.drawLine(QLineF(0,0,5,10));
                }
            p.restore();//pop matrix
        } //next link
    } //next note

    //If there's nothing  on the screen (and there are notes in the notefile)
    if( (displayed_notes==0) && !curr_nf()->isEmpty() ) {
        infoLabel->setText(tr("Press CTRL+J to jump to the nearest note."));
        infoLabel->show();
    }else if(mouse_note!=NULL){ //If we're making a link
        infoLabel->setText(tr("Click on a note to link to it."));
        infoLabel->show();
    }else if(curr_nf()->name=="HelpNoteFile"){
        infoLabel->setText(tr("This is the help note file."));
        infoLabel->show();
    }else if(move_on){
        infoLabel->setText(tr("Moving note"));
        infoLabel->show();
    }else{
        infoLabel->hide();
    }


    //============Display search results==================
    if(!misli_w->display_search_results) {return;}

    for(unsigned int i=0;i<misli_w->misli_i()->search_nf->note.size();i++){
        nt = misli_w->misli_i()->search_nf->note[i];
        if(int(i*SEARCH_RESULT_HEIGHT) < height()){
            p.setBrush(QBrush(QColor(255,255,255,255))); //set a clear color
            p.setPen(Qt::NoPen);
            // and clear the area behind the result
            p.drawRect(0,searchField->height() + i*SEARCH_RESULT_HEIGHT,nt->img->width(),nt->img->height());

            p.drawImage(0,searchField->height() + i*SEARCH_RESULT_HEIGHT,*nt->img);
            if(nt->type==NOTE_TYPE_REDIRECTING_NOTE){
                p.setBrush(QBrush(Qt::NoBrush));
                p.setPen(QColor(nt->txt_col[0]*255,nt->txt_col[1]*255,nt->txt_col[2]*255,nt->txt_col[3]*255));
                p.drawRect(0,searchField->height() + i*SEARCH_RESULT_HEIGHT,nt->img->width(),nt->img->height());
            }
        }
    }

}//return

void Canvas::mousePressEvent(QMouseEvent *event)
{
    if(!misli_w->misli_i()->notes_rdy()){return;}

    Note *nt_under_mouse;
    Note *nt_for_resize;
    Note *search_note;
    Link *ln_under_mouse;

    int x = event->x();
    int y = event->y();

    update();//don't put at the end , return get's called earlier in some cases

    if(event->modifiers()==Qt::ControlModifier){ctrl_is_pressed=1;}else ctrl_is_pressed=0;
    if(event->modifiers()==Qt::ShiftModifier){shift_is_pressed=1;}else shift_is_pressed=0;

    if (event->button()==Qt::LeftButton) { //on left button

        //----Save of global variables for other functions-----
        XonPush = x;
        YonPush = y;
        PushLeft=1;
        EyeXOnPush=eye_x;
        EyeYOnPush=eye_y;
        timed_out_move=0;

        if(misli_w->display_search_results){
            for(unsigned int i=0;i<misli_w->misli_i()->search_nf->note.size();i++){
                search_note = misli_w->misli_i()->search_nf->note[i];
                if( point_intersects_with_rectangle(x,y,0,searchField->height() + i*SEARCH_RESULT_HEIGHT,search_note->img->width(),searchField->height() + i*SEARCH_RESULT_HEIGHT+search_note->img->height()) ){
                    search_note->center_eye_on_me();
                    break;
                }
            }
        }

        setFocus(); //needs to be after the search note check , because a click hides the search results through losing focus

        if (mouse_note!=NULL) { // ------------LINKING ON KEY----------

            nt_under_mouse=get_note_under_mouse(x,y);
            if(nt_under_mouse!=NULL){
                set_linking_off();
                nt_under_mouse->link_to_selected();
                curr_nf()->save();
                misli_w->update_current_nf();
                return;
            }else{ //if there's no note under the mouse
                set_linking_off();
                return;
            }

        }

        // -----------RESIZE---------------
        nt_for_resize=get_note_clicked_for_resize(x,y);
        if( !(ctrl_is_pressed | shift_is_pressed) ) { //if neither ctrl or shift are pressed resize only the note under mouse
            curr_nf()->clear_note_selection();
        }
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
            curr_nf()->clear_note_selection();
            curr_nf()->clear_link_selection();
        }

        ln_under_mouse = get_link_under_mouse(x,y); //Za linkove
        if (ln_under_mouse!=NULL){
            ln_under_mouse->selected=1;
        }

        if (nt_under_mouse!=NULL){ //Za notes

            //if( last_release_event.elapsed()<350 ){//it's a doubleclick
            //    doubleClick();
            //}

            if(nt_under_mouse->selected){
                nt_under_mouse->selected=0;
            }else {
                nt_under_mouse->selected=1;
            }

            move_x=x-nt_under_mouse->x;
            move_y=y-nt_under_mouse->y;

            if(shift_is_pressed){
                nt_under_mouse->selected=1;
                for(unsigned int i=0;i<nt_under_mouse->outlink.size();i++){ //select all child notes
                    misli_dir()->nf_by_name(nt_under_mouse->nf_name)->get_note_by_id(nt_under_mouse->outlink[i].id)->selected=1;
                }
            }

            timed_out_move=1;
            move_func_timeout->start(MOVE_FUNC_TIMEOUT);

        }



    }else if(event->button()==Qt::RightButton){

        nt_under_mouse = get_note_under_mouse(x,y);

        contextMenu->clear();

        if(nt_under_mouse!=NULL){
            curr_nf()->clear_note_selection();
            nt_under_mouse->selected=true;

            contextMenu->addAction(misli_w->ui->actionEdit_note);
            contextMenu->addAction(misli_w->ui->actionDelete_selected);
            contextMenu->addAction(misli_w->ui->actionMake_link);
            contextMenu->addSeparator();
            contextMenu->addAction(misli_w->ui->actionDetails);
        }else{
            contextMenu->addAction(misli_w->ui->actionNew_note);
        }
        contextMenu->addMenu(&misli_w->misli_dg->edit_w->chooseNFMenu);
        contextMenu->popup(cursor().pos());

    }

}
void Canvas::mouseReleaseEvent(QMouseEvent *event)
{
    if(!misli_w->misli_i()->notes_rdy()){return;}
    //last_release_event.restart();

    Note * nt;

    if (event->button()==Qt::LeftButton) { //on left button


        PushLeft = 0;

        if(move_on){
            move_on=0;
            for(unsigned int i=0;i<curr_nf()->note.size();i++){
                nt=curr_nf()->note[i];
                if(nt->selected){
                    nt->z=0;
                    nt->calculate_coordinates();
                    nt->storeCoordinatesBeforeMove();
                    nt->correct_links(); //correcting the links
                }
            }
            curr_nf()->save(); //saving the new positions
            misli_w->update_current_nf();

        }else if (resize_on){

            for(unsigned int i=0;i<curr_nf()->note.size();i++){
                nt=curr_nf()->note[i];
                if(nt->selected){
                    nt->correct_links(); //korigirame linkovete
                }
            }
            curr_nf()->save(); //save na novite razmeri
            misli_w->update_current_nf();
            resize_on=0;
        }
        else { //normal move about the canvas
            save_eye_coords_to_nf();
        }
    }
    update();

}
void Canvas::mouseDoubleClickEvent(QMouseEvent *event)
{
    if(!misli_w->misli_i()->notes_rdy()){return;}

    if (event->button()==Qt::LeftButton) { //on left button doubleclick
        doubleClick();
    }

    update();
}
void Canvas::wheelEvent(QWheelEvent *event)
{
    if(!misli_w->misli_i()->notes_rdy()){return;}

    int numDegrees = event->delta() / 8;
    int numSteps = numDegrees / 15;

    eye_z-=MOVE_SPEED*numSteps;
    eye_z = stop(eye_z,1,1000); //can't change eye_z to more than 1000 or less than 1

    save_eye_coords_to_nf();
    update();

    //glutPostRedisplay(); artefact

}
void Canvas::mouseMoveEvent(QMouseEvent *event)
{
    if(!misli_w->misli_i()->notes_rdy()){return;}

    float scr_x,scr_y,scr2_x,scr2_y,nt_x,nt_y,m_x,m_y,d_x,d_y,t_x,t_y;

    Note * nt;

    int x = event->x();
    int y = event->y();

    current_mouse_x=x;
    current_mouse_y=y;

    if(PushLeft){
        if(move_on){

            for(unsigned int i=0;i<curr_nf()->note.size();i++){
                nt=curr_nf()->note[i];
                if(nt->selected){
                    project(nt->move_orig_x+move_x,nt->move_orig_y+move_y,scr_x,scr_y);//position of the mouse on click (every note has a theoretical position of the mouse on click, that's why we dont use x_on_push)
                    scr2_x=scr_x+x-XonPush;//current position of the mouse (again - theoretical for the notes , except for the one from which the move was initiated (for it the position is real))
                    scr2_y=scr_y+y-YonPush;
                    unproject(scr2_x,scr2_y,nt_x , nt_y); //find the mouse position in virtual world (not screen) coords
                    nt->x=nt_x-move_x; //substract the move distance and we get the result
                    nt->y=nt_y-move_y;
                    nt->calculate_coordinates();
                    nt->correct_links();
                }
            }

        }else if(resize_on){

            for(unsigned int i=0;i<curr_nf()->note.size();i++){
                nt=curr_nf()->note[i];
                if(nt->selected){

                    unproject(x,y,m_x,m_y);
                    d_x=m_x - resize_x;
                    d_y=m_y - resize_y;

                    nt->a=stop(d_x,MIN_NOTE_A,MAX_NOTE_A);

                    nt->b=stop(d_y,MIN_NOTE_B,MAX_NOTE_B);
                    nt->calculate_coordinates();
                    nt->storeCoordinatesBeforeMove();
                    nt->checkForFileDefinitions();
                    nt->check_text_for_system_call_definition();
                    nt->checkTextForLinks(misli_dir());
                    nt->adjustTextSize();
                    if(nt->type!=NOTE_TYPE_PICTURE_NOTE) nt->draw_pixmap();
                    nt->correct_links();
                }
            }

        }else{ //Else we're moving about the canvas (respectively - changing the camera position)

            float xrel=x-XonPush,yrel=y-YonPush;
            eye_x=EyeXOnPush-xrel*0.1*(eye_z*0.01); //xrel*1/(1/(eye_z*0.01))
            eye_y=EyeYOnPush-yrel*0.1*(eye_z*0.01);
            save_eye_coords_to_nf();
        }
    }else{ // left button is not pushed
        if(mouse_note!=NULL){

                unproject(x,y,t_x,t_y);
                mouse_note->x=t_x+0.02;
                mouse_note->y=t_y-0.02;
                mouse_note->calculate_coordinates();
                mouse_note->storeCoordinatesBeforeMove();
                mouse_note->correct_links();
            }
    } update();
//return;
}

void Canvas::doubleClick()
{
    Note *nt;
    nt = get_note_under_mouse(current_mouse_x,current_mouse_y);

    if(nt!=NULL){ //if we've clicked on a note
        if(nt->type==NOTE_TYPE_REDIRECTING_NOTE){ //if it's a valid redirecting note
            if(misli_dir()->nf_by_name(nt->address_string)!=NULL)
            misli_dir()->set_current_note_file(nt->address_string); //change notefile
        }else if(nt->type==NOTE_TYPE_TEXT_FILE_NOTE){
            QDesktopServices::openUrl(QUrl("file://"+nt->address_string, QUrl::TolerantMode));
        }else if(nt->type==NOTE_TYPE_SYSTEM_CALL_NOTE){
            QProcess process;
            float mouse_x,mouse_y;

            //Run the command and get the output
            process.start(nt->address_string);
            process.waitForFinished(-1);
            QByteArray out = process.readAllStandardOutput();

            //Put the feedback in a note below the command via the paste from clipboard mechanism
            project(nt->x,nt->ry+1,mouse_x,mouse_y);
            cursor().setPos(QPoint(mouse_x,mouse_y));
            current_mouse_x=mouse_x;
            current_mouse_y=mouse_y;
            misli_w->misli_dg->clipboard()->setText(QString(out));
            misli_w->new_note_from_clipboard();

        }else{ //edit that note
            curr_nf()->clear_note_selection();
            nt->selected=true;
            misli_w->misli_dg->edit_w->edit_note();
        }
    }
    else {//if not on note
        misli_w->misli_dg->edit_w->new_note();
    }
}

Note *Canvas::get_note_under_mouse(int mx , int my)
{
    Note * nt;

    float x,y,rx,ry;

    for(unsigned int i=0;i<curr_nf()->note.size();i++){
        nt = curr_nf()->note[i];
        x=nt->x; //coordinates of the box
        y=nt->y;
        rx=nt->rx;
        ry=nt->ry;

        project(x,y,x,y); //the corners of the box in screen coords
        project(rx,ry,rx,ry);


        if( point_intersects_with_rectangle(float(mx),float(my),x,y,rx,ry)) {
            //qDebug()<<"Note under mouse is "<<nt->text;
            if(nt!=mouse_note) return nt; //sloppy way to do it ,but works and it simple
        }

    }

return NULL;
}
Note *Canvas::get_note_clicked_for_resize(int mx , int my)
{
    float x,y,rx,ry,ryy,radius_x,scr_radius,r;
    Note *nt;

    for(unsigned int i=0;i<curr_nf()->note.size();i++){

        nt=curr_nf()->note[i];
        x=nt->x; //coordinates of the box
        y=nt->y;
        rx=nt->rx;
        ry=nt->ry;
        //rz=nt.z;

        radius_x=rx + RESIZE_CIRCLE_RADIUS;

        project(x,y,x,y); //calculate them in screen coords
        project(rx,ry,rx,ry);
        project(radius_x,nt->ry,radius_x,ryy); //project a point from the edge around the resizing circle

        scr_radius=mod(radius_x-rx); //radius of the circle for resizing in screen coords

        r=mod(dottodot(rx,ry,float(mx),float(my))); //distance mouse<->corner for resize
        if(r<=scr_radius){ //if the mouse is in the resizing circle
            return nt;
        }

    }

    return NULL;
}
Link *Canvas::get_link_under_mouse(int x,int y){ //returns one link (not necesserily the top one) onder the mouse

Link *ln;
float a,b,c,h,m_x,m_y;

unproject(x,y,m_x,m_y);

for(unsigned int i=0;i<curr_nf()->note.size();i++){
    for(unsigned int l=0;l<curr_nf()->note[i]->outlink.size();l++){ //for every link
        ln=&curr_nf()->note[i]->outlink[l];
        a=dottodot3(ln->x1,ln->y1,ln->z1,ln->x2,ln->y2,ln->z2); //link lenght
        b=dottodot3(m_x,m_y,0,ln->x2,ln->y2,ln->z2);
        c=dottodot3(m_x,m_y,0,ln->x1,ln->y1,ln->z1);
        h=distance_to_line(m_x,m_y,0,ln->x1,ln->y1,ln->z1,ln->x2,ln->y2,ln->z2);
        if( ( (c<a) && (b<a) ) && ( h <= (CLICK_RADIUS*2) ) ){ //if the mouse is not intersecting with a projection of the link but the link itself
            return ln;
        }

    }
}

return NULL;

}

void Canvas::move_func(){ //if the mouse hasn't moved and time_out_move is not off the move flag is set to true

    int x=current_mouse_x;
    int y=current_mouse_y;

    float dist = dottodot(XonPush,YonPush,x,y);

    if( (timed_out_move && PushLeft ) && ( dist<MOVE_FUNC_TOLERANCE ) ){

        get_note_under_mouse(x,y)->selected=1; //to pickup a selected note with control pressed (not to deselect it)
        move_on=1;
        for(unsigned int i=0;i<curr_nf()->note.size();i++){
            if(curr_nf()->note[i]->selected){
                    curr_nf()->note[i]->z=move_z;
                    curr_nf()->note[i]->correct_links();
            }
        }
    }

timed_out_move=0;
update();

}
void Canvas::set_linking_on()
{
    float x = current_mouse_x;
    float y = current_mouse_y;
    float txt_col[] = {0,0,1,1};
    float bg_col[] = {0,0,1,0.1};

    //Create a dummy note called a mouse note that will be attached to the mouse and hopefully not noticed
    if(curr_nf()->get_first_selected_note()!=NULL && mouse_note==NULL){
        unproject(x,y,x,y);
        mouse_note=curr_nf()->add_note("L",x,y,0,1,1,1,QDateTime(QDate(1,1,1)),QDateTime(QDate(1,1,1)),txt_col,bg_col);
        mouse_note->link_to_selected();
    }
}
void Canvas::set_linking_off()
{
    //remove the mouse note and set it to NULL , that's the signal that we're not linking anything
    curr_nf()->delete_note(mouse_note);
    curr_nf()->save();
    misli_w->update_current_nf();
    mouse_note=NULL;
}

int Canvas::paste()
{
    NoteFile *clipboard_nf=misli_w->clipboard_nf,*target_nf;
    Note *nt;
    Link *ln;
    float x,y;
    int old_id;

    misli_w->doing_cut_paste=true;

    clipboard_nf->make_all_ids_negative();

    //Make coordinates relative to the mouse
    x=current_mouse_x; //get mouse screen coords
    y=current_mouse_y;
    unproject(x,y,x,y); //translate them to canvas coords
    clipboard_nf->make_coords_relative_to(-x,-y);

    //Copy the notes over to the target
    misli_w->copy_selected_notes(clipboard_nf,curr_nf());

    //return clipboard notes' coordinates to 0
    clipboard_nf->make_coords_relative_to(x,y);

    target_nf=curr_nf();

    //Replace the negative id-s with real ones
    for(unsigned int n=0;n<target_nf->note.size();n++){ //for every note

        nt=target_nf->note[n];

        if(nt->id<0){ //only for the pasted notes (with negative id-s)
            old_id = nt->id;
            nt->id = target_nf->get_new_id();

            //Fix the id-s in the links
            for(unsigned int i=0;i<target_nf->note.size();i++){ //for every note
                for(unsigned int l=0;l<target_nf->note[i]->outlink.size();l++){ //for every outlink
                    ln=&target_nf->note[i]->outlink[l];
                    if(ln->id==old_id){ ln->id=nt->id ; } //if it has the old id - set it up with the new one
                }
                for(unsigned int in=0;in<target_nf->note[i]->inlink.size();in++){ //for every inlink
                    if(target_nf->note[i]->inlink[in]==old_id){ target_nf->note[i]->inlink[in]=nt->id ; } //if it has the old id - set it up with the new one
                }
            }
            nt->init();
            nt->init_links();
        }
    }

    clipboard_nf->make_all_ids_negative(); //restore ids to positive in the clipboard
    target_nf->save();
    misli_w->update_current_nf();
    return 0;
}

void Canvas::jump_to_nearest_note()
{
    Note * nt,*nearest_note;
    float best_result = 10000,result,x_unprojected,y_unprojected;

    unproject(current_mouse_x,current_mouse_y,x_unprojected,y_unprojected);

    for(unsigned int i=0;i<curr_nf()->note.size();i++){
        nt=curr_nf()->note[i];
        result = dottodot3(x_unprojected,y_unprojected,0,nt->x,nt->y,nt->z);
        if( result<best_result ){
            nearest_note = nt;
            best_result = result;
        }
    }

    if(best_result!=10000){
        nearest_note->center_eye_on_me();
    }
}
