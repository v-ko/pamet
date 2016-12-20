#ifndef TIMELINEWIDGET_H
#define TIMELINEWIDGET_H

#include <QWidget>

#include "timeline.h"

class MisliWindow;

namespace Ui {
class TimelineWidget;
}

class TimelineWidget : public QWidget
{
    Q_OBJECT

public:
    //Functions
    explicit TimelineWidget(MisliWindow *misliWindow_);
    ~TimelineWidget();

    //Variables
    MisliWindow *misliWindow;
    Timeline *timeline;
    Ui::TimelineWidget *ui;
};

#endif // TIMELINEWIDGET_H
