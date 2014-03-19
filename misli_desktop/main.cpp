/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

//----------Second major release-------------

//updategl pri select all --done
//езикът да е в отделно меню --done
//da ne se povdiga zapiskata a da se poqvqva nadpis "move" s podravnitelni linii ot rybovete --done
//промени дефулта за големината на записката - да са по-широки и по-ниски --done
//BUG : double-click-a da iska edno i sy6to mqsto --done
//BUG : segfault pri pravene na link sled kopirane (dava ednakvi id-ta ponqkoga pri kopirane)--done
//БЪГ: като преименувам нф и нф-тата които имат линк записки към първия не се сейват за да се запази--done
//преименуването на линк нф-тата--done
//BUG: pri skysqvane na teksta na link note file --done
//mahane ili opravqne na auto adjust height --done
//BUG: "external deleted" ne se maha dori kato se nameri file-a --done
//premesti petko10.h funkciite da sa v git --done 15.03.2014

//===========Additional features========
//about dialog - v nego da pi6e i versiqta
//               link to bug tracking
//update prompt sled 6-12 meseca (primerno)?
//>Nova help sistema?
//>First start window s izbirane na ezika
//"use home folder" kop4e pri pyrvo puskane na programata (za direktoriq)
//ctrl+shift+V za paste ot clipboard-a
//pri linkvaneto da dava spisyk s nfiles (moje s inducirane na kontekstovo menu prosto

//arch package
//LSB Build ?

//Video za predstavqne na angl i bg
//Release
//razprostranenie

//====Android port=========
//BUG: pinch out-a da ne mesti nalqvo nadqsno
//Android UI s mestene na vsi4ko ob6to v canvas i MisliInstance
//Za mobile versiqta - donations s napomnqne kolko rabota e svyr6ena

//=========Good practice changes=========
//ogledai mural.ly za idei
//polzvai enum za note type
//opravi for loop-ovete na c++11
//*Automated test with some tool for automation (make note , choose dir , make link , etc.)

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

