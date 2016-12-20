#include "timelinewidget.h"
#include "ui_timelinewidget.h"

#include <QLayout>

#include "misliwindow.h"

TimelineWidget::TimelineWidget(MisliWindow *misliWindow_) :
    QWidget(misliWindow_),
    ui(new Ui::TimelineWidget)
{
    misliWindow = misliWindow_;
    ui->setupUi(this);
    timeline = new Timeline(this);
    ui->horizontalLayout->addWidget(timeline);
}

TimelineWidget::~TimelineWidget()
{
    delete ui;
}
