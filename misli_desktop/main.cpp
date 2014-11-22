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



//Na note.h sym (pi6e do kyde) s prenapisvaneto

//GitHub README
//>arch package

//=========Future changes=========
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
    //In the constructor:
    //1.Load the language and fail-safe settings and construct the windows
    //2.present splash screen
    //3.Start loading notes asynchronosly
    //4.Present GUI

    return misli.exec();
}

