/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

//---------------------------------------------------------------------
//QtLib bugs:
//BUG: next i prev nf ne ba4kat s + i -
//BUG: menu-tata ne se zatvarqt kato cykne6 2 pyt

//Android UI s mestene na vsi4ko ob6to v canvas i MisliInstance
//po-dobyr help
//video za predstavqne na angl i bg
//First launch dialogue : do you want to see a short clip or display help

//Release routine:
//update translations
//commit
//build on Windows

//razprostranenie


//---------Good practice changes----------
//polzvai enum za note type
//opravi for loop-ovete na c++11

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

