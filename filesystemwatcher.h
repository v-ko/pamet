/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef FILESYSTEMWATCHER_H
#define FILESYSTEMWATCHER_H

#include <QFileSystemWatcher>

class MisliDir;

class FileSystemWatcher : public QFileSystemWatcher
{
    Q_OBJECT
public:
    FileSystemWatcher(MisliDir * misli_dir_);
    ~FileSystemWatcher();
    
    //Variables
    MisliDir * misli_dir;
};

#endif // FILESYSTEMWATCHER_H
