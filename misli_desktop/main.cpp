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

//release routine
//arch package
//crash log
//windows build за маги

//FIXME-tata

//====Future stuff====
//-Тегло
//-Geolocation - отделен widget
//-Имейли
//Трябва да има как отделно да въвеждам събития тип "за 1 път направих това нещо което продължи дълго след това"
//Бутон за скачане на избрана дата и бутон за скачане на сега
//DB size indicator
//save animation

//Refactoring:
//да преместя canvas в misli_desktop

//Bugs:
//търсенето е прецакано и крашва мн редовно...тестване
//крашва при добавяне на папка..needs info
//Дебъгване на ъпдейта при синхронизация

//====Release routine====
//update translations
//commit
//build on Windows
//build installer PS C:\C++\misli\misli\installer> C:\Qt\QtIFW2.0.0\bin\binarycreator.exe --offline-only -c config\config.xml -p packages MisliInstaller.exe

//=========Test cases===========
//Input inaccessible/non-existent dir when adding a dir

#include "mislidesktopgui.h"
#include "archivemodule.h"
#include "photomodule.h"
#include "notesmodule.h"
#include "communicationsmodule.h"
#include "statisticsmodule.h"

int main(int argc, char *argv[])
{
    MisliDesktopGui misli(argc, argv);
    Timeline *timeline = misli.misliWindow->timelineWidget.timeline;
    //Timeline modules
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

