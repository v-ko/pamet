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

#include "filesystemwatcher.h"
#include "mislidir.h"
#include <QDebug>

#include "misliinstance.h"
#include "misli_desktop/mislidesktopgui.h"

FileSystemWatcher::FileSystemWatcher(MisliDir * misli_dir_)
{
    //addPath("/home/p10/Desktop/notes.misl");

    misli_dir=misli_dir_;

    if(misli_dir->debug) qDebug()<<"Connect returns:"<<connect(this,SIGNAL(fileChanged(QString)),misli_dir,SLOT(handle_changed_file(QString)) );//,Qt::QueuedConnection) ;

}
FileSystemWatcher::~FileSystemWatcher()
{
}
