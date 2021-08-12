#include "archivemodule.h"

ArchiveModule::ArchiveModule(Timeline *timeline_):
    TimelineModule(timeline_),
    checkbox("Archive module")
{
    controlWidget = &checkbox;
    noteFile.setPathAndLoad("/sync/misli/.misli_timeline_database.json");
}
