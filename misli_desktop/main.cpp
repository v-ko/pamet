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

//opravqm search-a


//=========Future changes=========
//GitHub README
//>arch package
//MIME type and CLI open file
//display dates in status bar/on hover
//display search results i hidesearchstuff da sa lambdas
//ako ima update prosto da se poqvqva menu-to update
//FIXME -tata
//debug option in CLI
//loading cursor when loadin an added misli_dir
//макс символи на записка да са поне двойно, а ограничението при ауто сайз-а да е на размер
//git versioning
//да dump-ва лог-а на файл
//да деселектва при ентер ако не е в/у записка
//Дублира линковете (повече от 1 на записка)
//Да премества мишката в центъра на resize circle-a, а не него да го мести директно
//селектирането с клавиатура не бачка
//ctrl-R за rename file
//ctrl-Del за delete file
//Frame-oве в които да се дропват записки (и да си имат идентификатори, които после да могат да се ползват за widget-и)
//BUG: text poleto (pri pravene na zapiska) nqama copy/paste - za6toto nqma fokus za shorcutite?
//BUG:При добавяне на текст не auto-size-ва текста
//Feature:backspace - за връщане на предната записка
//Tagove
//Common .user file settings Qt
//Ima nqkyde integer smqtane pri koordinatite na strelkite (eventualno i zapiskite)
//picture compatability (nqkoi kartinki ne se zarejdat)
//install target through the .pro file (and INSTALLS clouses)
//Pri enter da selectva i linkove ako ima
//dva pyti cykvane na desen buton da e link
//izvitite linii da sa vektorno obusloveni (az da si gi 4ertaq)
//imenata na elementite da sa na obratno buttonEdikakvo si i menuEdiKakvoSI , za da gi namiram lesno
//BUG: da ne trie klipborda ako ne e successful copy
//QStandardPaths::DataLocation default
//ogledai mural.ly za idei
//polzvai enum za note type
//opravi for loop-ovete na c++11
//Automated test with some tool for automation (make note , choose dir , make link , etc.)
//Progress bars
//Proper logging
//Redo
//Memory based undo/redo limitation
//CLI
//Do 15 septemvri 2015 da sym izkaral autoupdate-va6ta versiq
//Video za predstavqne na angl i bg

//====Android port=========
//Za mobile versiqta - donations s napomnqne kolko rabota e svyr6ena

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

