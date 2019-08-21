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

#include <fstream>
#include <QString>
#include <QDesktopWidget>
#include <QDebug>

#include "petko10.h"
#include "note.h"
#include "notefile.h"
#include "common.h"
#include "misliinstance.h"
#include "misli_desktop/misliwindow.h"
#include "misli_desktop/mislidesktopgui.h"

NoteFile::NoteFile()
{
    saveWithRequest = false;
    keepHistoryViaGit = false;
    indexedForSearch = false;

    //Clear the variables
    lastNoteId = 0;
    isDisplayedFirstOnStartup = 0;
    eyeX = 0;
    eyeY = 0;
    eyeZ = INITIAL_EYE_Z;

    isReadable=true;

    connect(this, &NoteFile::noteTextChanged, [=](){
       indexedForSearch = false;
    });
}
NoteFile::~NoteFile()
{
    for(Note* nt:notes) delete nt;
}

QString NoteFile::filePath()
{
    return filePath_m;
}

QString NoteFile::name()
{
    QString name_ = QFileInfo(filePath_m).fileName();
    name_.chop(5);
    return name_;
}

int NoteFile::init()   //returns negative on errors
{
    QFile ntFile(filePath_m);
    QString fileString;
    QStringList lines,noteIniStrings,note_ids;

    //Clear stuff
    lastNoteId=0;
    for(Note *nt: notes) delete nt;
    notes.clear();
    comment.clear();

    //Open the file
    if(!ntFile.open(QIODevice::ReadOnly)){
        qDebug()<<"[NoteFile::init]Error opening notefile: "<<filePath_m;
        return -2;
    }
    //Check for abnormally large files
    if(ntFile.size()>10000000){
        qDebug()<<"[NoteFile::init]Note file "<<name()<<" is more than 10MB.Skipping.";
        return -3;
    }
    //Get the data into a string
    fileString=fileString.fromUtf8(ntFile.readAll().data());
    ntFile.close();

    //Clear the windows standart junk
    fileString = fileString.replace("\r","");
    //Get the lines in separate strings
    lines = fileString.split(QString("\n"),QString::SkipEmptyParts);

    //Get the comments and tags
    for(QString line: lines){ //for every line of text
        if(line.startsWith("#")) comment.push_back(line);
        if(line.startsWith("is_displayed_first_on_startup")){
            isDisplayedFirstOnStartup = true;
            continue;
        }
        if(line.startsWith("is_a_timeline_note_file")){
            isTimelineNoteFile = true;
            continue;
        }
    }

    //Extract the groups(notes)
    if(q_get_groups(fileString,note_ids,noteIniStrings)!=1){d("error when extracting the groups");exit(43);}

    //Create the notes
    for(int i=0;i<noteIniStrings.size();i++){ //get the notes
        loadNote(new Note(note_ids[i].toInt(),noteIniStrings[i]));
    }

    initLinks();

    return 0;
}
void NoteFile::initLinks()  //init all the links in the note_file notes
{
    for(Note *nt: notes) initNoteLinks(nt);
}

void NoteFile::virtualSave()
{
    QString iniString;
    QTextStream iniStringStream(&iniString,QIODevice::ReadWrite);

    //Adding the comments
    for(unsigned int c=0;c<comment.size();c++) iniStringStream<<comment[c]<<'\n';

    //The flag for displaying first on startup
    if(isDisplayedFirstOnStartup) iniStringStream<<"is_displayed_first_on_startup"<<'\n';

    //Adding the notes
    for(Note *nt: notes) iniStringStream<<nt->propertiesInIniString();

    undoHistory.push_back(iniString);
    redoHistory.clear();

    if(undoHistory.size()>MAX_UNDO_STEPS){ //Avoid a memory leak by having max undo steps
        undoHistory.pop_front();
    }
}
void NoteFile::hardSave()
{
    if(saveWithRequest){
        emit requestingSave(this);
        return;
    }else{
        QFile ntFile(filePath_m);
        if( !ntFile.open(QIODevice::WriteOnly) ){
            qDebug()<<"[NoteFile::hardSave]Failed opening the file.";
        }
        ntFile.write(undoHistory.back().toUtf8());
        ntFile.close();
    }
    qDebug()<<"Note file:"<<name()<<" saved.";
}
void NoteFile::save()
{
    if(filePath_m=="clipboardNoteFile") return;

    virtualSave();
    hardSave();
    //Git commit
    QProcess p;
    if(keepHistoryViaGit){
        p.setWorkingDirectory(QFileInfo(filePath_m).dir().path());
        p.start("git",QStringList()<<"add"<<"-A");
        p.waitForFinished();
        qDebug()<<p.readAll();
        p.start("git",QStringList()<<"commit"<<"-m"<<"'"+QDateTime::currentDateTime().toString("yyyy.MM.dd HH:mm:ss")+"'");
        p.waitForFinished();
        qDebug()<<p.readAll();
        //FIXME handle stuff that might happen, check if git is available in order to avoid littering the log, etc
        //the other stuff is in MisliDir::setDirectoryPath
    }
}
void NoteFile::undo()
{
    if(undoHistory.size()>=2){
        redoHistory.push_front(undoHistory.back());
        undoHistory.pop_back(); //pop the current version
        hardSave();

        init();
    }
}
void NoteFile::redo()
{
    if(redoHistory.size()>=1){
        undoHistory.push_back(redoHistory.front());
        redoHistory.pop_back(); //pop the current version
        hardSave();

        init();
    }
}

void NoteFile::addNote(Note* nt)
{
    loadNote(nt);
    save();
    emit visualChange();
}
Note* NoteFile::loadNote(Note *nt)
{
    //A check for the free ids system
    if(nt->id > lastNoteId){
        lastNoteId = nt->id;
    }

    notes.push_back(nt);

    //Connections
    connect(nt,SIGNAL(propertiesChanged()),this,SLOT(save()));
    connect(nt,SIGNAL(visualChange()),this,SIGNAL(visualChange()));
    connect(nt,SIGNAL(linksChanged()),this,SLOT(initLinks()));
    connect(nt,&Note::textChanged,[=](){
        emit noteTextChanged(this);
    });
    return nt;
}
Note *NoteFile::cloneNote(Note *nt)
{
    Note * nt2 = new Note(nt);
    loadNote(nt2);
    return nt2;
}
void NoteFile::deleteSelected() //deletes all marked selected and returns their number
{
    int deletedItemsCount = 0;
    while(getFirstSelectedNote()!=NULL){ //delete selected notes
        deletedItemsCount++;
        Note *nt = getFirstSelectedNote();
        notes.removeOne(nt);
        delete nt;
    }
    //Remove all selected links
    for(Note *nt: notes){
        QMutableListIterator<Link> linkIter(nt->outlinks);
        while(linkIter.hasNext()){
            if(linkIter.next().isSelected){
                deletedItemsCount++;
                linkIter.remove();
            }
        }
    }
    if(deletedItemsCount!=0){
        initLinks();
        save();
        emit noteTextChanged(this);
        emit visualChange();
    }
}

Note *NoteFile::getFirstSelectedNote() //returns first (in the vector arrangement) selected note
{
    for(Note *nt: notes){
            if(nt->isSelected()){return nt;}
    }
    return NULL;
}
Note *NoteFile::getLowestIdNote()
{
    if(notes.size()==0){return NULL;}

    int lowest_id=notes[0]->id; //we assume the first note
    for(Note *nt: notes){ //for the rest of the notes
        if( nt->id<lowest_id ){
            lowest_id=nt->id;
        }
    }
    return getNoteById(lowest_id);
}
Note *NoteFile::getNoteById(int id) //returns the note with the given id
{
    for(Note *nt: notes){
        if( nt->id==id ){return nt;} //ako id-to syvpada vyrni pointera kym toq note
    }
    return NULL;
}
void NoteFile::selectAllNotes()
{
    for(Note *nt: notes) nt->setSelected(true);
}

void NoteFile::clearNoteSelection()
{
    for(Note *nt: notes) nt->setSelected(false);
}
void NoteFile::clearLinkSelection()
{
    for(Note *nt: notes){
        for(Link &ln:nt->outlinks) ln.isSelected = false;
    }
}
void NoteFile::makeCoordsRelativeTo(double x,double y)
{
    for(Note *nt: notes){
        QRectF tmpRect( QPointF(nt->rect().x() - x, nt->rect().y() - y), nt->rect().size() );
        nt->setRect( tmpRect );

        for(Link &ln: nt->outlinks){
            ln.controlPoint.setX(ln.controlPoint.x()-x);
            ln.controlPoint.setY(ln.controlPoint.y()-y);
        }
    }
}

void NoteFile::makeAllIDsNegative()
{
    for(Note *nt: notes){
        nt->id = -nt->id;
        for(Link &ln: nt->outlinks){
            ln.id= -ln.id;
        }
    }
}

int NoteFile::getNewId()
{
    for(int i=1;i<65535;i++){
        if(getNoteById(i)==NULL){
            return i;
        }
    }
    qDebug()<<"No free note id up to 65535. Either there's a bug or someone's been busy.";
    return 0;
}
int NoteFile::linkSelectedNotesTo(Note *nt)
{
    int linksAdded=0;
    for(Note *nt2: notes){ //za vseki note ot current
        if( nt2->isSelected() ){ //ako e selectiran
            linksAdded += nt2->addLink(nt->id);
        }
    }
    return linksAdded;
}
void NoteFile::initNoteLinks(Note *nt) //smqta koordinatite
{
    checkForInvalidLinks(nt);

    for(Link &ln: nt->outlinks){
        //---------Smqtane na koordinatite za link-a---------------
        Note *target_note = getNoteById(ln.id);

        //Setup the rectangles to check if they intersect
        QRectF note1 = nt->rect(), note2 = target_note->rect();
        note1.moveTop(0);
        note2.moveTop(0);
        note1.setHeight(1);
        note2.setHeight(1);

        //Construct the line as it would be without a control point (stored as autoLine)
        if(note1.intersects(note2)){ //If the notes are one above another
            //Check which one is above the other
            if(nt->rect().center().y() > target_note->rect().center().y()){ //Note1 is below
                ln.autoLine.setLine(nt->rect().center().x(),
                                nt->rect().y(),
                                target_note->rect().center().x(),
                                target_note->rect().bottom());
            }else{//Note1 is above
                ln.autoLine.setLine(nt->rect().center().x(),
                                nt->rect().bottom(),
                                target_note->rect().center().x(),
                                target_note->rect().y());
            }
        }else if(note1.right()<note2.x()){ //If the second note is on the right
            ln.autoLine.setLine(nt->rect().right(),
                            nt->rect().center().y(),
                            target_note->rect().left(),
                            target_note->rect().center().y());
        }else{ //If the second note is on the left
            ln.autoLine.setLine(nt->rect().left(),
                            nt->rect().center().y(),
                            target_note->rect().right(),
                            target_note->rect().center().y());
        }

        //Set the control point if it hasn't been
        if(!ln.controlPointIsSet){
            ln.line = ln.autoLine;
            ln.controlPoint = ln.middleOfTheLine();
            ln.controlPointIsSet = true;
        }

        if(ln.controlPointIsChanged){
            //Check if a control point is needed
            QPainterPath linePath(ln.autoLine.p1());
            linePath.lineTo(ln.autoLine.p2());
            QRectF controlPointRect(0,0,CLICK_RADIUS,CLICK_RADIUS);
            controlPointRect.moveCenter(ln.controlPoint);

            //If the path is almost identicle with the straight line or the control point is in the note
            if( linePath.intersects(controlPointRect) | nt->rect().intersects(controlPointRect) ){
                ln.usesControlPoint = false;
                ln.path = QPainterPath(); //to redraw
            }else{
                ln.usesControlPoint = true;
            }
            ln.controlPointIsChanged = false;
        }

        if(ln.usesControlPoint){
            QPointF controlP = ln.controlPoint;
            QRectF controlRect(0,0,1,1);
            controlRect.moveCenter(controlP);
            controlRect.moveTop(0);

            //Set P1 of the line
            if(note1.intersects(controlRect)){ //If the notes are one above another
                //Check which one is above the other
                if(nt->rect().center().y() > controlP.y()){ //controlRect is above
                    ln.line.setP1(QPointF(nt->rect().center().x(),
                                          nt->rect().y()));
                }else{//controlRect is below
                    ln.line.setP1(QPointF(nt->rect().center().x(),
                                          nt->rect().bottom()));
                }
            }else if(note1.right()<controlRect.x()){ //If the controlRect is on the right
                ln.line.setP1(QPointF(nt->rect().right(),
                                      nt->rect().center().y()));
            }else{ //If the second note is on the left
                ln.line.setP1(QPointF(nt->rect().left(),
                                      nt->rect().center().y()));
            }

            //Set P2 of the line
            if(note2.intersects(controlRect)){ //If the notes are one above another
                //Check which one is above the other
                if(controlP.y() > target_note->rect().center().y()){ //The control point is below note2
                    ln.line.setP2(QPointF(target_note->rect().center().x(),
                                          target_note->rect().bottom()));
                }else{//The control point is above
                    ln.line.setP2(QPointF(target_note->rect().center().x(),
                                          target_note->rect().y()));
                }
            }else if(controlP.x()<note2.x()){ //If the control point is on the left
                ln.line.setP2(QPointF(target_note->rect().left(),
                                target_note->rect().center().y()));
            }else{ //If the control point is on the right
                ln.line.setP2(QPointF(target_note->rect().right(),
                                      target_note->rect().center().y()));
            }
        }else{
            ln.line = ln.autoLine;
        }

        ln.path = QPainterPath(); //clear the path so it's redrawn in canvas::paintEvent

    }//next link



    emit visualChange();
}

void NoteFile::setFilePath(QString newPath)
{
    if(newPath==filePath_m) return;

    if(QFileInfo(newPath).isReadable()){
        isReadable = true;
        filePath_m = newPath;
        init();
    }else{
        qDebug()<<"[NoteFile::setFilePath]File not readable:"<<newPath;
    }
}

void NoteFile::checkForInvalidLinks(Note *nt)
{
    QListIterator<Link> iterator(nt->outlinks);
    bool linksChangedHere = false;

    while(iterator.hasNext()){
        Link ln = iterator.next();
        if(getNoteById(ln.id)==NULL){ //if there's no note with the specified link id
            nt->removeLink(ln.id);
            linksChangedHere = true;
        }
    }
    if(linksChangedHere) save();
}
