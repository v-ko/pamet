/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "filesystemwatcher.h"
#include "mislidir.h"
#include <QDebug>

#include "misliinstance.h"
#include "misli_desktop/mislidesktopgui.h"

FileSystemWatcher::FileSystemWatcher(MisliDir * misli_dir_)
{
    //addPath("/home/p10/Desktop/notes.misl");

    misli_dir=misli_dir_;

    qDebug()<<"Connect returns:"<<connect(this,SIGNAL(fileChanged(QString)),misli_dir,SLOT(handle_changed_file(QString)) );//,Qt::QueuedConnection) ;

}
FileSystemWatcher::~FileSystemWatcher()
{
}
