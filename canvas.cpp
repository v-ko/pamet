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

#include <QInputDialog>

#include "canvas.h"
#include "misli_desktop/misliwindow.h"
#include "notessearch.h"
#include "ui_misliwindow.h"

Canvas::Canvas(MisliWindow *misliWindow_) :
    detailsMenu(tr("Details"),this)
{
    hide();

    //Random
    misliWindow = misliWindow_;
    linkOnControlPointDrag = NULL;
    cpChangeNote = NULL;
    PushLeft = false;
    timedOutMove = false;
    moveOn = false;
    noteResizeOn = false;
    userIsDraggingStuff = false;

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
    setAcceptDrops(true);
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
QPointF Canvas::unproject(QPointF point)
{
    return QPointF(unprojectX(point.x()),unprojectY(point.y()));
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
float Canvas::heightScaleFactor()
{
    return 1000/noteFile()->eyeZ;
}

void Canvas::paintEvent(QPaintEvent*)
{
    if(noteFile()==NULL) return;

    //Init the painter
    QPainter painter;
    QPen pen;
    pen.setCosmetic(true);

    if(!painter.begin((this))){
        qDebug()<<"[Canvas::Canvas]Failed to initialize painter.";
    }
    painter.setPen(pen);
    painter.setRenderHint(QPainter::Antialiasing); //better antialiasing
    painter.setRenderHint(QPainter::TextAntialiasing);
    painter.fillRect(0,0,width(),height(),QColor(255,255,255,255)); //clear background

    //==========Check for some special conditions================
    if(linkingIsOn){ //If we're making a link
        infoLabel->setText(tr("Click on a note to link to it."));
        infoLabel->show();
    }else if(noteFile()==misliWindow->helpNoteFile){
        infoLabel->setText(tr("This is the help note file."));
        infoLabel->show();
        painter.fillRect(0,0,width(),height(),QColor(255,255,240,255)); //clear background
    }else if(moveOn){
        infoLabel->setText(tr("Moving note"));
        infoLabel->show();
    }else if(userIsDraggingStuff){
        if(draggedStuffIsValid){
            painter.fillRect(0,0,width(),height(),QColor(240,255,240,255)); //greenish background
        }else{
            painter.fillRect(0,0,width(),height(),QColor(255,240,240,255)); //redish background
        }
    }else{
        infoLabel->hide();
    }

    //Setup the transformation matrix
    QTransform viewpointTransform;
    viewpointTransform.scale(heightScaleFactor(),heightScaleFactor());
    viewpointTransform.translate(width()/heightScaleFactor()/2 - noteFile()->eyeX,
                height()/heightScaleFactor()/2 - noteFile()->eyeY);
    painter.setTransform(viewpointTransform);
    QRectF windowFrame;
    windowFrame.setSize( QSizeF(width()/heightScaleFactor(), height()/heightScaleFactor()) );
    windowFrame.moveCenter(QPointF(noteFile()->eyeX,noteFile()->eyeY));

    //=============Start painting===========================
    int displayed_notes = 0;
    for(Note* nt: noteFile()->notes){

        QColor circleColor = nt->backgroundColor();
        circleColor.setAlpha(60);//same as BG but transparent

        //Draw the note (only if it's on screen (to avoid lag) )
        if(nt->rect().intersects(windowFrame)){
            displayed_notes++;

            //Check the validity of the address string
            if(nt->type==NoteType::redirecting){
                if(misliWindow->currentDir()->noteFileByName(nt->addressString)==NULL &&
                   nt->textForShortening()!=tr("Missing note file") )
                {
                    nt->setTextForShortening(tr("Missing note file"));
                }
            }

            //Handle autoSize requests
            if(nt->requestAutoSize){
                nt->requestAutoSize = false;
                nt->autoSize(painter);
                noteFile()->save();
            }
            //Draw the actual note
            nt->drawNote(painter);

            //Draw additional lines to help alignment
            if( (moveOn | noteResizeOn) && nt->isSelected_m){

                float x = nt->rect().x();
                float y = nt->rect().y();
                float rectX = nt->rect().right(); //coordinates of the rectangle encapsulating the note
                float rectY = nt->rect().bottom();

                QLineF leftLine(x,y-ALIGNMENT_LINE_LENGTH,x,rectY+ALIGNMENT_LINE_LENGTH);
                QLineF rightLine(rectX,y-ALIGNMENT_LINE_LENGTH,rectX,rectY+ALIGNMENT_LINE_LENGTH);
                QLineF bottomLine(x-ALIGNMENT_LINE_LENGTH,rectY,rectX+ALIGNMENT_LINE_LENGTH,rectY);
                QLineF topLine(x-ALIGNMENT_LINE_LENGTH,y,rectX+ALIGNMENT_LINE_LENGTH,y);

                //Set the color
                pen.setColor(nt->textColor());
                painter.setPen( pen );
                painter.drawLine(leftLine);
                painter.drawLine(rightLine);
                painter.drawLine(bottomLine);
                painter.drawLine(topLine);
            }

            //If it's selected - draw the resize circle
            if(nt->isSelected_m){
                painter.setBrush(circleColor);
                painter.drawEllipse(nt->rect().bottomRight(),RESIZE_CIRCLE_RADIUS,RESIZE_CIRCLE_RADIUS);

                if(linkingIsOn){
                    Link ln(0);
                    ln.line.setPoints(nt->rect().center(), unproject(mousePos()));
                    nt->drawLink(painter, ln);
                }
            }
        }
    } //next note

    //Draw all the links. It's not much compute time and when a note goes offscreen its links should still be visible
    for(Note* nt: noteFile()->notes){
        //Draw links
        for(Link &ln: nt->outlinks){
            nt->drawLink(painter, ln);
        } //next link
    }

    //Show the shadows of stuff that's about to be pasted when ctrl is pressed
    if( ctrlUpdateHack ){
        ctrlUpdateHack = false;
        NoteFile *clipboardNF = misliWindow->clipboardNoteFile;
        float x,y;
        x = mapFromGlobal(cursor().pos()).x(); //get mouse screen coords
        y = mapFromGlobal(cursor().pos()).y();
        unproject(x,y,x,y); //translate them to canvas coords

        clipboardNF->makeCoordsRelativeTo(-x,-y);
        for(Note *nt: clipboardNF->notes){
            pen.setColor(nt->textColor());
            painter.setPen(pen);
            painter.setBrush(Qt::NoBrush);
            painter.drawRect(nt->rect());
        }
        clipboardNF->makeCoordsRelativeTo(x,y);
    }

    //If there's no note on the screen - show the JumpToNearestNoteButton
    if( (displayed_notes==0) && !noteFile()->notes.isEmpty() ) {
        misliWindow->ui->jumpToNearestNotePushButton->show();
    }else{
        misliWindow->ui->jumpToNearestNotePushButton->hide();
    }
}

void Canvas::mousePressEvent(QMouseEvent *event)
{
    handleMousePress(event->button());
}
void Canvas::mouseReleaseEvent(QMouseEvent *event)
{
    handleMouseRelease(event->button());
}
void Canvas::mouseDoubleClickEvent(QMouseEvent *event)
{
    if(noteFile()==NULL) return;

    //Don't accept doubleClick on modifiers, because it ruin a selection
    if( (event->button()==Qt::LeftButton) &&
            !(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ControlModifier) &&
            !(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ShiftModifier) ){
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

    if(PushLeft){
        if(moveOn){
            QPointF realPos( unproject(event->pos()) ), realPosOnPush( unproject(QPointF(XonPush, YonPush))), deltaRealPos, newPos;
            deltaRealPos = realPos - realPosOnPush;

            for(Note *nt: noteFile()->notes){
                if(nt->isSelected()){
                    newPos = nt->posBeforeMove + deltaRealPos;
                    QRectF newRect(nt->rect());
                    newRect.moveTopLeft(newPos);
                    nt->setRect( newRect );

                    for(Link &ln: nt->outlinks){
                        ln.usesControlPoint = false;
                        ln.controlPointIsSet = false;
                    }
                    noteFile()->initLinks();
                }
            }

        }else if(noteResizeOn){

            for(Note *nt:noteFile()->notes){
                if(nt->isSelected_m){

                    float d_x, d_y, realX, realY;
                    unproject(event->x(),event->y(),realX,realY);
                    d_x = realX - resizeX;
                    d_y = realY - resizeY;

                    QRectF newRect( nt->rect());
                    newRect.setSize( QSizeF(d_x, d_y) );
                    nt->setRect( newRect );

                    noteFile()->initLinks();
                }
            }

        }else if(linkOnControlPointDrag!=NULL){ //We're changing a control point
            linkOnControlPointDrag->controlPoint = unproject(mousePos());
            linkOnControlPointDrag->isSelected = true;
            linkOnControlPointDrag->controlPointIsChanged = true;
            noteFile()->initNoteLinks(cpChangeNote);
            update();
        }else{ //Else we're moving about the canvas (respectively - changing the camera position)

            float xrel=event->x()-XonPush,yrel=event->y()-YonPush;
            noteFile()->eyeX = EyeXOnPush - xrel*noteFile()->eyeZ/1000; // eyez/1000 is the transform factor practically
            noteFile()->eyeY = EyeYOnPush - yrel*noteFile()->eyeZ/1000;
            update();
        }
    }else if(linkingIsOn){
        update();
    }

    if(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ControlModifier){
        ctrlUpdateHack = true;
        update(); //while showing the shadows of the notes for pasting
    }
}
void Canvas::dragEnterEvent(QDragEnterEvent *event)
{
    //Pretty much if there's items of the types we accept - we acknowledge the drop
    //but if they are invalid - we indicate that. Before the drop - with a redish canvas.
    //And on it - with a specific message
    draggedStuffIsValid = mimeDataIsCompatible(event->mimeData());

    if(event->mimeData()->hasUrls() |
            event->mimeData()->hasImage() |
            event->mimeData()->hasText())
    {
        userIsDraggingStuff = true;
        event->acceptProposedAction();
        update();
    }
}
void Canvas::dragLeaveEvent(QDragLeaveEvent *)
{
    userIsDraggingStuff = false;
    update();
}
void Canvas::dropEvent(QDropEvent *event)
{
    pasteMimeData(event->mimeData());
    userIsDraggingStuff = false;
    update();
}

void Canvas::doubleClick()
{
    Note *nt = getNoteUnderMouse(mousePos().x(),mousePos().y());

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
            newNote->requestAutoSize = true;

        }else if(nt->type==NoteType::webPage){
            QDesktopServices::openUrl(QUrl(nt->addressString, QUrl::TolerantMode));
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
void Canvas::handleMousePress(Qt::MouseButton button)
{
    if(noteFile()==NULL) return;

    Note *noteUnderMouse, *noteForResize;
    Link *linkUnderMouse;
    bool ctrl_is_pressed,shift_is_pressed;

    int x = mousePos().x();
    int y = mousePos().y();

    update();//don't put at the end , return get's called earlier in some cases

    if(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ControlModifier){
        ctrl_is_pressed=true;
    }else ctrl_is_pressed=false;
    if(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ShiftModifier){
        shift_is_pressed=true;
    }else shift_is_pressed=false;

    if (button==Qt::LeftButton) { //on left button

        //----Save of global variables for other functions-----
        XonPush = x;
        YonPush = y;
        PushLeft = true;
        EyeXOnPush = noteFile()->eyeX;
        EyeYOnPush = noteFile()->eyeY;
        timedOutMove = false;

        if (linkingIsOn) { // ------------LINKING ON KEY----------

            noteUnderMouse = getNoteUnderMouse(x,y);
            linkingIsOn = false;
            if(noteUnderMouse!=NULL){
                if( noteFile()->linkSelectedNotesTo(noteUnderMouse)>0 ){
                    noteFile()->save();
                }
            }
            update();
            return;
        }

        // -----------RESIZE---------------
        noteForResize=getNoteClickedForResize(x,y);
        if( !(ctrl_is_pressed | shift_is_pressed) ) { //if neither ctrl or shift are pressed resize only the note under mouse
            noteFile()->clearNoteSelection();
        }
        if (noteForResize!=NULL){
            noteForResize->setSelected(true);
            noteResizeOn=true;
            resizeX=noteForResize->rect().x();
            resizeY=noteForResize->rect().y();
            QCursor::setPos( mapToGlobal( project(noteForResize->rect().bottomRight()).toPoint() ) );
            return;
        }

        //---------DRAG LINK CONTROL POINT---------------
        linkOnControlPointDrag = getControlPointUnderMouse(mousePos().x(),mousePos().y());
        if(linkOnControlPointDrag!=NULL){
            linkOnControlPointDrag->isSelected = true;
            if(!linkOnControlPointDrag->usesControlPoint){
                linkOnControlPointDrag->controlPoint = unproject(mousePos());
            }
        }
        update();

        //----------SELECT------------
        //Clear selection if there are no modifiers
        if( !(ctrl_is_pressed | shift_is_pressed) ) {
            noteFile()->clearNoteSelection();
            noteFile()->clearLinkSelection();
        }

        //Select links
        linkUnderMouse = getLinkUnderMouse(x,y);
        if (linkUnderMouse!=NULL){
            linkUnderMouse->isSelected = true;
        }

        //Select notes
        noteUnderMouse = getNoteUnderMouse(x,y);
        if (noteUnderMouse!=NULL){

            if(noteUnderMouse->isSelected()){
                noteUnderMouse->setSelected(false);
            }else {
                if(noteUnderMouse->type == NoteType::textFile){
                    noteUnderMouse->checkTextForFileDefinition();
                }
                noteUnderMouse->setSelected(true);
            }

            distanceToPrimeNoteX = x-noteUnderMouse->rect().x();
            distanceToPrimeNoteY = y-noteUnderMouse->rect().y();

            if(shift_is_pressed){
                //Select all notes this one links to
                noteUnderMouse->setSelected(true);
                for(Link ln: noteUnderMouse->outlinks){
                    noteFile()->getNoteById(ln.id)->setSelected(true);
                }
            }

            timedOutMove = true;
            move_func_timeout->start(MOVE_FUNC_TIMEOUT);
        }



    }else if(button==Qt::RightButton){

        noteUnderMouse = getNoteUnderMouse(x,y);

        contextMenu->clear();

        if(noteUnderMouse!=NULL){
            noteUnderMouse->setSelected(true);

            contextMenu->addAction(misliWindow->ui->actionEdit_note);
            contextMenu->addAction(misliWindow->ui->actionDelete_selected);
            contextMenu->addAction(misliWindow->ui->actionMake_link);
            contextMenu->addSeparator();
            detailsMenu.clear();
            detailsMenu.addAction("Date created:"+noteUnderMouse->timeMade.toString("d.M.yyyy H:m:s"));
            detailsMenu.addAction("Date modified:"+noteUnderMouse->timeModified.toString("d.M.yyyy H:m:s"));
            contextMenu->addMenu(&detailsMenu);
        }else{
            contextMenu->addAction(misliWindow->ui->actionNew_note);
        }
        contextMenu->addMenu(misliWindow->ui->menuSwitch_to_another_note_file);
        contextMenu->addSeparator();
        contextMenu->addAction(misliWindow->ui->actionCopy);
        contextMenu->addAction(misliWindow->ui->actionPaste);
        contextMenu->addAction(misliWindow->ui->actionCreate_note_from_the_clipboard_text);

        contextMenu->popup(cursor().pos());
    }
}
void Canvas::handleMouseRelease(Qt::MouseButton button)
{
    if(noteFile()==NULL) return;

    if(button==Qt::LeftButton){
        PushLeft = false;

        if(moveOn){
            moveOn = false;
            noteFile()->save(); //saving the new positions
            noteFile()->initLinks();
        }else if(noteResizeOn){
            noteResizeOn = false;
            noteFile()->save(); //save the new size
            noteFile()->initLinks();
        }else if(linkOnControlPointDrag!=NULL){
            linkOnControlPointDrag = NULL;
            noteFile()->save(); //save the new controlPoint position
            update();
        }
    }
}

Note *Canvas::getNoteUnderMouse(int mouseX, int mouseY)
{
    for(Note *nt: noteFile()->notes){
        if( project(nt->rect()).contains(QPointF(mouseX,mouseY))){
            return nt;
        }
    }

return NULL;
}
Note *Canvas::getNoteClickedForResize(int mouseX , int mouseY)
{
    for(Note *nt: noteFile()->notes){
        if(QLineF(unproject(QPointF(mouseX,mouseY)),nt->rect().bottomRight()).length()<=RESIZE_CIRCLE_RADIUS){
        //if(dottodot(unprojectX(mouseX),unprojectY(mouseY),nt->rect().right(),nt->rect().bottom())<=RESIZE_CIRCLE_RADIUS){
            return nt;
        }
    }
    return NULL;
}
Link *Canvas::getLinkUnderMouse(int mouseX,int mouseY) //returns one link (not necesserily the top one) onder the mouse
{
    QRectF mouseSelectionRect(0,0,CLICK_RADIUS,CLICK_RADIUS); //not perfect, but works
    mouseSelectionRect.moveCenter(unproject(QPointF(mouseX,mouseY)));

    for(Note *nt: noteFile()->notes){
        for(Link &ln: nt->outlinks){
            if(ln.path.translated(ln.line.p1()).intersects(mouseSelectionRect)){
                return &ln;
            }
        }
    }
    return NULL;
}
Link *Canvas::getControlPointUnderMouse(int x, int y)
{
    for(Note *nt: noteFile()->notes){
        for(Link &ln: nt->outlinks){
            if(ln.usesControlPoint){
                if(QLineF(unproject(QPointF(x,y)),ln.controlPoint).length()<=RESIZE_CIRCLE_RADIUS){
                    cpChangeNote = nt;
                    return &ln;
                }
            }else{
                if(QLineF(unproject(QPointF(x,y)),ln.middleOfTheLine()).length()<=RESIZE_CIRCLE_RADIUS){
                    cpChangeNote = nt;
                    return &ln;
                }
            }
        }
    }
    cpChangeNote = NULL;
    return NULL;
}

void Canvas::startMove(){ //if the mouse hasn't moved and time_out_move is not off the move flag is set to true

    int x=mousePos().x();
    int y=mousePos().y();

    float dist = dottodot(XonPush,YonPush,x,y);

    if( (timedOutMove && PushLeft ) && ( dist<MOVE_FUNC_TOLERANCE ) ){

        getNoteUnderMouse(x,y)->setSelected(true); //to pickup a selected note with control pressed (not to deselect it)

        //Store all the coordinates before the move
        for(Note *nt: misliWindow->currentDir()->currentNoteFile->notes){
            if(nt->isSelected()) nt->posBeforeMove = nt->rect().topLeft();
        }
        moveOn = true;
        update();
    }

    timedOutMove = false;
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
    x=mousePos().x(); //get mouse screen coords
    y=mousePos().y();
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
    Note *nearest_note = NULL;
    float best_result = 0, result,x_unprojected, y_unprojected;

    unproject(mousePos().x(),mousePos().y(),x_unprojected,y_unprojected);

    int iter=0;
    for(Note *nt: noteFile()->notes){
        result = QLineF(unproject(mousePos()), nt->rect().topLeft()).length();

        if( (result<best_result) | (iter==0) ){
            nearest_note = nt;
            best_result = result;
        }
        iter++;
    }

    if(iter>0){
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
void Canvas::setNoteFile(NoteFile *newNoteFile) //This function has to not care what happens to the last NF
                                                //Else we need no know the misliDir of the last one
{
    MisliDir *misliDir = misliWindow->currentDir();

    if(misliDir==NULL){
        if(newNoteFile!=NULL){
            qDebug()<<"[Canvas::setNoteFile]Trying to set a notefile while currentDir is NULL.";
            return;
        }else{ //Just update the UI - that's all that's needed in that case
            hide();
            misliWindow->ui->makeNoteFilePushButton->show();
            misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(false);
            misliWindow->updateNoteFilesListMenu();
            misliWindow->updateTitle();
            update();
            return;
        }
    }

    disconnect(visualChangeConnection);

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
            if(misliWindow->misliDesktopGUI->firstProgramStart()){
                //Copy the first preset notefile
                QString path = QDir(misliWindow->currentDir()->directoryPath()).filePath("notes.misl");
                QFile ntFile(path);
                QFile::copy(":/other/initial_start_nf_"+misliWindow->misliDesktopGUI->language()+".misl",path);
                ntFile.setPermissions(QFile::ReadOwner | QFile::WriteOwner);//in the qrc the file is RO, we need RW
                misliWindow->currentDir()->addNoteFile(path);

                //Copy the second preset notefile
                path = QDir(misliWindow->currentDir()->directoryPath()).filePath("notes2.misl");
                ntFile.setFileName(path);
                QFile::copy(":/other/notes2.misl",path);
                ntFile.setPermissions(QFile::ReadOwner | QFile::WriteOwner);//in the qrc the file is RO, we need RW
                misliWindow->currentDir()->addNoteFile(path);

                misliWindow->misliDesktopGUI->setFirstProgramStart(false);
                return;
            }else{//Else the "Make new notefile" button is shown and the user will do so
                hide();
                misliWindow->ui->jumpToNearestNotePushButton->hide();
                misliWindow->ui->makeNoteFilePushButton->show();
                misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(false);
            }
        }
    }else if(!misliWindow->currentDir()->noteFiles().contains(newNoteFile) && newNoteFile!=misliWindow->helpNoteFile){
        qDebug()<<"[Canvas::setNoteFile]Trying to set a notefile that does not belong to the current misli dir.";
        return;
    }else{
        visualChangeConnection = connect(newNoteFile,SIGNAL(visualChange()),this,SLOT(update()));

        misliWindow->ui->makeNoteFilePushButton->hide();
        misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(true);
        show();
        update();
    }

    if( newNoteFile != misliDir->currentNoteFile ){
        misliDir->lastNoteFile = misliDir->currentNoteFile;
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

bool Canvas::mimeDataIsCompatible(const QMimeData *mimeData)
{
    if(mimeData->hasUrls()){
        QList<QUrl> urls = mimeData->urls();

        //If there's no valid URLs - draggedStuffIsValid is left false
        for(QUrl url: urls){
            if(url.isLocalFile()){
                if(url.fileName().endsWith(".txt")){
                    return true;
                }else if(!QImage(url.toLocalFile()).isNull()){
                    return true;
                }else{
                    return false;
                }
            }else{
                return true;
            }
        }
        return false;
    }else if(mimeData->hasImage()){
        if(QImage(qvariant_cast<QImage>(mimeData->imageData())).isNull()){
            return false;
        }else{
            return true;
        }
    }else if(mimeData->hasText()){
        return true;
    }else{
        return false;
    }
}
void Canvas::pasteMimeData(const QMimeData *mimeData)
{
    //We'll use the note input mechanism to make the new notes from the dropped items
    misliWindow->edit_w->x_on_new_note=mousePos().x(); //cursor position relative to the gl widget
    misliWindow->edit_w->y_on_new_note=mousePos().y();
    misliWindow->edit_w->edited_note=NULL;

    if(mimeData->hasImage()){
        QString imageName = QInputDialog::getText(this,tr("Give a name to the image"),tr("Enter a name for the image"));
        QImage img = qvariant_cast<QImage>(mimeData->imageData());
        QDir misliDir(misliWindow->currentDir()->directoryPath());

        if(imageName.isEmpty()){
            misliWindow->misliDesktopGUI->showWarningMessage(tr("Can't use an empty name."));
            return;
        }else if(misliDir.entryList().contains(imageName+".png")){
            misliWindow->misliDesktopGUI->showWarningMessage(tr("File name is taken."));
            return;
        }

        imageName = misliDir.filePath(imageName+".png");
        if(!img.save(imageName)){
            misliWindow->misliDesktopGUI->showWarningMessage(tr("Could not save the image (maybe a file with this name already exists? )"));
        }else{
            misliWindow->edit_w->setTextEditText( "define_picture_note:"+imageName );
            misliWindow->edit_w->inputDone();
        }
    }else if(mimeData->hasText()){
        QUrl url(mimeData->text().trimmed(),QUrl::StrictMode);

        if(url.isValid()){
            if(url.toString().isEmpty()){
                qDebug()<<"[Canvas::dropEvent]Empty URL dropped";
            }else if(url.isLocalFile()){
                if(url.fileName().endsWith(".txt")){
                    misliWindow->edit_w->setTextEditText( "define_text_file_note:"+misliWindow->edit_w->maybeToRelativePath(url.toLocalFile()) );
                    misliWindow->edit_w->inputDone();
                }else if(!QImage(url.toLocalFile()).isNull()){
                    misliWindow->edit_w->setTextEditText( "define_picture_note:"+misliWindow->edit_w->maybeToRelativePath(url.toLocalFile()) );
                    misliWindow->edit_w->inputDone();
                }else{
                    misliWindow->misliDesktopGUI->showWarningMessage(tr("Unsupported file dropped:")+url.toLocalFile());
                }
            }else{
                QString pageName = QInputDialog::getText(this,tr("Give a name to the web page"),tr("Enter a name for the web page"));
                misliWindow->edit_w->setTextEditText( "define_web_page_note:\nurl="+url.toString()+"\nname="+pageName );
                misliWindow->edit_w->inputDone();
            }
        }else{
            misliWindow->edit_w->setTextEditText( mimeData->text() );
            misliWindow->edit_w->inputDone();
        }

    }
}

QPointF Canvas::mousePos()
{
    return mapFromGlobal(cursor().pos());
}
