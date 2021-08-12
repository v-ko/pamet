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

    connect( ui->googleTimelinePushButton, &QPushButton::clicked, [&](){
        QString address = QDateTime::fromMSecsSinceEpoch( timeline->positionInMSecs ).toString("yyyy-MM-dd");
        address = "https://www.google.com/maps/timeline?pb=!1m2!1m1!1s"+address;
        QDesktopServices::openUrl(QUrl(address));
    });
}

TimelineWidget::~TimelineWidget()
{
    delete ui;
    delete timeline;
}
