#ifndef TIMELINEMODULE_H
#define TIMELINEMODULE_H

#include <QObject>
#include <QWidget>
#include <QCheckBox>
#include <QPushButton>
#include <QProcess>
#include <QThread>
#include <QtConcurrent/QtConcurrent>
//FIXME those are needed in the individual modules

#include <../library.h>

class Timeline;

class TimelineModule : public QObject
{
    Q_OBJECT
public:
    TimelineModule(Timeline *timeline_);

    //Variables
    Timeline *timeline;
    QWidget *controlWidget;
    QList<Note*> notesForDisplay;

    //Virtual functions
public slots:
    virtual void paintRoutine(QPainter &) {}
};

#endif // TIMELINEMODULE_H
