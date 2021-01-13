#ifndef NOTESMODULE_H
#define NOTESMODULE_H

#include "timelinemodule.h"

class NotesModule : public TimelineModule
{
    Q_OBJECT
public:
    NotesModule(Timeline *timeline_);

    //Variables
    QCheckBox checkbox;
    Library *misliDir;
signals:

public slots:
    void loadNotes();
};

#endif // NOTESMODULE_H
