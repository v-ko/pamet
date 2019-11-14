#ifndef STATISTICSMODULE_H
#define STATISTICSMODULE_H

#include "misliwindow.h"

class StatisticsModule : public TimelineModule
{
public:
    struct Statistic{
        QString name;
        QList<QDateTime> timestamps;
        QList<double> values;
    };

    //Functions
    StatisticsModule(Timeline *timeline_);
    Statistic* statsbyName(QString name){
        for(Statistic &st: stats){
            if(name==st.name) return &st;
        }
        return nullptr;
    }
    QString statsFilePath(){
        QFileInfo statsFile(timeline->timelineWidget->misliWindow->misliLibrary()->fileStoragePath + "/statistics.csv");
        if(statsFile.exists()){
            return statsFile.filePath();
        }else{
            qDebug()<<"Stats file path is empty";
            return QString();
        }
    }

    //Variables
    QList<Statistic> stats;
    QList<QCheckBox*> checkboxes;
    QList<int> qtColorCodes;

public slots:
    void loadStats();
    void saveStats();
    void paintRoutine(QPainter &painter);
};

#endif // STATISTICSMODULE_H
