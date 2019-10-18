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

#include "common.h"
#include "misliinstance.h"
#include "mislidir.h"
#include "misli_desktop/misliwindow.h"
#include "misli_desktop/mislidesktopgui.h"

MisliDir::MisliDir(QString folder_path, bool enableFSWatch)
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
    QDir newDir(folder_path);

    if(!newDir.exists()){
        qDebug() << "[MisliDir::setDirectoryPath]Directory missing, creating it.";

        if(!newDir.mkdir(folder_path)){
            qDebug() << "[MisliDir::setDirectoryPath]Failed making directory: " << folder_path;
            return;
        }
    }

    folderPath = folder_path;
    loadNoteFiles();
}
MisliDir::~MisliDir()
{
    unloadAllNoteFiles();
    delete fs_watch;
    delete hangingNfCheck;
}
QList<NoteFile*> MisliDir::noteFiles()
{
    return noteFiles_m;
}

void MisliDir::checkForHangingNFs()
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

NoteFile * MisliDir::noteFileByName(QString name)
{
    for(NoteFile *nf: noteFiles_m){
        if(nf->name()==name){
            return nf;
        }
    }
    return nullptr;
}

NoteFile * MisliDir::defaultNfOnStartup()
{
    for(NoteFile *nf: noteFiles_m){
        if(nf->isDisplayedFirstOnStartup) return nf;
    }
    return nullptr;
}

int MisliDir::makeNotesFile(QString name)
{
    QFile ntFile;
    QString filePath;

    if(noteFileByName(name)!=nullptr){ //Check if such a NF doesn't exist already
        return -1;
    }

//    if(use_json){
//        name = name + ".json";
//    }else{
//        name = name + ".misl";
//    }

    filePath=QDir(folderPath).filePath(name);

    ntFile.setFileName(filePath);

    if(!ntFile.open(QIODevice::WriteOnly)){ //Creates the NF
        qDebug()<<"Error making new notes file";
        return -1;
    }

    ntFile.close();

    loadNoteFile(filePath);

    return 0;
}

void MisliDir::softDeleteNF(NoteFile* nf)
{
    if(fsWatchIsEnabled) fs_watch->removePath(nf->filePath());
    noteFiles_m.removeOne(nf);
    delete nf;
    emit noteFilesChanged();
}

void MisliDir::loadNoteFiles()
{
    unloadAllNoteFiles();

    QDir dir(folderPath);
    QStringList files;
    if(use_json){

    }else{

    }

    files = dir.entryList(QStringList()<<"*.json", QDir::Files);
    files.append(dir.entryList(QStringList()<<"*.misl", QDir::Files));

    for(QString fileName: files){
        loadNoteFile(dir.absoluteFilePath(fileName));
    }
}
void MisliDir::reinitNotesPointingToNotefiles()
{
    for(NoteFile *nf: noteFiles_m){
        for(Note *nt: nf->notes){
            if(nt->type==NoteType::redirecting) nt->checkTextForNoteFileLink();
        }
    }
}

void MisliDir::handleChangedFile(QString filePath)
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

void MisliDir::unloadAllNoteFiles()
{
    while(!noteFiles_m.isEmpty()){
        softDeleteNF(noteFiles_m.first());
    }
}

void MisliDir::deleteAllNoteFiles()
{
    QDir dir(folderPath);

    for(NoteFile *nf: noteFiles_m){
        if(!dir.remove(nf->filePath())){
            qDebug()<<"[MisliDir::deleteAllNoteFiles]Could not remove notefile"<<nf->name();
            return;
        }
    }
    unloadAllNoteFiles();
}

float MisliDir::defaultEyeZ()
{
    return settings.value("eye_z",QVariant(90)).toFloat();
}
void MisliDir::setDefaultEyeZ(float value)
{
    settings.setValue("eye_z",QVariant(value));
    settings.sync();
}

void MisliDir::loadNoteFile(QString pathToNoteFile)
{
    NoteFile *nf = new NoteFile;

    nf->saveWithRequest = true;
    nf->keepHistoryViaGit = keepHistoryViaGit;
    nf->eyeZ = defaultEyeZ();
    nf->setPathAndLoad(pathToNoteFile);

    //If the file didn't init correctly - don't add it
    if(!nf->isReadable | nf->name().isEmpty() ){
        qDebug()<<"[MisliDir::addNoteFile]Note file is not readable, skipping: "<<pathToNoteFile;
        delete nf;
        return;
    }

    noteFiles_m.push_back(nf);
    nf->saveStateToHistory(); //should be only a virtual save for ctrl-z

    if(fsWatchIsEnabled) fs_watch->addPath(nf->filePath());
    connect(nf,SIGNAL(requestingSave(NoteFile*)),this,SLOT(handleSaveRequest(NoteFile*)));

    emit noteFilesChanged();
}

void MisliDir::handleSaveRequest(NoteFile *nf)
{
    nf->saveWithRequest = false;
    if(fsWatchIsEnabled) fs_watch->removePath(nf->filePath());
    nf->saveLastInHistoryToFile();
    if(fsWatchIsEnabled) fs_watch->addPath(nf->filePath());
    nf->saveWithRequest = true;
}
