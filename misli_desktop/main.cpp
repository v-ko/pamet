/*  This file is part of Misli.

    Misli is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Misli is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "../global.h"
#include "mislidesktopgui.h"
#include "archivemodule.h"
#include "photomodule.h"
#include "notesmodule.h"
#include "communicationsmodule.h"
#include "statisticsmodule.h"

int main(int argc, char *argv[])
{
    MisliDesktopGui misli(argc, argv);

    //Timeline modules
    Timeline *timeline = misli.misliWindow->timelineWidget.timeline;
    //NotesModule *notesModule = new NotesModule(timeline);
    PhotoModule *photoModule = new PhotoModule(timeline);
    CommunicationsModule *communicationsModule = new CommunicationsModule(timeline);
    StatisticsModule *statisticsModule = new StatisticsModule(timeline);
    //timeline->addModule(notesModule);
    timeline->addModule(photoModule);
    timeline->addModule(communicationsModule);
    timeline->addModule(statisticsModule);

    return misli.exec();
}

