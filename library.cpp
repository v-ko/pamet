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

#include <QDebug>

#include "global.h"
#include "library.h"
#include "misli_desktop/misliwindow.h"
#include "misli_desktop/mislidesktopgui.h"

Library::Library(QString storageLocation, bool enableFSWatch)
{
    fsWatchIsEnabled = enableFSWatch;

    //FS-watch stuff
    if(fsWatchIsEnabled){
        fs_watch = new QFileSystemWatcher(this);
        connect(fs_watch,SIGNAL(fileChanged(QString)),this,SLOT(handleChangedFile(QString)) );

        hangingNfCheck = new QTimer;
        connect(hangingNfCheck,SIGNAL(timeout()),this,SLOT(checkForHangingNFs() ));
    }else{
        fs_watch = nullptr;
        hangingNfCheck = nullptr;
    }

    //Connect propery changes
    connect(this,SIGNAL(noteFilesChanged()),this,SLOT(reinitNotesPointingToNotefiles()));

    //Setup
    QDir newDir(storageLocation);

    if(!newDir.exists()){
        qDebug() << "[Library::setDirectoryPath]Directory missing, creating it.";

        if(!newDir.mkdir(storageLocation)){
            qDebug() << "[Library::setDirectoryPath]Failed making directory: " << storageLocation;
            return;
        }
    }

    folderPath = storageLocation;
    loadNoteFiles();
}
Library::~Library()
{
    unloadAllNoteFiles();
    delete fs_watch;
    delete hangingNfCheck;
}
QList<NoteFile*> Library::noteFiles()
{
    return noteFiles_m;
}

void Library::checkForHangingNFs()
{
    int missingNfCount=0;

    for(NoteFile * nf: noteFiles_m){
        if(!nf->isReadable){
            //Try to init
            if( nf->loadFromFilePath() == 0 ){ //File is found and initialized properly
                nf->isReadable = true;
                //qDebug()<<"Adding path to fs_watch: "<<nf->filePath_m;
                fs_watch->addPath(nf->filePath()); //when a file is deleted it gets off the fs_watch and we need to re-add it when a unix-type file save takes place
            }else{
                missingNfCount++;
            }
        }
    }
    if(missingNfCount==0) hangingNfCheck->stop(); //if none are missing - stop checking
}

NoteFile * Library::noteFileByName(QString name)
{
    for(NoteFile *nf: noteFiles_m){
        if(nf->name()==name){
            return nf;
        }
    }
    return nullptr;
}

NoteFile * Library::defaultNoteFile()
{
    if(noteFiles_m.isEmpty()){
        qDebug()<<"[Library::defaultNfOnStartup] No note files.";
        return nullptr;
    }

    for(NoteFile *nf: noteFiles_m){
        if(nf->isDisplayedFirstOnStartup) return nf;
    }

    return noteFiles_m[0];
}

int Library::makeCanvas(QString name)
{
    if(noteFileByName(name) != nullptr){ //Check if such a NF doesn't exist already
        return -1;
    }

    QString filePath = QDir(folderPath).filePath(name + ".json");
    QFile ntFile(filePath);

    if(!ntFile.open(QIODevice::WriteOnly)){ //Creates the NF
        qDebug()<<"Error making new notes file";
        return -1;
    }

    ntFile.close();

    loadNoteFile(filePath);

    return 0;
}

void Library::unloadNoteFile(NoteFile* nf)
{
    if(fsWatchIsEnabled) fs_watch->removePath(nf->filePath());
    noteFiles_m.removeOne(nf);
    delete nf;
    emit noteFilesChanged();
}

void Library::loadNoteFiles()
{
    unloadAllNoteFiles();

    QDir dir(folderPath);

    QStringList nfs_misl = dir.entryList(QStringList()<<"*.misl", QDir::Files);
    QStringList nfs_json = dir.entryList(QStringList()<<"*.json", QDir::Files);

    // First load any .misl (legacy) note files and backup + convert them
    for(QString fileName: nfs_misl){
        //backup
        QString oldPath = dir.absoluteFilePath(fileName);
        QString backupPath = oldPath + ".backup";

        if (QFile::exists(backupPath))
        {
            QFile::remove(backupPath);
        }
        QFile::copy(oldPath, backupPath);

        //load nf
        loadNoteFile(oldPath);
    }

    //Rename all misl to json
    for(NoteFile *nf: noteFiles()){
        QString newName = nf->filePath();
        newName.chop(5);
        newName = newName + ".json";
        renameNoteFile(nf, newName);
    }

    for(QString fileName: nfs_json){
        loadNoteFile(dir.absoluteFilePath(fileName));
    }
}
void Library::reinitNotesPointingToNotefiles()
{
    for(NoteFile *nf: noteFiles_m){
        for(Note *nt: nf->notes){
            if(nt->type==NoteType::redirecting) nt->checkTextForNoteFileLink();
        }
    }
}

void Library::handleChangedFile(QString filePath)
{
    int err=0;

    NoteFile *nf,dummyNF;

    dummyNF.filePath_m = filePath; //Get the name
    nf = noteFileByName(dummyNF.name()); //Locate the nf whith that name

    if(nf==nullptr) return;//avoid segfaults on a wrong name

    if( nf->loadFromFilePath()==0 ){
        nf->isReadable = true;
    }else if(err ==-2){ //most times the file is deleted and then replaced on sync , so we need to check back for it later
        nf->isReadable=false;
        hangingNfCheck->start(700);
    }
    emit noteFilesChanged();
}

void Library::unloadAllNoteFiles()
{
    while(!noteFiles_m.isEmpty()){
        unloadNoteFile(noteFiles_m.first());
    }
}

double Library::defaultEyeZ()
{
    return settings.value("eye_z",QVariant(90)).toDouble();
}
void Library::setDefaultEyeZ(double value)
{
    settings.setValue("eye_z",QVariant(value));
    settings.sync();
}

void Library::loadNoteFile(QString pathToNoteFile)
{
    NoteFile *nf = new NoteFile;

    nf->saveWithRequest = true;
    nf->eyeZ = defaultEyeZ();
    nf->setPathAndLoad(pathToNoteFile);

    //If the file didn't init correctly - don't add it
    if(!nf->isReadable | nf->name().isEmpty() ){
        qDebug()<<"[Library::addNoteFile]Note file is not readable, skipping: " << pathToNoteFile;
        delete nf;
        return;
    }

    noteFiles_m.push_back(nf);
    nf->saveStateToHistory(); //should be only a virtual save for ctrl-z

    if(fsWatchIsEnabled) fs_watch->addPath(nf->filePath());
    connect(nf,SIGNAL(requestingSave(NoteFile*)),this,SLOT(handleSaveRequest(NoteFile*)));

    emit noteFilesChanged();
}

void Library::handleSaveRequest(NoteFile *nf)
{
    nf->saveWithRequest = false;
    if(fsWatchIsEnabled) fs_watch->removePath(nf->filePath());
    nf->saveLastInHistoryToFile();
    if(fsWatchIsEnabled) fs_watch->addPath(nf->filePath());
    nf->saveWithRequest = true;
}

bool Library::renameNoteFile(NoteFile *nf, QString newName)
{
    if(noteFileByName(newName) != nullptr){
        return false;
    }

    QString newFilePath = QDir(folderPath).filePath(newName + ".json");
    QString oldName = nf->name();

    QFile file(nf->filePath());

    if( !file.copy(newFilePath) ){ //Copy to a nf with the new name
        qDebug() << "Error copying " << file.fileName() << " to " << newFilePath;
        return false;
    }
    fs_watch->removePath(nf->filePath());//deal with fs_watch
    nf->filePath_m = newFilePath;
    nf->save();
    nf->setPathAndLoad(nf->filePath());
    file.remove();

    //Now change all the notes that point to this one too
    for(NoteFile *nf2: noteFiles_m){
        for(Note *nt: nf2->notes){
            if(nt->type==NoteType::redirecting){
                if(nt->textForDisplay_m==oldName){
                    nt->changeText("this_note_points_to:" + newName);
                }
            }
        }
    }
    return true;
}
