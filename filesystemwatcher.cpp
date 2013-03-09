#include "filesystemwatcher.h"
#include "misliinstance.h"

FileSystemWatcher::FileSystemWatcher(MisliInstance * misl_i_)
{
    misl_i=misl_i_;

    connect(this,SIGNAL(fileChanged(QString)),this,SLOT(call_misl_file_changed(QString)));
}

void FileSystemWatcher::call_misl_file_changed(QString qstr)
{
    misl_i->file_changed(qstr);
}
