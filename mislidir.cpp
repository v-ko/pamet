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

#include "misliinstance.h"
#include "mislidir.h"
#include "misli_desktop/misliwindow.h"
#include "misli_desktop/mislidesktopgui.h"

MisliDir::MisliDir(QString nts_dir, bool enableFSWatch)
{
    fsWatchIsEnabled = enableFSWatch;
    currentNoteFile = NULL;
    lastNoteFile = NULL;
    keepHistoryViaGit = false;

    //FS-watch stuff
    if(fsWatchIsEnabled){
        fs_watch = new QFileSystemWatcher(this);
        connect(fs_watch,SIGNAL(fileChanged(QString)),this,SLOT(handleChangedFile(QString)) );
        hangingNfCheck = new QTimer;
        connect(hangingNfCheck,SIGNAL(timeout()),this,SLOT(checkForHangingNFs() ));
    }else{
        fs_watch = NULL;
        hangingNfCheck = NULL;
    }

    //Connect propery changes
    connect(this,SIGNAL(noteFilesChanged()),this,SLOT(reinitNotesPointingToNotefiles()));

    //Setup
    setDirectoryPath(nts_dir);
}
MisliDir::~MisliDir()
{
    softDeleteAllNoteFiles();
    delete fs_watch;
    delete hangingNfCheck;
}
QString MisliDir::directoryPath()
{
    return directoryPath_m;
}
void MisliDir::setDirectoryPath(QString newDirPath)
{
    QDir newDir(newDirPath);
    if(!newDir.exists()){
        qDebug()<<"[MisliDir::setDirectoryPath]Directory missing, creating it.";
        if(!newDir.mkdir(newDirPath)){
            qDebug()<<"[MisliDir::setDirectoryPath]Failed making directory:"<<newDirPath;
            return;
        }
    }
    directoryPath_m = newDirPath;

    QFileInfo gitOptionFile(newDir.filePath(".keep_history_via_git"));
    if(gitOptionFile.exists()) keepHistoryViaGit = true;

    //Upon leading at least the current dir is set to this one in order to correct relative paths in the Note class
    //which has no access to the MisliDir class and its info
    QDir::setCurrent(directoryPath_m);

    loadNotesFiles();

    if(keepHistoryViaGit){
        //Do a profilactic or innitial commit
        QProcess p;
        p.start("git",QStringList()<<"init");
        p.waitForFinished();
        qDebug()<<p.readAll();
        p.start("git",QStringList()<<"add"<<"-A");
        p.waitForFinished();
        qDebug()<<p.readAll();
        p.start("git",QStringList()<<"commit"<<"-m"<<"'Dir init commit'");
        p.waitForFinished();
        qDebug()<<p.readAll();
        p.start("git",QStringList()<<"gc"<<"--auto");
        p.waitForFinished();
        qDebug()<<p.readAll();
    }

    emit directoryPathChanged(newDirPath);
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
            if( nf->init() == 0 ){ //File is found and initialized properly
                nf->isReadable = true;
                //qDebug()<<"Adding path to fs_watch: "<<nf->filePath_m;
                fs_watch->addPath(nf->filePath_m); //when a file is deleted it gets off the fs_watch and we need to re-add it when a unix-type file save takes place
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
    return NULL;
}

NoteFile * MisliDir::defaultNfOnStartup()
{
    for(NoteFile *nf: noteFiles_m){
        if(nf->isDisplayedFirstOnStartup) return nf;
    }
    return NULL;
}

int MisliDir::makeNotesFile(QString name)
{
    QFile ntFile;
    QString filePath;

    if(noteFileByName(name)!=NULL){ //Check if such a NF doesn't exist already
        return -1;
    }

    filePath=QDir(directoryPath_m).filePath(name+".misl");

    ntFile.setFileName(filePath);

    if(!ntFile.open(QIODevice::WriteOnly)){ //Creates the NF
        qDebug()<<"Error making new notes file";
        return -1;
    }

    ntFile.close();

    addNoteFile(filePath);

    return 0;
}

void MisliDir::softDeleteNF(NoteFile* nf)
{
    if(nf==currentNoteFile) currentNoteFile=NULL;

    if(fsWatchIsEnabled) fs_watch->removePath(nf->filePath_m);
    noteFiles_m.removeOne(nf);
    delete nf;
    emit noteFilesChanged();
}

void MisliDir::loadNotesFiles()
{
    softDeleteAllNoteFiles();

    QDir dir(directoryPath_m);
    QStringList files = dir.entryList(QStringList()<<"*.misl",QDir::Files);

    for(QString fileName: files){
        addNoteFile(dir.absoluteFilePath(fileName));
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

    if(nf==NULL) return;//avoid segfaults on a wrong name

    if( nf->init()==0 ){
        nf->isReadable = true;
    }else if(err ==-2){ //most times the file is deleted and then replaced on sync , so we need to check back for it later
        nf->isReadable=false;
        hangingNfCheck->start(700);
    }
    emit noteFilesChanged();
}

void MisliDir::softDeleteAllNoteFiles()
{
    while(!noteFiles_m.isEmpty()){
        softDeleteNF(noteFiles_m.first());
    }
}

void MisliDir::deleteAllNoteFiles()
{
    QDir dir(directoryPath_m);

    for(NoteFile *nf: noteFiles_m){
        if(!dir.remove(nf->filePath())){
            qDebug()<<"[MisliDir::deleteAllNoteFiles]Could not remove notefile"<<nf->name();
            return;
        }
    }
    softDeleteAllNoteFiles();
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

void MisliDir::addNoteFile(QString pathToNoteFile)
{
    NoteFile *nf = new NoteFile;

    nf->saveWithRequest = true;
    nf->keepHistoryViaGit = keepHistoryViaGit;
    nf->eyeZ = defaultEyeZ();
    nf->setFilePath(pathToNoteFile);

    //If the file didn't init correctly - don't add it
    if(!nf->isReadable | nf->name().isEmpty() ){
        qDebug()<<"[MisliDir::addNoteFile]Note file is not readable, skipping:"<<pathToNoteFile;
        delete nf;
        return;
    }

    noteFiles_m.push_back(nf);
    nf->virtualSave(); //should be only a virtual save for ctrl-z

    if(fsWatchIsEnabled) fs_watch->addPath(nf->filePath());
    connect(nf,SIGNAL(requestingSave(NoteFile*)),this,SLOT(handleSaveRequest(NoteFile*)));

    emit noteFilesChanged();
}

void MisliDir::handleSaveRequest(NoteFile *nf)
{
    nf->saveWithRequest = false;
    if(fsWatchIsEnabled) fs_watch->removePath(nf->filePath_m);
    nf->hardSave();
    if(fsWatchIsEnabled) fs_watch->addPath(nf->filePath_m);
    nf->saveWithRequest = true;
}
