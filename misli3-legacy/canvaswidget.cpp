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
#include <QMessageBox>
#include <QAction>

#include "canvaswidget.h"
#include "misli_desktop/misliwindow.h"
#include "notessearch.h"
#include "ui_misliwindow.h"

CanvasWidget::CanvasWidget(MisliWindow *misliWindow_, NoteFile *nf) :
    detailsMenu(tr("Details"),this)
{
    hide();

    //Random
    misliWindow = misliWindow_;
    linkOnControlPointDrag = nullptr;
    cpChangeNote = nullptr;
    PushLeft = false;
    timedOutMove = false;
    moveOn = false;
    noteResizeOn = false;
    userIsDraggingStuff = false;

    contextMenu = new QMenu(this);

    infoLabel = new QLabel(this);
    infoLabel->setFont(QFont("Helvetica", 15));

    //Setting the timer for the move_func
    move_func_timeout = new QTimer(this);
    move_func_timeout->setSingleShot(1);
    connect(move_func_timeout, SIGNAL(timeout()), this, SLOT(startMove()));

    setMouseTracking(1);
    setFocusPolicy(Qt::ClickFocus);
    setAcceptDrops(true);

    //Prepare per tag filter actions for the context menu
    per_tag_filter_menu.setTitle("Filter per tag (hacky)");
    for(auto tag: misliWindow->misliLibrary()->filter_menu_tags){
        QAction *action = new QAction(tag);
        action->setCheckable(true);
        action->setChecked(true);

        per_tag_filter_menu.addAction(action);
        connect(action, SIGNAL(triggered()), this, SLOT(update));
    }

    // Set notefile
    setNoteFile(nf);
}
CanvasWidget::~CanvasWidget()
{
    delete contextMenu;
    delete infoLabel;
    delete move_func_timeout;
}
QPointF CanvasWidget::project(QPointF point)
{
    return QPointF(projectX(point.x()),projectY(point.y()));
}
QLineF CanvasWidget::project(QLineF line)
{
    return QLineF(project(line.p1()),project(line.p2()));
}
QRectF CanvasWidget::project(QRectF rect)
{
    return QRectF(project(rect.topLeft()),project(rect.bottomRight()));
}
void CanvasWidget::project(double realX, double realY, double &screenX, double &screenY)
{
    screenX = projectX(realX);
    screenY = projectY(realY);
}
void CanvasWidget::unproject(double screenX, double screenY, double &realX, double &realY)
{
    realX = unprojectX(screenX);
    realY = unprojectY(screenY);
}
QPointF CanvasWidget::unproject(QPointF point)
{
    return QPointF(unprojectX(point.x()),unprojectY(point.y()));
}

double CanvasWidget::projectX(double realX)
{
    realX -= noteFile()->eyeX;
    realX = realX/noteFile()->eyeZ; //The heigher we look from - the smaller the note
    realX = realX*1000; //More readable note sizes (and not to break compatability, this section was changed)
    return realX + double(width())/2;
}
double CanvasWidget::projectY(double realY)
{
    realY -= noteFile()->eyeY;
    realY = realY/noteFile()->eyeZ;
    realY = realY*1000;
    return realY + double(height())/2;
}
double CanvasWidget::unprojectX(double screenX)
{
    screenX -= double(width())/2;
    screenX = screenX/1000;
    screenX = screenX*noteFile()->eyeZ;
    return screenX + noteFile()->eyeX;
}
double CanvasWidget::unprojectY(double screenY)
{
    screenY -= double(height())/2;
    screenY = screenY/1000;
    screenY = screenY*noteFile()->eyeZ;
    return screenY + noteFile()->eyeY;
}
double CanvasWidget::heightScaleFactor()
{
    return 1000/noteFile()->eyeZ;
}

void CanvasWidget::paintEvent(QPaintEvent*)
{
    QTime paintStartTime = QTime::currentTime();
    if(noteFile()==nullptr) return;

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

    // Allowed tags
    QStringList allowedTags;
    for(auto action: per_tag_filter_menu.actions()){
        if(!action->isChecked()){
            allowedTags.append(action->text());
        }
    }

    //=============Start painting===========================
    int displayed_notes = 0;
    for(Note* nt: noteFile()->notes){

        QColor circleColor = nt->backgroundColor();
        circleColor.setAlpha(60);//same as BG but transparent

        //Draw the note (only if it's on screen (to avoid lag) )
        if(!nt->rect().intersects(windowFrame)){
            continue;
        }

        bool hideNote = false;
        for(auto tag: nt->tags){
            if(allowedTags.indexOf(tag) != -1){
                hideNote = true;
            }
        }
        if(hideNote) continue;

        displayed_notes++;

        //Check the validity of the address string
        if(nt->type == NoteType::redirecting){
            if(misliWindow->misliLibrary()->noteFileByName(nt->addressString) == nullptr &&
               nt->textForShortening!=tr("Missing note file") )
            {
                nt->textForShortening = tr("Missing note file");
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

        //Wash out some notes to visualize tags if tags view is activated
        if(misliWindow->ui->actionToggle_tags_view->isChecked()){
            if(!nt->tags.contains(misliWindow->ui->tagTextLineEdit->text())){
                painter.fillRect(nt->rect(), QBrush(QColor(255,255,255,128), Qt::SolidPattern));
            }
        }

        //Draw additional lines to help alignment
        if( (moveOn | noteResizeOn) && nt->isSelected_m){

            double x = nt->rect().x();
            double y = nt->rect().y();
            double rectX = nt->rect().right(); //coordinates of the rectangle encapsulating the note
            double rectY = nt->rect().bottom();

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
    } //next note

    //Draw all the links. It's not much compute time and when a note goes offscreen its links should still be visible
    for(Note* nt: noteFile()->notes){
        //Draw links
        for(Link &ln: nt->outlinks){
            nt->drawLink(painter, ln);
        } //next link
    }

    //Show the shadows of stuff that's about to be pasted when ctrl is pressed
    if( misliWindow->misliDesktopGUI->queryKeyboardModifiers() & Qt::ControlModifier ){
        ctrlUpdateHack = false;
        NoteFile *clipboardNF = misliWindow->clipboardNoteFile;
        double x,y;
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

    qDebug() << "Painter latency: " << QTime::currentTime().msecsTo( paintStartTime);
}

void CanvasWidget::mouseDoubleClickEvent(QMouseEvent *event)
{
    if(noteFile()==nullptr) return;

    //Don't accept doubleClick on modifiers, because it ruin a selection
    if( (event->button()==Qt::LeftButton) &&
            !(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ControlModifier) &&
            !(misliWindow->misliDesktopGUI->keyboardModifiers()==Qt::ShiftModifier) ){
        doubleClick();
    }
}
void CanvasWidget::wheelEvent(QWheelEvent *event)
{
    if(noteFile()==nullptr) return;

    int numDegrees = event->delta() / 8;
    int numSteps = numDegrees / 15;

    noteFile()->eyeZ -= MOVE_SPEED * numSteps;
    noteFile()->eyeZ = std::max(1.0, std::min(noteFile()->eyeZ, 1000.0));

    update();
    //glutPostRedisplay(); artefact, thank you for siteseeing
}
void CanvasWidget::mouseMoveEvent(QMouseEvent *event)
{
    if(noteFile() == nullptr) return;

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
                    noteFile()->arrangeLinksGeometry();
                }
            }

        }else if(noteResizeOn){

            for(Note *nt:noteFile()->notes){
                if(nt->isSelected_m){

                    double d_x, d_y, realX, realY;
                    unproject(event->x(),event->y(),realX,realY);
                    d_x = realX - resizeX;
                    d_y = realY - resizeY;

                    QRectF newRect( nt->rect());
                    newRect.setSize( QSizeF(d_x, d_y) );
                    nt->setRect( newRect );

                    noteFile()->arrangeLinksGeometry();
                }
            }

        }else if(linkOnControlPointDrag!=nullptr){ //We're changing a control point
            linkOnControlPointDrag->controlPoint = unproject(mousePos());
            linkOnControlPointDrag->isSelected = true;
            linkOnControlPointDrag->controlPointIsChanged = true;
            noteFile()->arrangeLinksGeometry(cpChangeNote);
            update();
        }else{ //Else we're moving about the canvas (respectively - changing the camera position)

            double xrel=event->x()-XonPush,yrel=event->y()-YonPush;
            noteFile()->eyeX = EyeXOnPush - xrel*noteFile()->eyeZ/1000; // eyez/1000 is the transform factor practically
            noteFile()->eyeY = EyeYOnPush - yrel*noteFile()->eyeZ/1000;
            update();
        }
    }else if(linkingIsOn){
        update();
    }

    if(misliWindow->misliDesktopGUI->keyboardModifiers() == Qt::ControlModifier){
        ctrlUpdateHack = true;
        update(); //while showing the shadows of the notes for pasting
    }
}
void CanvasWidget::dragEnterEvent(QDragEnterEvent *event)
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
void CanvasWidget::dragLeaveEvent(QDragLeaveEvent *)
{
    userIsDraggingStuff = false;
    update();
}
void CanvasWidget::dropEvent(QDropEvent *event)
{
    pasteMimeData(event->mimeData());
    userIsDraggingStuff = false;
    update();
}

void CanvasWidget::doubleClick()
{
    Note *nt = getNoteUnderMouse(mousePos().x(),mousePos().y());

    if(nt!=nullptr){ //if we've clicked on a note
        if(nt->type == NoteType::redirecting){ //if it's a valid redirecting note

            if(misliWindow->misliLibrary()->noteFileByName(nt->addressString)!=nullptr)
            setNoteFile(misliWindow->misliLibrary()->noteFileByName(nt->addressString));

        }else if(nt->type == NoteType::textFile){

            QDesktopServices::openUrl(QUrl("file://"+nt->addressString, QUrl::TolerantMode));

        }else if(nt->type == NoteType::systemCall){

            QProcess process;

            //Run the command and get the output
            process.setWorkingDirectory(library()->folderPath);
            process.start(nt->addressString);
            process.waitForFinished(-1);
            QByteArray out = process.readAllStandardOutput();
            QByteArray err = process.readAllStandardError();
            QString cwd = QDir::currentPath();
            if(!out.isEmpty()){
                //Put the feedback in a note below the command
                Note *newNote = new Note(noteFile()->getNewId(), QString(out + err));
                newNote->setRect(QRectF(nt->rect().x(), nt->rect().bottom() + 1, 1, 1));
                newNote->timeMade = QDateTime::currentDateTime();
                newNote->timeModified = QDateTime::currentDateTime();
                newNote->textColor_m = nt->textColor();
                newNote->backgroundColor_m = nt->backgroundColor();
                newNote->requestAutoSize = true;
                noteFile()->addNote(newNote);
            }

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
void CanvasWidget::handleMousePress(Qt::MouseButton button)
{
    if(noteFile()==nullptr) return;

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
            if(noteUnderMouse!=nullptr){
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
        if (noteForResize!=nullptr){
            noteForResize->setSelected(true);
            noteResizeOn=true;
            resizeX=noteForResize->rect().x();
            resizeY=noteForResize->rect().y();
            QCursor::setPos( mapToGlobal( project(noteForResize->rect().bottomRight()).toPoint() ) );
            return;
        }

        //---------DRAG LINK CONTROL POINT---------------
        linkOnControlPointDrag = getControlPointUnderMouse(mousePos().x(),mousePos().y());
        if(linkOnControlPointDrag!=nullptr){
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
        if (linkUnderMouse!=nullptr){
            linkUnderMouse->isSelected = true;
        }

        //Select notes
        noteUnderMouse = getNoteUnderMouse(x,y);
        if (noteUnderMouse!=nullptr){

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

        if(noteUnderMouse!=nullptr){
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
        contextMenu->addMenu(&per_tag_filter_menu);

        contextMenu->popup(cursor().pos());
    }
}
void CanvasWidget::handleMouseRelease(Qt::MouseButton button)
{
    if(noteFile()==nullptr) return;

    if(button==Qt::LeftButton){
        PushLeft = false;

        if(moveOn){
            moveOn = false;
            noteFile()->save(); //saving the new positions
            noteFile()->arrangeLinksGeometry();
        }else if(noteResizeOn){
            noteResizeOn = false;
            noteFile()->save(); //save the new size
            noteFile()->arrangeLinksGeometry();
        }else if(linkOnControlPointDrag!=nullptr){
            linkOnControlPointDrag = nullptr;
            noteFile()->save(); //save the new controlPoint position
            update();
        }
    }else if(button==Qt::MiddleButton){
        Note *nt = getNoteUnderMouse(mousePos().x(), mousePos().y());
        if( nt == nullptr ){
            return;
        }

        if(nt->type == NoteType::redirecting){
            NoteFile *nfUnderMouse = misliWindow->misliLibrary()->noteFileByName(nt->addressString);

            if(nfUnderMouse != nullptr){
                misliWindow->openNoteFileInNewTab(nfUnderMouse);
            }
        }
    }
}

Note *CanvasWidget::getNoteUnderMouse(int mouseX, int mouseY)
{
    for(Note *nt: noteFile()->notes){
        if( project(nt->rect()).contains(QPointF(mouseX,mouseY))){
            return nt;
        }
    }

return nullptr;
}
Note *CanvasWidget::getNoteClickedForResize(int mouseX , int mouseY)
{
    for(Note *nt: noteFile()->notes){
        if(QLineF(unproject(QPointF(mouseX,mouseY)),nt->rect().bottomRight()).length()<=RESIZE_CIRCLE_RADIUS){
        //if(dottodot(unprojectX(mouseX),unprojectY(mouseY),nt->rect().right(),nt->rect().bottom())<=RESIZE_CIRCLE_RADIUS){
            return nt;
        }
    }
    return nullptr;
}
Link *CanvasWidget::getLinkUnderMouse(int mouseX,int mouseY) //returns one link (not necesserily the top one) onder the mouse
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
    return nullptr;
}
Link *CanvasWidget::getControlPointUnderMouse(int x, int y)
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
    cpChangeNote = nullptr;
    return nullptr;
}

void CanvasWidget::startMove(){ //if the mouse hasn't moved and time_out_move is not off the move flag is set to true

    qreal x = mousePos().x();
    qreal y = mousePos().y();

    qreal dist = QLineF(XonPush, YonPush, x, y).length();

    if( (timedOutMove && PushLeft ) && ( dist<MOVE_FUNC_TOLERANCE ) ){

        getNoteUnderMouse(x, y)->setSelected(true); //to pickup a selected note with control pressed (not to deselect it)

        //Store all the coordinates before the move
        for(Note *nt: currentNoteFile->notes){
            if(nt->isSelected()) nt->posBeforeMove = nt->rect().topLeft();
        }
        moveOn = true;
        update();
    }

    timedOutMove = false;
}

QString CanvasWidget::copySelectedNotes(NoteFile *sourceNotefile, NoteFile *targetNoteFile)
{
    QString clipboardText;

    //Copy selected notes (only the info that would be in the file)
    for(Note *nt_in_source: sourceNotefile->notes){
        if(nt_in_source->isSelected()){
            Note *nt_in_target = targetNoteFile->cloneNote(nt_in_source);
            //Add the links
            nt_in_target->outlinks = nt_in_source->outlinks;

            //Add the note text to the regular clipboard
            clipboardText += nt_in_source->text_m;
            clipboardText += "\n\n"; //leave space before the next (gets trimmed in the end)
        }
    }

    return clipboardText;
}

void CanvasWidget::paste()
{
    NoteFile *clipboardNF = misliWindow->clipboardNoteFile;
    int old_id;

    clipboardNF->makeAllIDsNegative();

    //Make coordinates relative to the mouse
    double x = mousePos().x(); //get mouse screen coords
    double y = mousePos().y();
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
    noteFile()->arrangeLinksGeometry();

    clipboardNF->makeAllIDsNegative(); //restore ids to positive in the clipboard
    noteFile()->save();
}

void CanvasWidget::jumpToNearestNote()
{
    Note *nearest_note = nullptr;
    double best_result = 0, result,x_unprojected, y_unprojected;

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

NoteFile* CanvasWidget::noteFile()
{
    return currentNoteFile;
}
void CanvasWidget::setNoteFile(NoteFile *newNoteFile) //This function has to not care what happens to the last NF
                                                //Else we need no know the misliDir of the last one
{
    if( newNoteFile == currentNoteFile ){
        return;
    }

    disconnect(visualChangeConnection);

    if(newNoteFile == nullptr){

        if(!library()->noteFiles().isEmpty()){ // If the library is NOT empty

            if(library()->defaultNoteFile() != nullptr){
                setNoteFile(library()->defaultNoteFile());
                return;

            }else{
                setNoteFile(library()->noteFiles()[0]);
                return;
            }

        }else{ //If the library IS empty
            misliWindow->ui->jumpToNearestNotePushButton->hide();
            misliWindow->ui->makeNoteFilePushButton->show();
            misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(false);
            misliWindow->updateNoteFilesListMenu();
            misliWindow->updateTitle();
            hide();
        }

    }else{ //If the newNoteFile is NOT NULL
        visualChangeConnection = connect(newNoteFile, SIGNAL(visualChange()), this, SLOT(update()));

        misliWindow->ui->makeNoteFilePushButton->hide();
        misliWindow->ui->menuSwitch_to_another_note_file->setEnabled(true);
        show();
    }

    lastNoteFile = currentNoteFile;
    currentNoteFile = newNoteFile;
    misliWindow->updateNoteFilesListMenu();
    misliWindow->updateTitle();

    int myIndex = misliWindow->ui->tabWidget->indexOf(this);
    misliWindow->ui->tabWidget->setTabText(myIndex, noteFile()->name());

    update();
}

void CanvasWidget::centerEyeOnNote(Note *nt)
{
    noteFile()->eyeX = nt->rect().center().x();
    noteFile()->eyeY = nt->rect().center().y();
    update();
}

bool CanvasWidget::mimeDataIsCompatible(const QMimeData *mimeData)
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
void CanvasWidget::pasteMimeData(const QMimeData *mimeData)
{
    //We'll use the note input mechanism to make the new notes from the dropped items
    misliWindow->edit_w->x_on_new_note=mousePos().x(); //cursor position relative to the gl widget
    misliWindow->edit_w->y_on_new_note=mousePos().y();
    misliWindow->edit_w->edited_note=nullptr;

    if(mimeData->hasImage()){
        QString imageName = QInputDialog::getText(this,tr("Give a name to the image"),tr("Enter a name for the image"));
        QImage img = qvariant_cast<QImage>(mimeData->imageData());
        QDir misliDir(misliWindow->misliLibrary()->folderPath);

        if(imageName.isEmpty()){
            QMessageBox::warning(this, "Warning", tr("Can't use an empty name."));
            return;
        }else if(misliDir.entryList().contains(imageName+".png")){
            QMessageBox::warning(this, "Warning", tr("File name is taken."));
            return;
        }

        imageName = misliDir.filePath(imageName+".png");
        if(!img.save(imageName)){
            QMessageBox::warning(this, "Warning", tr("Could not save the image (maybe a file with this name already exists? )"));
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
                    QMessageBox::warning(this, "Warning", tr("Unsupported file dropped:")+url.toLocalFile());
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

QPointF CanvasWidget::mousePos()
{
    return mapFromGlobal(cursor().pos());
}

//void CanvasWidget::setCurrentDir(Library * newDir)
//{
//    if(currentDir_m == newDir && newDir != nullptr) return;

//    disconnect(nfChangedConnecton);
//    currentDir_m = newDir;

//    if(newDir != nullptr){
//        nfChangedConnecton = connect(newDir,&Library::noteFilesChanged,[&] {
//            setNoteFile(currentNoteFile);
//        });
//        misliWindow->ui->addMisliDirPushButton->hide();
//        misliWindow->ui->makeNoteFilePushButton->setEnabled(true);

//        setNoteFile(currentNoteFile);
//        misliWindow->notes_search->findByText(misliWindow->ui->searchLineEdit->text());
//    }else{
//        if(misliWindow->misliInstance()->misliDirs().isEmpty()){//If there are no dirs
//            misliWindow->misliInstance()->addDir(QStandardPaths::writableLocation(QStandardPaths::DataLocation));
//            return;
//        }else{ //Else just switch to the last
//            setCurrentDir(misliWindow->misliInstance()->misliDirs().last());
//            return;
//        }
//    }

//    misliWindow->updateDirListMenu();
//}
