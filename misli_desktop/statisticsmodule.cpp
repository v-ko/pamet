#include "statisticsmodule.h"

#include <QVBoxLayout>
#include <QMessageBox>

#include "timelinewidget.h"
#include "misliwindow.h"

StatisticsModule::StatisticsModule(Timeline *timeline_):
    TimelineModule(timeline_)
{
    timeline = timeline_;
    qtColorCodes = { 7,8,9,10,11,12,13,14,15,16,17,18,19 };

    //Setup the control widget
    controlWidget = new QWidget(timeline->timelineWidget);
    //Create the layout
    QVBoxLayout *layout = new QVBoxLayout(controlWidget);
    controlWidget->setLayout(layout);

    //Add a button to open the data file when needed and an update button
    QPushButton *openDataFileButton = new QPushButton("Open data file", controlWidget),
            *reloadDataFileButton = new QPushButton("Reload data file", controlWidget);
    layout->addWidget(openDataFileButton);
    layout->addWidget(reloadDataFileButton);
    connect(openDataFileButton, &QPushButton::clicked, [&](bool){
        if(statsFilePath().isEmpty()){
            QMessageBox::information(controlWidget,tr("FYI"),tr("No statistics file present."));
        }
        QDesktopServices::openUrl(QUrl(statsFilePath()));
    });
    connect(reloadDataFileButton, &QPushButton::clicked, this, &StatisticsModule::loadStats);

    loadStats();
}

void StatisticsModule::paintRoutine(QPainter &painter)
{
    QList<Statistic*> statsForDrawing;
    QFont font;
    font.setPixelSize(10);
    painter.setFont(font);

    //Get the stats that have been selected into a list
    for(Statistic &st: stats){
        for(QCheckBox *checkBox: checkboxes){
            if(checkBox->isChecked() && (checkBox->text()==st.name) ){
                if(statsForDrawing.size()>=qtColorCodes.size()){
                    qDebug()<<"Not enough color codes to show all stats. Leaving the last ones unrepresented";
                }else{
                    statsForDrawing.append(&st);
                }
            }
        }
    }

    for(Statistic *st: statsForDrawing){
        painter.setPen(QColor(Qt::GlobalColor(qtColorCodes[statsForDrawing.indexOf(st)])));
        int textX = ( statsForDrawing.indexOf(st)%10 )*100; //100px per caption
        int textY = ( statsForDrawing.indexOf(st)/10 )*30+50; //10 captions per row
        painter.drawText(textX,textY,st->name);

        for(int i=0; i<st->values.size() ; i++){
            painter.drawEllipse(timeline->toPixelsFromMSecs(st->timestamps[i].toMSecsSinceEpoch()),
                                timeline->baselineY()-Scale(10,timeline->baselineY(),st->values[i]),5,5);
            //if()
        }
    }
}

void StatisticsModule::loadStats()
{
    if(!statsFilePath().isEmpty()){
        QFile file(statsFilePath());
        if(!file.open(QIODevice::ReadOnly)){
            qDebug()<<"Error on opening the stats file for reading.";
            return;
        }
        stats.clear();
        while(!file.atEnd()){
            QString row = QString(file.readLine()).trimmed();
            if(row.isEmpty()) break; //at end (probably only a newline char is left)
            QStringList values = row.split(",");
            if(values.size()!=3){
                qDebug()<<"Bad stats data";
                break;
            }
            Statistic* statistic = statsbyName(values[1]);
            if(statistic==NULL){

                stats.push_back(Statistic());
                statistic = &stats.back();
                statistic->name = values[1];
            }
            statistic->timestamps.append(QDateTime::fromString(values[0],"yyyy.MM.dd hh:mm:ss"));
            statistic->values.append(values[2].toFloat());
        }
        file.close();
    }

    //Clear all of the checkboxes (if any)
    for(QCheckBox *checkBox: checkboxes){
        checkBox->deleteLater();
        checkboxes.removeOne(checkBox);
    }
    //Add a checkBox for each statistic
    for(Statistic &st: stats){
        checkboxes.append(new QCheckBox(st.name,controlWidget));
        checkboxes.back()->setChecked(true);
        //checkboxes.back()->setStyleSheet("QCheckBox { color: "+QColor(qtColourCodes" }");
        controlWidget->layout()->addWidget(checkboxes.back());
    }
}
void StatisticsModule::saveStats()
{
    if(!statsFilePath().isEmpty()){
        QFile file(statsFilePath());
        if(!file.open(QIODevice::WriteOnly|QIODevice::Truncate)){
            qDebug()<<"Error on opening the stats file for writing.";
            return;
        }
        QTextStream stream(&file);
        for(Statistic &st: stats){
            for(int i=0; i<st.timestamps.size(); i++){
                stream<<st.timestamps[i].toString("yyyy.MM.dd hh:mm:ss")<<","<<st.name<<","<<QString::number(st.values[i]);
            }
        }
        file.close();
    }
}
