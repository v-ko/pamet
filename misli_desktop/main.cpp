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

//release routine...done
//windows build...дън
//pri save v timeline-a се преебава периода (прави го да е от текущия начален до текущото време примерно)...дън
//2017.01.27
//Много ще е лесно да направя меню ентри за да ми отваря гугъл таймлайна на деня на който искам (от в мисли)...дън
//Добавяне на разделителни линии м/у модулите...остаи
//save aнимация с едно зелено тръгче просто , което да се появява и постепенно свива и изчезва...wontfix
//Set default search scope to current dir...done
//BUG: при пействане и нова записка не се закръглят координатите...дън
//BUG: auto-size-a ne save-a...done
//Memory leak при зареждането на снимките...дън
//оправи изобразяването на снимките
//BUG: backspace (last dir) does not work when switching with search...дън
//link mode samo ako ima asociirana zapiska...дън
//BUG: при натискане на копче се появява сянката...дън

//виж във файла със записки

//Вграден rollback със staggered versioning:
//Да прочета за git workflow-a основните, щото е тъпо че още не го разбирам перфектно
//добави проверка дали гит e наличен
//напиши проверката при пускане кога трябва да се направи сл сейв и да го прави ако е минала датата
//а ако не е - да насрочва таймер за правенето му
//направи скрипт за добавянето на всички досегашни записи от гит през 1 ден интервал
//Интерфейса в таймлайна ще е прост - тогъл бутон, който да менка "Върни на маркираната/Възстанови последната версия"
//А в самия таймлайн просто ще има някакъв маркер за всеки сейв и ще светва в жълто, когато е селектиран (=е най-близо
//до центъра), а останалите са червени. Активният в момента се маркира в зелено

//Installer stuff:
//linux installer
//arch package
//crash log в сетингс директорията, който обаче да може да се отваря от менюто

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
//Да преместя модулите в отделна директория
//да оправя в editnotewidnow мизериите

//Bugs:
//търсенето е прецакано и крашва мн редовно...тестване
//крашва при добавяне на папка..needs info
//Дебъгване на ъпдейта при синхронизация

//====Release routine====
//update translations
//commit
//build on Windows
//За да се ползва FreeType и да излизат по същия начин текстовете трябва да се добави qt.conf в bin (не се е ебавам)
//директорията, в който да има: [Platforms] \n WindowsArguments = fontengine=freetype
//bump version: in MisliDesctopGUI and the installer
//Тук в QtCreator add deployment step: C:\Qt\5.8\mingw53_32\bin\windeployqt.exe --dir data ./release/misli.exe  (в build dir-a)
//Добавяш misli.exe и qt.conf на ръка в същата папка
//Select all , десен бутн, 7зип - compress to "data.7z"
//Cut data.7z and paste to .../installer/packages/com.p10.misli/data
//build installer PS C:\C++\misli\misli\installer> C:\Qt\QtIFW2.0.0\bin\binarycreator.exe --offline-only -c config\config.xml -p packages MisliInstaller.exe
//pray to Bill Gates

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

