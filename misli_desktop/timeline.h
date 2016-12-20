#ifndef TIMELINE_H
#define TIMELINE_H

#include <QWidget>
#include <QTimer>
#include <QPainter>
#include <QSlider>

#include "timelinemodule.h"
#include "../notefile.h"
#include "../petko10.h"

class TimelineWidget;

class Timeline : public QWidget
{
    Q_OBJECT
   
public:
    //Functions
    explicit Timeline(TimelineWidget *timelineWidget_);
    float scaleToPixels(qint64 miliseconds);
    float scaleToSeconds(qint64 pixels);
    void drawDelimiter(QPainter* painter, qint64 delimiterInMSecs, float lineHeight);
    void addModule(TimelineModule *module);
    qint64 leftEdgeInMSecs();
    float baselineY();
    float fontSizeForNote(Note *nt);
    Note *getNoteUnderMouse(QPoint mousePosition);

    //Variables
    QList<TimelineModule*> modules;
    QList<Note*> notes, usedNotes;
    TimelineWidget *timelineWidget;
    qint64 viewportSizeInMSecs;
    qint64 positionInMSecs; //miliseconds since (or before for negative values) 1970.1.1 00:00:00 (the posix standard)
    QSlider slider;
    float baselinePositionCoefficient;
    ArchiveModule archiveModule;
    int lastMousePos;

    //Test stuff
    QTimer refresh;
signals:

public slots:

protected:
    void paintEvent(QPaintEvent *);
    void wheelEvent(QWheelEvent *event);
    void mouseDoubleClickEvent(QMouseEvent *event);
    //void mousePressEvent(QMouseEvent *event);
    void mouseMoveEvent(QMouseEvent *event);
    void mouseReleaseEvent(QMouseEvent *event);
};

#endif // TIMELINE_H
