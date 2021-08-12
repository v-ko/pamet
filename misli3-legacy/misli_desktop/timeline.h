#ifndef TIMELINE_H
#define TIMELINE_H

#include <QWidget>
#include <QTimer>
#include <QPainter>
#include <QSlider>

#include "timelinemodule.h"
#include "archivemodule.h"
#include "../notefile.h"
#include "../util.h"

class TimelineWidget;

class Timeline : public QWidget
{
    Q_OBJECT
   
public:
    //Functions
    explicit Timeline(TimelineWidget *timelineWidget_);
    ~Timeline();
    int scaleToPixels(qint64 miliseconds);
    double scaleToMSeconds(qint64 pixels);
    int toPixelsFromMSecs(qint64 miliseconds);
    void drawDelimiter(QPainter* painter, qint64 delimiterInMSecs, double lineHeight);
    void addModule(TimelineModule *module);
    qint64 leftEdgeInMSecs();
    double baselineY();
    double fontSizeForNote(Note *nt);
    Note *getNoteUnderMouse(QPoint mousePosition);

    //Variables
    QList<TimelineModule*> modules;
    QList<Note*> usedNotes;
    TimelineWidget *timelineWidget;
    qint64 viewportSizeInMSecs;
    qint64 positionInMSecs; //position of the center of the visible timeline
    //miliseconds since (or before for negative values) 1970.1.1 00:00:00 (the posix standard)
    QSlider slider;
    double baselinePositionCoefficient;
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
