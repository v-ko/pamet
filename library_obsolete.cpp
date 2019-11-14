///*  This file is part of Misli.

//    Misli is free software: you can redistribute it and/or modify
//    it under the terms of the GNU General Public License as published by
//    the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.

//    Misli is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU General Public License for more details.

//    You should have received a copy of the GNU General Public License
//    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
//*/

//#include "library.h"

//MisliInstance::MisliInstance()
//{
//}
//MisliInstance::~MisliInstance()
//{
//    for(Library *misliDir: misliDirs_m) delete misliDir;
//}

//QList<Library*> MisliInstance::misliDirs()
//{
//    return misliDirs_m;
//}

//Library *MisliInstance::addDir(QString path)
//{
//    Library *md = loadDir(path);
//    saveDirsToSettings();
//    emit misliDirsChanged();
//    return md;
//}
//Library *MisliInstance::loadDir(QString path)
//{
//    Library * md = new Library(path);
//    misliDirs_m.push_back(md);
//    return md;
//}
//void MisliInstance::removeDir(Library *dir)
//{
//    unloadDir(dir);
//    saveDirsToSettings();
//    emit misliDirsChanged();
//}
//void MisliInstance::unloadDir(Library *dir)
//{
//    delete dir;
//    misliDirs_m.removeOne(dir);
//}

//void MisliInstance::loadStoredDirs()
//{
//    //Clear first
//    for(Library* misliDir: misliDirs_m) delete misliDir;
//    misliDirs_m.clear();

//    QStringList notesDirs;

//    //------Extract the directory paths from the settings----------
//    if(settings.contains("notes_dir")){
//        notesDirs = settings.value("notes_dir").toStringList();
//        qDebug()<<"Loading notes dirs:"<<notesDirs;
//    }

//    //-------Load the directories------------------------
//    for(QString notesDir: notesDirs){
//        loadDir(notesDir);
//    }

//    //New stuff
//    if( (notesDirs.size() > 1) | (notesDirs.size() < 0) ){
//        qDebug() << "Bad notes dirs size (!=1)";
//        return;
//    }
//    fileStoragePath = notesDirs[0];
//}
//void MisliInstance::saveDirsToSettings()
//{
//    QStringList notesDirsStringList;
//    for(Library* misliDir: misliDirs_m) notesDirsStringList.push_back(misliDir->folderPath);

//    settings.setValue("notes_dir",QVariant(notesDirsStringList));
//    settings.sync();
//}
