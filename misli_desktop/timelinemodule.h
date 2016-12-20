#ifndef TIMELINEMODULE_H
#define TIMELINEMODULE_H

#include <QObject>
#include <QWidget>
#include <QCheckBox>

#include <../misliinstance.h>

class TimelineModule : public QObject
{
    Q_OBJECT
public:
    TimelineModule();

    //Variables
    QWidget *widget;
signals:

public slots:
    virtual QList<Note*> loadNotes(){
        QList<Note*> dummy;
        return dummy;
    }
};

class NotesModule : public TimelineModule
{
    Q_OBJECT
public:
    NotesModule();

    //Variables
    QCheckBox checkbox;
    MisliDir *misliDir;
signals:

public slots:
    QList<Note*> loadNotes();
};

class ArchiveModule : public TimelineModule
{
    Q_OBJECT
public:
    ArchiveModule();

    //Variables
    QCheckBox checkbox;
    NoteFile noteFile;
signals:

public slots:
    QList<Note*> loadNotes();
};

#endif // TIMELINEMODULE_H
