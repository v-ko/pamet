#ifndef PHOTOMODULE_H
#define PHOTOMODULE_H

#include "timelinemodule.h"

class PhotoModule: public TimelineModule
{
    Q_OBJECT
public:
    PhotoModule(Timeline *timeline_);

    //Variables
    QFutureWatcher<void> loadFuture;
    QPushButton reloadButton;
    QList<Note*> tmpNotes,library;
    bool libraryIsLoaded;
signals:

public slots:
    void afterLoadingIsDone();
    void loadToTmp(qint64 positionInMSecs, qint64 viewportSizeInMSecs);
    void updateNotesForDisplay();
};

#endif // PHOTOMODULE_H
