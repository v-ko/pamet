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

#include "misliinstance.h"

MisliInstance::MisliInstance()
{
}
MisliInstance::~MisliInstance()
{
    for(MisliDir *misliDir: misliDirs_m) delete misliDir;
}

QList<MisliDir*> MisliInstance::misliDirs()
{
    return misliDirs_m;
}

MisliDir *MisliInstance::addDir(QString path)
{
    MisliDir *md = loadDir(path);
    saveDirsToSettings();
    emit misliDirsChanged();
    return md;
}
MisliDir *MisliInstance::loadDir(QString path)
{
    MisliDir * md = new MisliDir(path);
    misliDirs_m.push_back(md);
    return md;
}
void MisliInstance::removeDir(MisliDir *dir)
{
    unloadDir(dir);
    saveDirsToSettings();
    emit misliDirsChanged();
}
void MisliInstance::unloadDir(MisliDir *dir)
{
    delete dir;
    misliDirs_m.removeOne(dir);
}

void MisliInstance::loadStoredDirs()
{
    //Clear first
    for(MisliDir* misliDir: misliDirs_m) delete misliDir;
    misliDirs_m.clear();

    QStringList notesDirs;

    //------Extract the directory paths from the settings----------
    if(settings.contains("notes_dir")){
        notesDirs = settings.value("notes_dir").toStringList();
        qDebug()<<"Loading notes dirs:"<<notesDirs;
    }

    //-------Load the directories------------------------
    for(QString notesDir: notesDirs){
        loadDir(notesDir);
    }
}
void MisliInstance::saveDirsToSettings()
{
    QStringList notesDirsStringList;
    for(MisliDir* misliDir: misliDirs_m) notesDirsStringList.push_back(misliDir->folderPath);

    settings.setValue("notes_dir",QVariant(notesDirsStringList));
    settings.sync();
}
