#ifndef ARCHIVEMODULE_H
#define ARCHIVEMODULE_H

#include "timelinemodule.h"

class ArchiveModule : public TimelineModule
{
    Q_OBJECT
public:
    ArchiveModule(Timeline *timeline_);

    //Variables
    NoteFile noteFile;
    QCheckBox checkbox;
};

#endif // ARCHIVEMODULE_H
