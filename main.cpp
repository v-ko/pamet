/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

//----------Second major release-------------
//about dialog
//link to bug tracking

//da ne se povdiga zapiskata a da se poqvqva nadpis "move" s podravnitelni linii ot rybovete

//BUG : segfault pri pravene na link sled kopirane
//БЪГ: като преименувам нф и нф-тата които имат линк записки към първия не се сейват за да се запази
//преименуването на линк нф-тата
//BUG: pri skysqvane na teksta na link note file
//BUG: "external deleted" ne se maha dori kato se nameri file-a
//BUG:ne6to ne pomni kakto trqbva poziciqta na NF (kato se smenqt)
//mahane ili opravqne na auto adjust height
//list of notefiles
//windows build

//arch package
//LSB Build ?

//Video za predstavqne na angl i bg
//Release
//razprostranenie

//===========Additional features========
//>Nova help sistema
//>First start window s izbirane na ezika
//"use home folder" kop4e pri pyrvo puskane na programata (za direktoriq)
//ctrl+shift+V za paste ot clipboard-a

//*Automated test with some tool for automation (make note , choose dir , make link , etc.)

//Release routine:
//update translations
//commit
//build on Windows

//====Android port=========
//Android UI s mestene na vsi4ko ob6to v canvas i MisliInstance
//Za mobile versiqta - donations s napomnqne kolko rabota e svyr6ena

//=========Good practice changes=========
//ogledai mural.ly za idei
//polzvai enum za note type
//opravi for loop-ovete na c++11
//premesti petko10.h funkciite da sa v git

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

