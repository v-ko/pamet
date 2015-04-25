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
    saveWithRequest=false;

    //Clear the variables
    lastNoteId=0;
    isDisplayedFirstOnStartup=0;
    eyeX=0;
    eyeY=0;
    eyeZ=INITIAL_EYE_Z;

    isReadable=true;
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
    for(Note *nt:notes) delete nt;
    notes.clear();
    comment.clear();

    //Open the file
    if(!ntFile.open(QIODevice::ReadOnly)){
        qDebug()<<"Error opening notefile: "<<filePath_m;
        return -2;
    }
    //Check for abnormally large files
    if(ntFile.size()>10000000){
        qDebug()<<"Note file "<<name()<<" is more than 10MB.Skipping.";
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
            isDisplayedFirstOnStartup=true;
            continue;
        }
    }

    //Extract the groups(notes)
    if(q_get_groups(fileString,note_ids,noteIniStrings)!=1){d("error when extracting the groups");exit(43);}

    //Create the notes
    for(int i=0;i<noteIniStrings.size();i++){ //get the notes
        loadNote(new Note(note_ids[i].toInt(),noteIniStrings[i]));
    }

    findFreeIds();
    initLinks();

    return 0;
}
void NoteFile::initLinks()  //init all the links in the note_file notes
{
    for(Note *nt: notes) initNoteLinks(nt);
}

void NoteFile::virtualSave()
{
    qDebug()<<"NF("<<name()<<") Virtual save.";
    QString iniString;
    QTextStream iniStringStream(&iniString,QIODevice::ReadWrite);

    //Adding the comments
    for(unsigned int c=0;c<comment.size();c++) iniStringStream<<comment[c]<<'\n';

    //The flag for displaying first on startup
    if(isDisplayedFirstOnStartup) iniStringStream<<"is_displayed_first_on_startup"<<'\n';

    //Adding the notes
    for(Note *nt: notes) iniStringStream<<nt->propertiesInIniString();

    history.push_back(iniString);
    if(history.size()>MAX_UNDO_STEPS){ //Avoid a memory leak by having max undo steps
        history.pop_front();
    }
}
void NoteFile::hardSave()
{
    if(saveWithRequest){
        emit requestingSave(this);
        return;
    }else{
        QFile ntFile(filePath_m);
        ntFile.open(QIODevice::WriteOnly);
        ntFile.write(history.back().toUtf8());
        ntFile.close();
    }
    qDebug()<<"NF("<<name()<<") Hard save.";
}
void NoteFile::save()
{
    virtualSave();
    hardSave();
}
bool NoteFile::undo()
{
    if(history.size()>=2){
        history.pop_back(); //pop the current version
        hardSave();

        init();
        return true;
    }else{
        return false;
    }
}
void NoteFile::findFreeIds()
{
    freeId.clear();
    for(int i=1;i<lastNoteId;i++){ //for all ids to the last (exclude zero to avoid problems when negative ids are used)
        if(getNoteById(i)==NULL){ //if there's no note on it
            freeId.push_back(i); //add the id to the list
        }
    }
}

Note* NoteFile::addNote(Note* nt)
{
    loadNote(nt);
    save();
    emit visualChange();
    return nt;
}
Note* NoteFile::loadNote(Note *nt)
{
    //A check for the free ids system
    if(nt->id>lastNoteId){lastNoteId=nt->id;}

    if(!bufferImages) nt->bufferImage=false;
    else nt->bufferImage=true;

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
    Note * nt2 = new Note(nt->id,nt->text_m,nt->rect(),nt->fontSize(),nt->timeMade,nt->timeModified,nt->textColor(),nt->backgroundColor());
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
            if(linkIter.next().selected){
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
        for(Link &ln:nt->outlinks) ln.selected = false;
    }
}
void NoteFile::makeCoordsRelativeTo(double x,double y)
{
    for(Note *nt: notes){
        nt->rect().moveLeft(nt->rect().x()-x);
        nt->rect().moveTop(nt->rect().y()-y);
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
    int idd;

    if(freeId.size()!=0){
        idd =freeId.front();
        freeId.erase(freeId.begin());
    }else {
        lastNoteId++;
        idd=lastNoteId;
    }
    return idd;
}
void NoteFile::linkSelectedNotesTo(Note *nt)
{
    for(Note *nt2: notes){ //za vseki note ot current
        if( nt2->isSelected_m && ( nt2->id != nt->id ) ){ //ako e selectiran
            nt2->addLink(nt->id);
        }
    }
}
void NoteFile::initNoteLinks(Note *nt) //smqta koordinatite
{
    checkForInvalidLinks(nt);

    for(Link &ln: nt->outlinks){
        //---------Smqtane na koordinatite za link-a---------------
        Note *target_note=getNoteById(ln.id);
        QRectF note1 = nt->rect(),note2 = target_note->rect();

        //Setup the rectangles to check if they intersect
        note1.moveTop(0);
        note2.moveTop(0);
        note1.setHeight(1);
        note2.setHeight(1);

        if(note1.intersects(note2)){ //If the notes are one above another
            //Check which one is above the other
            if(nt->rect().center().y() > target_note->rect().center().y()){ //Note1 is below
                ln.line.setLine(nt->rect().center().x(),
                                nt->rect().y(),
                                target_note->rect().center().x(),
                                target_note->rect().bottom());
            }else{//Note1 is above
                ln.line.setLine(nt->rect().center().x(),
                                nt->rect().bottom(),
                                target_note->rect().center().x(),
                                target_note->rect().y());
            }
        }else if(note1.right()<note2.x()){ //If the second note is on the right
            ln.line.setLine(nt->rect().right(),
                            nt->rect().center().y(),
                            target_note->rect().left(),
                            target_note->rect().center().y());
        }else{ //If the second note is on the left
            ln.line.setLine(nt->rect().left(),
                            nt->rect().center().y(),
                            target_note->rect().right(),
                            target_note->rect().center().y());
        }
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
