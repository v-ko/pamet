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

//23.04.15 - подкарах всичко най-накрая и андроидската даже без видими бъгове
//the search is fixed ! --done
//display dates in the context menu --done
//FIXME -tata --done
//ctrl-R за rename file --done
//ctrl-Del за delete file --done
//Дублира линковете (повече от 1 на записка) --done
//GitHub README --done
//в misliwindow: select the note... : pravq go da imitira click za da ne prenapisvam ne6ta --done
//Да премества мишката в центъра на resize circle-a, а не него да го мести директно --done
//Redo --done
//100x undo/redo --done
//loading cursor when loadin an added misli_dir --done
//picture compatability (nqkoi kartinki ne se zarejdat) --done
//da priema samo po edno URI ! canvas::pasteMimeData --done
//accept drag/drop - v canvas da dovyr6a dropevent-a , posle v paintevent --done
//in edit note dialog: when making syscall : don't delete existing text --done
//web page name/display/open --done
//архиви - не , тая програма е за активни проекти, а не за архивиране --done
//Curved lines --done

//check for misliVersion.xml na misli.appspot.com (za desktop only) --done
//current_desktop_version.xml (4e da moje da se nadgrajda s dr elementi) --done
//селектирането докато се променя контрол пойнта е прецакано --done
//linkovete da se init-vat sprqmo kontrol pointa a ne p1 --done

//BUG: autoSize pravi nqkakva gre6ka pri malki textove --done
//BUG: lo6 import na text file/picture --done
//Няма да е различен дабъл клика на андроид за сега --done
//Obnovqvane na tekstovite файлове - on select --done
//granica i nadpis sys imeto na text file --done
//loading mouse при общите сценарии --done

//тест до лятото--done
//ctrl+R ne ba4ka --done
//При редакция на записка не скъсява текста като сейвна --done
//при копи пейст на само една записка все пак да я лепва за мишката --done
//при копи/пейст/местене не транслира контролните точки на линковете --done
//от менюто на десния бутон за сменяне на текущия файл със записки не сменя като се цъкне --done
//не лоадва променените на диска файлове със записки правилно (изкарва ги празни) --в момента няма проб
//фокус on the search field --done
//Макс сърч резултати --done

//Крашва при смяна на езика: delete later!! --done
//Шорткътите на кирилица не бачкат

//ima nqkakyv tegav problem s id-tata pri kopirane i/ili pri polu4avane na filechange koito zatriva ili golqma 4ast ot
//zapiskite ili vsi4ki
//windows installer (offline) https://doc.qt.io/qtinstallerframework/ifw-tutorial.html
//test upgrade
//merge to master
//upload all
//arch package

//====Future stuff====
//Трололо мод при който записките бягат от мишката , който се активира автоматично на 1 април
//MIME type/file association
//http://doc.qt.io/qt-5/qmimedatabase.html = Get file type Qt
//when Chrome->Qt text/uri-list is fixed - accept multiple URIs

//====Release routine====
//update translations
//commit
//build on Windows

//=========Test cases===========
//Input inaccessible/non-existent dir when adding a dir

#include "mislidesktopgui.h"

int main(int argc, char *argv[])
{
    MisliDesktopGui misli(argc, argv);
    return misli.exec();
}

