/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

//tooltips --done
//dovyrshi bg help-a
//pri syzdavane na initial note-a da q slaga ot qrc

//donations

//LSB Build ?
//licensing

//final code review
//update translations
//commit

//Build windows
//Static build windows

//Video za predstavqne na angl i bg
//Nqkolko tester-a za durakoustoi4ivost

//Release
//razprostranenie

//Static build Linux
//Packages
//>arch package

//====Android port=========
//Za mobile versiqta - donations s napomnqne kolko rabota e svyr6ena

//=========Future changes=========
//ogledai mural.ly za idei
//polzvai enum za note type
//opravi for loop-ovete na c++11
//*Automated test with some tool for automation (make note , choose dir , make link , etc.)
//Progress bars
//Proper logging
//Redo
//Memory based undo/redo limitation

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

