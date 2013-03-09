#ifndef FILESYSTEMWATCHER_H
#define FILESYSTEMWATCHER_H

#include <QFileSystemWatcher>

class MisliInstance;

class FileSystemWatcher : public QFileSystemWatcher
{
    Q_OBJECT
public:
    FileSystemWatcher(MisliInstance * misl_i_);
    
    //Variables
    MisliInstance * misl_i;
signals:
    
public slots:
    void call_misl_file_changed(QString qstr);
};

#endif // FILESYSTEMWATCHER_H
