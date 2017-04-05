#include "archivemodule.h"

ArchiveModule::ArchiveModule(Timeline *timeline_):
    TimelineModule(timeline_),
    checkbox("Archive module")
{
    controlWidget = &checkbox;
    noteFile.setFilePath("/sync/misli/archive.timeline");
}
