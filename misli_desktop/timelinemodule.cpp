#include "timelinemodule.h"

#include <QCheckBox>
#include "../mislidir.h"

TimelineModule::TimelineModule()
{
}

NotesModule::NotesModule():
    TimelineModule(),
    checkbox("Notes module")
{
    widget = &checkbox;
}

ArchiveModule::ArchiveModule():
    TimelineModule(),
    checkbox("Archive module")
{
    widget = &checkbox;
    noteFile.setFilePath("/sync/misli/archive.timeline");

}

QList<Note*> NotesModule::loadNotes()
{
    QList<Note*> list;

     misliDir = new MisliDir("/sync/misli",true,false);

    for(NoteFile *nf: misliDir->noteFiles())
    {
        qDebug()<<"Into the empty virtual function.";
        list.append( nf->notes );
    }

    return list;
}

QList<Note*> ArchiveModule::loadNotes()
{
    QList<Note*> list;

    list.append( noteFile.notes );

    return list;
}
