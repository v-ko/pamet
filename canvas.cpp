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

Canvas::Canvas(MisliWindow *misliWindow_)
{
    hide();

    //Random
    misliWindow = misliWindow_;
    linkingNote = NULL;
    PushLeft = false;
    timedOutMove = false;
    moveOn = false;
    resizeOn = false;

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
    connect(move_func_timeout, SIGNAL(timeout()), this, SLOT(startMove()));

    setMouseTracking(1);
    setFocusPolicy(Qt::ClickFocus);
}
Canvas::~Canvas()
{
    delete searchField;
    delete contextMenu;
    delete infoLabel;
    delete move_func_timeout;
}
QPointF Canvas::project(QPointF point)
{
    return QPointF(projectX(point.x()),projectY(point.y()));
}
QLineF Canvas::project(QLineF line)
{
    return QLineF(project(line.p1()),project(line.p2()));
}
QRectF Canvas::project(QRectF rect)
{
    return QRectF(project(rect.topLeft()),project(rect.bottomRight()));
}
void Canvas::project(float realX, float realY, float &screenX, float &screenY)
{
    screenX = projectX(realX);
    screenY = projectY(realY);
}
void Canvas::unproject(float screenX, float screenY, float &realX, float &realY)
{
    realX = unprojectX(screenX);
    realY = unprojectY(screenY);
}
float Canvas::projectX(float realX)
{
    realX -= noteFile()->eyeX;
    realX = realX/noteFile()->eyeZ; //The heigher we look from - the smaller the note
    realX = realX*1000; //More readable note sizes (and not to break compatability, this section was changed)
    return realX + float(width())/2;
}
float Canvas::projectY(float realY)
{
    realY -= noteFile()->eyeY;
    realY = realY/noteFile()->eyeZ;
    realY = realY*1000;
    return realY + float(height())/2;
}
float Canvas::unprojectX(float screenX)
{
    screenX -= float(width())/2;
    screenX = screenX/1000;
    screenX = screenX*noteFile()->eyeZ;
    return screenX + noteFile()->eyeX;
}
float Canvas::unprojectY(float screenY)
{
    screenY -= float(height())/2;
    screenY = screenY/1000;
    screenY = screenY*noteFile()->eyeZ;
    return screenY + noteFile()->eyeY;
}

void Canvas::paintEvent(QPaintEvent*)
{
    if(noteFile()==NULL) return;

    QPainter p;
    if(!p.begin((this))){
        qDebug()<<"[Canvas::paintEvent]Failed to initialize painter.";
    }
    float x,y,rectX,rectY,resizeCircleRadiusProjected;
    float frame_ratio,pixmap_ratio;
    int displayed_notes=0;

    p.setRenderHint(QPainter::Antialiasing, true); //better antialiasing
    p.fillRect(0,0,width(),height(),QColor(255,255,255,255)); //clear background

    for(Note* nt: noteFile()->notes){

        x=nt->rect().x();
        y=nt->rect().y();
        rectX = nt->rect().right(); //coordinates of the rectangle encapsulating the note
        rectY = nt->rect().bottom();

        QRectF projectedNoteRect = project(nt->rect());
        resizeCircleRadiusProjected = RESIZE_CIRCLE_RADIUS*1000/noteFile()->eyeZ;

        if( (moveOn | resizeOn) && nt->isSelected_m){ //Draw additional lines to help alignment

            //Set the color
            p.setPen(nt->textColor());

            //Draw the lines
            QLineF leftLine, rightLine, bottomLine, topLine;
            leftLine.setLine(x,y-ALIGNMENT_LINE_LENGTH,x,rectY+ALIGNMENT_LINE_LENGTH);
            rightLine.setLine(rectX,y-ALIGNMENT_LINE_LENGTH,rectX,rectY+ALIGNMENT_LINE_LENGTH);
            bottomLine.setLine(x-ALIGNMENT_LINE_LENGTH,rectY,rectX+ALIGNMENT_LINE_LENGTH,rectY);
            topLine.setLine(x-ALIGNMENT_LINE_LENGTH,y,rectX+ALIGNMENT_LINE_LENGTH,y);

            p.drawLine(project(leftLine));
            p.drawLine(project(rightLine));
            p.drawLine(project(bottomLine));
            p.drawLine(project(topLine));
        }

        //Check the validity of the address string
        if(nt->type==NoteType::redirecting){
            if(misliWindow->currentDir()->noteFileByName(nt->addressString)==NULL &&
                    nt->textForShortening()!=tr("Missing note file"))
            {
                nt->setTextForShortening(tr("Missing note file"));
            }
        }

        //Draw the note (only if it's on screen (to avoid lag) )
        QRectF imageRect = projectedNoteRect;
        if(projectedNoteRect.intersects(QRectF(0,0,width(),height()))){
            displayed_notes++;
            //If it's a picture note - resize appropriately to fit in the note boundaries
            if( (nt->type==NoteType::picture) && nt->textForDisplay_m.isEmpty() ){
                frame_ratio = nt->rect().width()/nt->rect().height();
                pixmap_ratio = nt->img->width()/nt->img->height();

                if( frame_ratio > pixmap_ratio ){
                    //if the width for the note frame is proportionally bigger than the pictures width
                    //we resize the note using the height of the frame and a calculated width
                    imageRect.setWidth(imageRect.height()*pixmap_ratio);
                    imageRect.moveCenter(projectedNoteRect.center());
                }else if( frame_ratio < pixmap_ratio ){
                    //we resize the note using the width of the frame and a calculated height
                    imageRect.setHeight(imageRect.width()/pixmap_ratio);
                    imageRect.moveCenter(projectedNoteRect.center());
                }
            }
            p.drawImage(imageRect.topLeft(),nt->img->scaled(QSize(imageRect.size().width(),imageRect.size().height()),
                                                            Qt::IgnoreAspectRatio,
                                                            Qt::SmoothTransformation));

            //If the note is redirecting draw a border to differentiate it
            if( (nt->type==NoteType::redirecting) | (nt->type==NoteType::systemCall) ){
                p.setPen(nt->textColor());
                p.setBrush(QBrush(Qt::NoBrush));
                p.drawRect(projectedNoteRect);
            }

            //If it's selected - overpaint with yellow
            if(nt->isSelected_m){
                p.setPen(QColor(0,0,0,0));
                p.setBrush(QBrush(QColor(255,255,0,127))); //half-transparent yellow
                p.drawRect(projectedNoteRect); //the yellow marking box

                //The circle for resize
                QColor circleColor = nt->backgroundColor();
                circleColor.setAlpha(60);//same as BG but transparent
                p.setBrush(QBrush(circleColor));
                p.drawEllipse(projectedNoteRect.bottomRight(),resizeCircleRadiusProjected,resizeCircleRadiusProjected);
            }
        }

        for(Link ln: nt->outlinks){

            //Draw the base line
            if(ln.selected){ //overpaint with yellow if it's selected
                p.setPen(QColor(150,150,0,255)); //set color
                p.drawLine(project(ln.line));
            }else{
                p.setPen(nt->textColor());
                p.drawLine(project(ln.line));
            }

            //Draw the arrow head
            p.save(); //pushMatrix() (not quite but ~)
                p.translate( project(ln.line.p2()) );
                p.rotate(90-ln.line.angle());

                if(ln.selected){ //overpaint when selected
                    p.setPen(QColor(150,150,0,255));
                    p.drawLine(QLineF(0,0,-5,10)); //both lines for the arrow
                    p.drawLine(QLineF(0,0,5,10));
                }else{
                    p.setPen(nt->textColor());
                    p.drawLine(QLineF(0,0,-5,10)); //both lines for the arrow
                    p.drawLine(QLineF(0,0,5,10));
                }
            p.restore();//pop matrix
        } //next link
    } //next note

    //If there's nothing  on the screen (and there are notes in the notefile)
    if( (displayed_notes==0) && !noteFile()->notes.isEmpty() ) {
        misliWindow->ui->jumpToNearestNotePushButton->show();
    }else if(linkingNote!=NULL){ //If we're making a link
        infoLabel->setText(tr("Click on a note to link to it."));
        infoLabel->show();
    }else if(noteFile()==misliWindow->helpNoteFile){
        infoLabel->setText(tr("This is the help note file."));
        infoLabel->show();
    }else if(moveOn){
        infoLabel->setText(tr("Moving note"));
        infoLabel->show();
    }else{
        infoLabel->hide();
        misliWindow->ui->jumpToNearestNotePushButton->hide();
    }
}

void Canvas::mousePressEvent(QMouseEvent *event)
{
    if(noteFile()==NULL) return;

    Note *nt_under_mouse;
    Note *nt_for_resize;
    Link *ln_under_mouse;
    bool ctrl_is_pressed,shift_is_pressed;

    int x = event->x();
    int y = event->y();

    update();//don't put at the end , return get's called earlier in some cases

    if(event->modifiers()==Qt::ControlModifier){ctrl_is_pressed=true;}else ctrl_is_pressed=false;
    if(event->modifiers()==Qt::ShiftModifier){shift_is_pressed=true;}else shift_is_pressed=false;

    if (event->button()==Qt::LeftButton) { //on left button

        //----Save of global variables for other functions-----
        XonPush = x;
        YonPush = y;
        PushLeft = true;
        EyeXOnPush = noteFile()->eyeX;
        EyeYOnPush = noteFile()->eyeY;
        timedOutMove=false;

        if (linkingIsOn()) { // ------------LINKING ON KEY----------

            nt_under_mouse=getNoteUnderMouse(x,y);
            setLinkingState(false);
            if(nt_under_mouse!=NULL){
                noteFile()->linkSelectedNotesTo(nt_under_mouse);
                noteFile()->save();
            }else{ //if there's no note under the mouse
                update();
            }
            return;
        }

        // -----------RESIZE---------------
        nt_for_resize=getNoteClickedForResize(x,y);
        if( !(ctrl_is_pressed | shift_is_pressed) ) { //if neither ctrl or shift are pressed resize only the note under mouse
            noteFile()->clearNoteSelection();
        }
        if (nt_for_resize!=NULL){
            nt_for_resize->setSelected(true);
            resizeOn=true;
            resizeX=nt_for_resize->rect().x();
            resizeY=nt_for_resize->rect().y();
            return;
        }

        //----------SELECT------------
        //Clear selection if there are no modifiers
        if( !(ctrl_is_pressed | shift_is_pressed) ) {
            noteFile()->clearNoteSelection();
            noteFile()->clearLinkSelection();
        }

        //Select links
        ln_under_mouse = getLinkUnderMouse(x,y);
        if (ln_under_mouse!=NULL){
            ln_under_mouse->selected=true;
        }

        //Select notes
        nt_under_mouse = getNoteUnderMouse(x,y);
        if (nt_under_mouse!=NULL){

            //if( last_release_event.elapsed()<350 ){//it's a doubleclick
            //    doubleClick();
            //}

            if(nt_under_mouse->isSelected()){
                nt_under_mouse->setSelected(false);
            }else {
                nt_under_mouse->setSelected(true);
            }

            moveX=x-nt_under_mouse->rect().x();
            moveY=y-nt_under_mouse->rect().y();

            if(shift_is_pressed){
                //Select all notes this one links to
                nt_under_mouse->setSelected(true);
                for(Link ln: nt_under_mouse->outlinks){
                    noteFile()->getNoteById(ln.id)->setSelected(true);
                }
            }

            timedOutMove=true;
            move_func_timeout->start(MOVE_FUNC_TIMEOUT);
        }



    }else if(event->button()==Qt::RightButton){

        nt_under_mouse = getNoteUnderMouse(x,y);

        contextMenu->clear();

        if(nt_under_mouse!=NULL){
            noteFile()->clearNoteSelection();
            nt_under_mouse->isSelected_m=true;

            contextMenu->addAction(misliWindow->ui->actionEdit_note);
            contextMenu->addAction(misliWindow->ui->actionDelete_selected);
            contextMenu->addAction(misliWindow->ui->actionMake_link);
            contextMenu->addSeparator();
            contextMenu->addAction(misliWindow->ui->actionDetails);
        }else{
            contextMenu->addAction(misliWindow->ui->actionNew_note);
        }
        contextMenu->addMenu(&misliWindow->edit_w->chooseNFMenu);
        contextMenu->popup(cursor().pos());
    }

}
void Canvas::mouseReleaseEvent(QMouseEvent *event)
{
    if(noteFile()==NULL) return;
    //last_release_event.restart();

    if(event->button()==Qt::LeftButton){
        PushLeft = false;

        if(moveOn){
            moveOn = false;
            noteFile()->save(); //saving the new positions
            noteFile()->initLinks();
        }else if(resizeOn){
            resizeOn = false;
            noteFile()->save(); //save the new size
            noteFile()->initLinks();
        }
    }
}
void Canvas::mouseDoubleClickEvent(QMouseEvent *event)
{
    if(noteFile()==NULL) return;

    if (event->button()==Qt::LeftButton) { //on left button doubleclick
        doubleClick();
    }
}
void Canvas::wheelEvent(QWheelEvent *event)
{
    if(noteFile()==NULL) return;

    int numDegrees = event->delta() / 8;
    int numSteps = numDegrees / 15;

    noteFile()->eyeZ-=MOVE_SPEED*numSteps;
    noteFile()->eyeZ = stop(noteFile()->eyeZ,1,1000); //can't change eye_z to more than 1000 or less than 1

    update();
    //glutPostRedisplay(); artefact
}
void Canvas::mouseMoveEvent(QMouseEvent *event)
{
    if(noteFile()==NULL) return;

    float scr_x,scr_y,scr2_x,scr2_y,nt_x,nt_y,m_x,m_y,d_x,d_y,t_x,t_y;

    int x = event->x();
    int y = event->y();

    current_mouse_x=x;
    current_mouse_y=y;

    if(PushLeft){
        if(moveOn){

            for(Note *nt:noteFile()->notes){
                if(nt->isSelected()){
                    project(nt->xBeforeMove+moveX,nt->yBeforeMove+moveY,scr_x,scr_y);//position of the mouse on click (every note has a theoretical position of the mouse on click, that's why we dont use x_on_push)
                    scr2_x = scr_x + x - XonPush;//current position of the mouse (again - theoretical for the notes , except for the one from which the move was initiated (for it the position is real))
                    scr2_y = scr_y + y - YonPush;
                    unproject(scr2_x, scr2_y, nt_x, nt_y); //find the mouse position in real coords (not screen)
                    nt->rect().moveLeft(nt_x - moveX); //substract the move distance and we get the result
                    nt->rect().moveTop(nt_y - moveY);
                    noteFile()->initLinks();
                }
            }

        }else if(resizeOn){

            for(Note *nt:noteFile()->notes){
                if(nt->isSelected_m){

                    unproject(x,y,m_x,m_y);
                    d_x = m_x - resizeX;
                    d_y = m_y - resizeY;

                    nt->rect().setWidth( stop(d_x,MIN_NOTE_A,MAX_NOTE_A) );
                    nt->rect().setHeight( stop(d_y,MIN_NOTE_B,MAX_NOTE_B) );

                    nt->adjustTextSize();
                    if(nt->type!=NoteType::picture) nt->drawPixmap();
                    noteFile()->initLinks();
                }
            }

        }else{ //Else we're moving about the canvas (respectively - changing the camera position)

            float xrel=x-XonPush,yrel=y-YonPush;
            noteFile()->eyeX = EyeXOnPush - xrel*noteFile()->eyeZ/1000; // eyez/1000 is the transform factor practically
            noteFile()->eyeY = EyeYOnPush - yrel*noteFile()->eyeZ/1000;
            update();
        }
    }else{ // left button is not pushed
        if(linkingNote!=NULL){
            unproject(x,y,t_x,t_y);
            linkingNote->rect().moveLeft(t_x+0.02);//+0.02 so it's not under the mouse apex
            linkingNote->rect().moveTop(t_y-0.02);
            //linkingNote->storeCoordinatesBeforeMove(); FIXME
            noteFile()->initLinks();
        }
    }
}

void Canvas::doubleClick()
{
    Note *nt = getNoteUnderMouse(current_mouse_x,current_mouse_y);

    if(nt!=NULL){ //if we've clicked on a note
        if(nt->type==NoteType::redirecting){ //if it's a valid redirecting note

            if(misliWindow->currentDir()->noteFileByName(nt->addressString)!=NULL)
            setNoteFile(misliWindow->currentDir()->noteFileByName(nt->addressString));

        }else if(nt->type==NoteType::textFile){

            QDesktopServices::openUrl(QUrl("file://"+nt->addressString, QUrl::TolerantMode));

        }else if(nt->type==NoteType::systemCall){

            QProcess process;

            //Run the command and get the output
            process.start(nt->addressString);
            process.waitForFinished(-1);
            QByteArray out = process.readAllStandardOutput();

            //Put the feedback in a note below the command via the paste from clipboard mechanism
            Note *newNote = noteFile()->addNote(new Note(noteFile()->getNewId(),
                                         QString(out),
                                         QRect(nt->rect().x(),nt->rect().bottom()+1,1,1),
                                         1,
                                         QDateTime::currentDateTime(),
                                         QDateTime::currentDateTime(),
                                         nt->textColor(),
                                         nt->backgroundColor()));
            newNote->autoSize();

        }else{ //Edit that note
            noteFile()->clearNoteSelection();
            nt->setSelected(true);
            misliWindow->edit_w->editNote();
        }
    }
    else {//if not on note
        misliWindow->edit_w->newNote();
    }
}

Note *Canvas::getNoteUnderMouse(int mouseX, int mouseY)
{
    for(Note *nt: noteFile()->notes){
        if( project(nt->rect()).intersects(QRectF(mouseX,mouseY,1,1))){
            return nt;
        }
    }

    //Old code// FIXME - remove it
    /*
    Note * nt;

    float x,y,rx,ry;
    for(unsigned int i=0;i<noteFile()->notes.size();i++){
        nt = noteFile()->notes[i];
        x=nt->x; //coordinates of the box
        y=nt->y;
        rx=nt->x+nt->a;
        ry=nt->y+nt->b;

        project(x,y,x,y); //the corners of the box in screen coords
        project(rx,ry,rx,ry);


        if( project(nt->rect()).intersects(QRectF(mouseX,mouseY,1,1))){
        //if( point_intersects_with_rectangle(float(mouseX),float(mouseY),x,y,rx,ry)) {
            //qDebug()<<"Note under mouse is "<<nt->text;
            //if(nt!=linkingNote)  //sloppy way to do it ,but works and it simple
            return nt;
        }

    }*/

return NULL;
}
Note *Canvas::getNoteClickedForResize(int mouseX , int mouseY)
{
    //Old code// FIXME - remove it
    /*
    float x,y,rx,ry,ryy,radius_x,scr_radius,r;
    Note *nt;

    for(unsigned int i=0;i<noteFile()->notes.size();i++){

        nt=noteFile()->notes[i];
        x=nt->x; //coordinates of the box
        y=nt->y;
        rx=nt->x+nt->a;
        ry=nt->y+nt->b;
        //rz=nt.z;

        radius_x=rx + RESIZE_CIRCLE_RADIUS;

        project(x,y,x,y); //calculate them in screen coords
        project(rx,ry,rx,ry);
        project(radius_x,nt->ry,radius_x,ryy); //project a point from the edge around the resizing circle

        scr_radius=mod(radius_x-rx); //radius of the circle for resizing in screen coords

        r=mod(dottodot(rx,ry,float(mouseX),float(mouseY))); //distance mouse<->corner for resize
        if(r<=scr_radius){ //if the mouse is in the resizing circle
            return nt;
        }

    }*/

    for(Note *nt: noteFile()->notes){
        if(dottodot(unprojectX(mouseX),unprojectY(mouseY),nt->rect().right(),nt->rect().bottom())<=RESIZE_CIRCLE_RADIUS){
            return nt;
        }
    }
    return NULL;
}
Link *Canvas::getLinkUnderMouse(int mouseX,int mouseY) //returns one link (not necesserily the top one) onder the mouse
{
    float a,b,c,h,unprojMouseX = unprojectX(mouseX), unprojMouseY = unprojectY(mouseY) ;
    //unproject(mouseX,mouseY,mouseX,mouseY);

    //Old code// FIXME - remove it
    /*
    for(unsigned int i=0;i<noteFile()->notes.size();i++){
        for(unsigned int l=0;l<noteFile()->notes[i]->outlink.size();l++){ //for every link
            ln=&noteFile()->notes[i]->outlink[l];
            a=dottodot3(ln->x1,ln->y1,ln->z1,ln->x2,ln->y2,ln->z2); //link lenght
            b=dottodot3(mouseX,mouseY,0,ln->x2,ln->y2,ln->z2);
            c=dottodot3(mouseX,mouseY,0,ln->x1,ln->y1,ln->z1);
            h=distance_to_line(mouseX,mouseY,0,ln->x1,ln->y1,ln->z1,ln->x2,ln->y2,ln->z2);
            if( ( (c<a) && (b<a) ) && ( h <= (CLICK_RADIUS*2) ) ){ //if the mouse is not intersecting with a projection of the link but the link itself
                return ln;
            }

        }
    }*/

    for(Note *nt: noteFile()->notes){
        for(Link &ln: nt->outlinks){
            a=ln.line.length();
            b=dottodot(unprojMouseX,unprojMouseY,ln.line.x2(),ln.line.y2());
            c=dottodot(unprojMouseX,unprojMouseY,ln.line.x1(),ln.line.y1());
            h=distance_to_line(unprojMouseX,unprojMouseY,0,ln.line.x1(),ln.line.y1(), 0, ln.line.x2(), ln.line.y2(), 0);
            if( ( (c<a) && (b<a) ) && ( h <= (CLICK_RADIUS*2) ) ){ //if the mouse is not intersecting with a projection of the link but the link itself
                return &ln;
            }
        }
    }
    return NULL;
}

void Canvas::startMove(){ //if the mouse hasn't moved and time_out_move is not off the move flag is set to true

    int x=current_mouse_x;
    int y=current_mouse_y;

    float dist = dottodot(XonPush,YonPush,x,y);

    if( (timedOutMove && PushLeft ) && ( dist<MOVE_FUNC_TOLERANCE ) ){

        getNoteUnderMouse(x,y)->setSelected(true); //to pickup a selected note with control pressed (not to deselect it)

        //Store all the coordinates before the move
        for(Note *nt: misliWindow->currentDir()->currentNoteFile->notes){
            if(nt->isSelected()) nt->storeCoordinatesBeforeMove();
        }
        moveOn = true;
        update();
    }

    timedOutMove = false;
}
bool Canvas::linkingIsOn()
{
    if(linkingNote==NULL){
        return false;
    }else{
        return true;
    }
}

void Canvas::setLinkingState(bool setLinkingOn)
{
    if(setLinkingOn){
        float x = unprojectX(current_mouse_x);
        float y = unprojectY(current_mouse_y);

        //Create a dummy note that will be attached to the mouse
        if(noteFile()->getFirstSelectedNote()!=NULL && linkingNote==NULL){
            linkingNote = noteFile()->loadNote(new Note(noteFile()->getNewId(),
                                                      "linkingNote",
                                                      QRectF(x,y,0.1,0.1),
                                                      1,
                                                      QDateTime::currentDateTime(),
                                                      QDateTime::currentDateTime(),
                                                      Qt::red,
                                                      Qt::red));
            noteFile()->linkSelectedNotesTo(linkingNote);
        }
    }else{
        //Remove the mouse note and set it to NULL , that's the signal that we're not linking anything
        if(linkingIsOn()){
            noteFile()->notes.removeOne(linkingNote);
            delete linkingNote;
            linkingNote=NULL;
        }
    }

    emit linkingStateToggled(setLinkingOn);
}

QString Canvas::copySelectedNotes(NoteFile *sourceNotefile, NoteFile *targetNoteFile)
{
    QString clip_text;

    //Copy selected notes (only the info that would be in the file)
    for(Note *nt_in_source: sourceNotefile->notes){
        if(nt_in_source->isSelected()){
            Note *nt_in_target = targetNoteFile->cloneNote(nt_in_source);
            //Add the links
            nt_in_target->outlinks = nt_in_source->outlinks;
            //Add the note text to the regular clipboard
            clip_text+=nt_in_source->text_m;
            clip_text+="\n\n"; //leave space before the next (gets trimmed in the end)
        }
    }

    return clip_text;
}

void Canvas::paste()
{
    NoteFile *clipboardNF=misliWindow->clipboardNoteFile;
    float x,y;
    int old_id;

    clipboardNF->makeAllIDsNegative();

    //Make coordinates relative to the mouse
    x=current_mouse_x; //get mouse screen coords
    y=current_mouse_y;
    unproject(x,y,x,y); //translate them to canvas coords
    clipboardNF->makeCoordsRelativeTo(-x,-y);

    //Copy the notes over to the target
    clipboardNF->selectAllNotes();
    copySelectedNotes(clipboardNF, noteFile());

    //return clipboard notes' coordinates to 0
    clipboardNF->makeCoordsRelativeTo(x,y);

    //Replace the negative id-s with real ones
    for(Note *nt: noteFile()->notes){

        if(nt->id<0){ //only for the pasted notes (with negative id-s)
            old_id = nt->id;
            nt->id = noteFile()->getNewId();

            //Now check ALL of the links in the NF for that id and change them
            for(Note *nt2: noteFile()->notes){
                for(Link &ln: nt2->outlinks){
                    if(ln.id==old_id){ ln.id=nt->id ; } //if it has the old id - set it up with the new one
                }
            }
        }
    }
    noteFile()->initLinks();

    clipboardNF->makeAllIDsNegative(); //restore ids to positive in the clipboard
    noteFile()->save();
}

void Canvas::jumpToNearestNote()
{
    Note *nearest_note;
    float best_result = 10000,result,x_unprojected,y_unprojected;

    unproject(current_mouse_x,current_mouse_y,x_unprojected,y_unprojected);

    for(Note *nt: noteFile()->notes){
        result = dottodot(x_unprojected,y_unprojected,nt->rect().x(),nt->rect().y());
        if( result<best_result ){
            nearest_note = nt;
            best_result = result;
        }
    }

    if(best_result!=10000){
        centerEyeOnNote(nearest_note);
    }
}

NoteFile* Canvas::noteFile()
{
    if(misliWindow->currentDir()==NULL){
        return NULL;
    }else{
        return misliWindow->currentDir()->currentNoteFile;
    }
}
void Canvas::setNoteFile(NoteFile *newNoteFile)
{
    MisliDir *misliDir = misliWindow->currentDir();

    if(misliDir==NULL){
        if(newNoteFile!=NULL){
            qDebug()<<"[Canvas::setNoteFile]Trying to set a notefile while currentDir is NULL.";
            return;
        }else{ //Just update the UI - that's all that's needed in that case
            hide();
            misliWindow->ui->jumpToNearestNotePushButton->hide();
            misliWindow->ui->makeNoteFilePushButton->show();
            misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(false);
            misliWindow->updateNoteFilesListMenu();
            misliWindow->updateTitle();
            update();
            return;
        }
    }

    disconnect(visualChangeConnection);
    disconnect(noteTextChangedConnection);

    if(newNoteFile==NULL){
        //Check the current dir for NFs
        if(!misliDir->noteFiles().isEmpty()){
            //If it's not empty set a notefile - the default or there's none - the first
            if(misliDir->defaultNfOnStartup()!=NULL){
                setNoteFile(misliDir->defaultNfOnStartup());
                return;
            }else{
                setNoteFile(misliDir->noteFiles()[0]);
                return;
            }
        }else{ //If there's no notefile in the dir
            //On the first start - set the default NF (with some help notes)
            if(misliWindow->misli_dg->firstProgramStart()){
                QString path = QDir(misliWindow->currentDir()->directoryPath()).filePath("notes.misl");
                QFile ntFile(path);
                QFile::copy(":/other/initial_start_nf_"+misliWindow->misli_dg->language()+".misl",path);
                ntFile.setPermissions(QFile::ReadOwner | QFile::WriteOwner);//in the qrc the file is RO, we need RW
                misliWindow->currentDir()->addNoteFile(path);
                return;
            }else{//Else the "Make new notefile" button is shown and the user will do so
                hide();
                misliWindow->ui->jumpToNearestNotePushButton->hide();
                misliWindow->ui->makeNoteFilePushButton->show();
                misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(false);
            }
        }
    }else if(!misliWindow->currentDir()->noteFiles().contains(newNoteFile)){
        qDebug()<<"[Canvas::setNoteFile]Trying to set a notefile that does not belong to the current misli dir.";
        return;
    }else{
        visualChangeConnection = connect(newNoteFile,SIGNAL(visualChange()),this,SLOT(update()));
        noteTextChangedConnection = connect(newNoteFile,&NoteFile::noteTextChanged,
                                            misliWindow->notes_search,[&](NoteFile* nf){
            misliWindow->notes_search->loadNotes(nf, misliWindow->currentDir(),1);
        });

        misliWindow->ui->jumpToNearestNotePushButton->show();
        misliWindow->ui->makeNoteFilePushButton->hide();
        misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(true);
        show();
        update();
    }

    misliDir->currentNoteFile = newNoteFile;
    misliWindow->updateNoteFilesListMenu();
    misliWindow->updateTitle();
    update();
    emit noteFileChanged(newNoteFile);//In principle it should be unused
}

void Canvas::centerEyeOnNote(Note *nt)
{
    noteFile()->eyeX = nt->rect().center().x();
    noteFile()->eyeY = nt->rect().center().y();
    update();
}

void Canvas::recheckYourNoteFile()
{
    MisliDir *misliDir = misliWindow->currentDir();
    if(misliDir==NULL) return;

    if(misliWindow->currentDir()->currentNoteFile==NULL){ //Check the current dir for NFs
        if(!misliDir->noteFiles().isEmpty()){ //If it's not empty set a notefile - the default or there's none - the first
            if(misliDir->defaultNfOnStartup()!=NULL){
                setNoteFile(misliDir->defaultNfOnStartup());
            }else{
                setNoteFile(misliDir->noteFiles()[0]);
            }
        }else{ //If there's no notefile in the dir
            if(misliWindow->misli_dg->firstProgramStart()){ //On the first start - set the default NF (with some help notes)
                QString path = QDir(misliWindow->currentDir()->directoryPath()).filePath("notes.misl");
                QFile ntFile(path);
                QFile::copy(":/other/initial_start_nf_"+misliWindow->misli_dg->language()+".misl",path);
                ntFile.setPermissions(QFile::ReadOwner | QFile::WriteOwner);//in the qrc the file is RO, we need RW
                misliWindow->currentDir()->addNoteFile(path);
            }//Else the "Make new notefile" button is shown and the user will do so
        }
    }else if(misliWindow->currentDir()->currentNoteFile!=misliWindow->currentDir()->currentNoteFile){ //Only if the current dir has changed
        setNoteFile(misliWindow->currentDir()->currentNoteFile);
    }else if(!misliWindow->currentDir()->noteFiles().contains(misliWindow->currentDir()->currentNoteFile)){ //If it's missing => it's deleted
        misliWindow->currentDir()->currentNoteFile = NULL; //So that it doesn't try to disconnect it
        recheckYourNoteFile(); //Auto set the note file
    }else{
        qDebug()<<"[Canvas::recheckYourNoteFile]Well I have no idea what the fuck is going on.";
    }
}
