#include "timelinemodule.h"

#include <QDir>
#include <QDirIterator>
#include <QCheckBox>
#include <QMediaMetaData>
#include "../mislidir.h"
#include "timeline.h"

TimelineModule::TimelineModule(Timeline *timeline_)
{
    timeline = timeline_;
}
