/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

//LOG

//v momenta parse-vaneto na key file-a (notes.ini) ne raboti , ne se znae dali izob6to zapisvaneto v obekta KeyFile raboti , ta tova e naleja6toto - done
//11.09.12 mai ima problem s razpredelqneto po redove --done
//+ horizontalniqt razmer na bukvite ne e 1 i teksta ne syvpada s poleto /+ima funkciq za tova v FTGL --done
//+ pixelizira teksta ,ta trqbva da go napravq poligonalen --done

//14.09.12 ne izlizat nqkoi bukvi (FTGL) (workaround s polzvaneto na drug FTFont (font2) ) --done
//+ da vgradq text-wrap-vaneto na FTGL --done
//+da debugna pozicioniraneto na nova zapiska --done

//16.09.11 trqbva new line support - za momenta nov (NAPRAVI GO) red se zamestva s "//" --done vsy6tnost nqma6e problem s noviq red ?!

//20.09.12 da sloja save-a kydeto trqbva (pri addNote) --done
//+ moje da sloja ob6tata 4ast na addNote fnkciite v edna otdelna i da q vikam s argumentite tam --done
//+da probvam s glutTimerFunc za da ne vyrti prekaleno mnogo Glib Main loop iterator-a --moved-->
//Kym stroeja:
//>vzimane na dir ot .conf file-a --done
//21.09.12 : vij addNoteBase (dovyrshvane na popravkata na funkciite) --done
//>pretyrsvane na dir-a za file-ove --done
//>>slagane na 1vi obekt v main (pravene na funkciq za smqna na segashnite notes) --done
//>dialog za izbirane na tablica za display (21.09.12 sega e s +/-)
//21.09.12 bug - pri polzvane na delete (ili ne samo) se kombinira sydyrjanieto na 2ta file-a --done
//+da napravq save_note_file(NoteFile *nf) koqto da vikam i da ne byrkam ostanaloto pri save --done
//Kym novi opcii:
//>delete --done
//>LINKOVE
//>>link obekt - po-dobre da sa zaka4eni nqkaksi kym note-a . Primerno vsqka harakteristika na linkovete da e value list v note-a ~~done
//>>syzdavane na link pri selectiran obekt --done
//>>korigirane teksta na link --done
//=================================================================================================

//22.09.12:DEBUG: poziciite na linkovete ne se smqtat pravilno . izob6to testvai linkovete --done
//+ ne se otvarq izob6to key filea , vyzmojni pri4ini - dobavqh z kydeto go nqma6e po funkciite (za da debugna gornoto) --done
//i delete-nah file-ovete . ta ili makeNotesFile ne srabotva s noviq kontext ili sys zetovete sym obyrkal ne6to --done
//>>risuvane na link --done
//>>zapisvane na infoto za link v file-a --done (30.09.12)
//                                      >>>export --done
//                                      >>>import --done

//>>>v render da pooprostq s lokalni promenlivi --done

//===================================================================================================30.09.12

//>edit note --done (02.10.12)

//BUG:file-a se preebava v nqkakvi situacii i header-a ili byte alignment-a mu se preebava za6toto izliza kato binaren (dropbox backtrack za sega)
 //-->edin hvanat slu4ai: "/s" se zamestva ot dva boklu4evi simvola (pri string list-ite na linkovete na edin note) (mai osobeno pri iztrivane na link.
//po nqkakva pri4ina i pri edin takyv simvlo se preebava celqt encoding na file-a) --mai e gotov,prosto trqbva da se save-va nf navreme ,ne ustanovih
//to4niqt problem ,no sybliudavai tova za da ne se poqvqva pak toz byg (9.10.12) --done

//>mestene --done
//>~resize (9.10.12 prikliu4ih s debugvaneto na resize i move)--done
//>ima byg pri mesteneto - kato premesti6 belejka render q vijda pravilno , pravilno se zapisva vyv file-a ,no se selectva samo na pyrvona4alna poziciq --done

//>manual linkvane --done
//>ikona --done (7.10.12 elementarna)
//============================================================================================09.10.12


//BUG:kato premestq zapiskata "az da narisuvam..." okolo child zapiskite i , pri opredeleno zasi4ane na elementi (ili eba li go kakvo) segmentira programata --done
//RAZ4ISTI KODA , ZA6TOTO TAKA DEBUG-VANETO SI E ---- MAMATA (18.10.12) vsi4ko koeto trqbva e po klasove --done

// po sredata na raz4istvaneto sym --done
// >> trqbva da zamestq publi4niq *note navsqkyde sys NoteFile::curr_nv ; --done
// >> trqbva da opravq bug-a za link_to_selected (koito e dosta dylboko , mai e zaradi lo6o vryzvane na nf pri dobavqne na zapiska ili ddz ?! ) --done

//BUG:resize-a ne ba4ka pri proizvolni zapiski (po-to4no na opredeleni pozicii project to plane smqta s gre6ka radiusa na kryga v/y ekrana ?!?!) 18.10.12--DONE

//>>selectirane na link --done
//>delete link --done
//>strelka na link-a --done

//=========================================================================================19.10.12

//Migrirane kym QT (za UI i GL render) i standartnite C++ biblioteki za vyzmojno nai-mn funkcii (za da sym minimalno zavisim ot UI platformata)
//>adaptirane na vsi4ki funkcii koito moga kym standartnite biblioteki v C::B --done

//FREEZE, zapo4vam migriraneto kym Qt --done
//>preminavane v QtCreator i adaptirane na render i input funkciite --done
//>>.conf file-a 6te e s qsettings ustavno --nqma problem s path-a --done
//>>dir za notes 6te e s prompt --done
//>>init notes files dir rutinata --done
//>>UI , input , debug i sme gotovi --done

//prenapisah algorityma za raz4itane na .misl (20.10.12) --done
//prenapisah NoteFile::save (20.10.12) --done

//<---------------------------------na4alo na zapisvaneto na tozi log v Qt proekta (22.10.12)----------

//moje da trqbva tozi red na opengl za blendata ako pixelizira (trqbva6e) --done

//TODO:
//>dovyr6vane na obrabotkata na klaviaturata (samo za ascii) --done
//>pravene na edit_note prozoreca --done

//Belejki: --stari
//ako 6te opravqm problema s ikonata trqbva da opravq programata da dava na GLUT prozoreca WM_CLASS property . prez glut ne stava , nai-dobroto koeto namerih e prez xlib : http://tronche.com/gui/x/xlib/ICC/client-to-window-manager/wm-class.html ne e problem v qt --done
//shte dava gre6ka ako conf-file-a e prazen(mai) v qt ne e problem --done
//trqbva da poopravq iteriraneto na main loop-a za da ne qde tolkova -- primerno da vyrti samo kogato e otvoren gtk prozoreca ne e problem v qt --done
//i da optimiziram algorityma za skysqvane na teksta --done (ot 4asti)

//>iterirane v g_main_loop samo za dialozite - izli6no, na qt sym --done
//====================================================================================22.10.12

//>razkarvane na FTGL i zamestvane s Qt ekvivalenta (+pointeri kym parent klasovete+ kysi imena na obektite) --done
//vyrvi prenapisvane na klasovete ot 2 dena (31.10.12) --done

//============================premestih se v 4istiq qt proekt=========================04.11.12

//izpipvane na izobrazqvaneto na teksta --done
//>interference na texturite s ostanaloto --done
//>preodolqvane na problema sys stypkovidnoto orazmerqvane (dosta typo polzvah ...i() gl funkciq) --done
//>da napravq taka 6toto da mi za4ita alpha kanala na texturata (GL_REPLACE e pravilniq mod ,ako ima alpha) --done

//================================================================================06.11.12

//>opravqne na resize-a --done

//BUG:segmentira pri move kato ima 2 file-a --done
//>prosledi v koi moment se preebava note_file[0].note[1][2][3]->nf->note --done
//sloji breakpointi po cqlata dyljina ,ta do addnote --done
//trqbva samo da vidq kyde se preebavat vs-te --done
//properties na pointera (nqkyde v note::init ili malko predi tova) --done

//mahane na ";" ot linkovete --done

//GetTextBetweenQT 6toto taq rabota deto q napravih za da zamestq strdup 4upi programata --done

//build na windows : --done
//>transparency problema ostana - ako sloji6 blend config funkciqta v setupGlenv se opravq transparency-to , --done
//no teksturite o6te ne rabotqt . Sig trqbva po-dobre da abstrahiram painter-a i GL --done
//push i pop atributi za 3te bubble-a (paint/save texture/draw) --done
//ima ne6to m/u note->init i drawGL --done

//opravi current_note_file --done

//============================================================================10.11.12

//>da opravq encoding-a na vsi4ko navsqkyde --done
//>>da izbera encoding : UTF-8 za file-ove , UTF-16 za programata (v momenta vs e UTF-8) --done
//>>promqna : UTF-8 za c-string-ovete i file-ovete , QString za tekstovi manipulacii --done
//>>da testvam dali FTGL raboti dobre s UTF-16 wchar (na win i linux) 6te polzvam QString+razkarah FTGL --done
//>>da namerq na4in za prosto konvertirane ot UTF-16 wchar/wstring kym UTF-8 za zapisvane vyv file --done
//>>opravqne na vs text sys polzvane na QString --done

//>note-ove so4e6ti kym file-ove : v teksta da se indikira s "this_note_points_to:..." --done
//>zapomnqne na pyrvona4alna poziciq - pomni pri smenite ot file na file, za sega stiga --done
//>imeto na file-a v title-a --done
//BUG:novite zapiski ne izlizat kydeto trqbva --done
//double-click za new note --done
//iz4istvane na text poleto na getNFName --done
//mai trqbva skysqvane na vremeto za zadyrjane na mi6kata za move note --done

//test windows --done
//set instrukcii za polzvane v .txt -ostavi , 6te pravq napravo oficialnata versiq --done

//==========================================================================16.11.12

//BUG:trqbva rebuild na Qt sys fontconfig bibliotekata nali4na za da ba4kat qt fontovete --done
//edit: vsy6tonost mai ne , tova e problem na ubuntu , za win mai se polzva dr mehanizym --done

//>opravqne na algorityma na key-value parser-a - ostavi q taq rabota za sega --done
//>info za note - data na modifikaciq , data na syzdavane --done
//>promqna na dt_mod pri smqna samo na texta --done
//>dati za linkovete ? -ne --done

//BUG:opravi mehanizma na pravene na na4alen nf ako nqma drugi ,grozno e - kvo mu e be --done
//BUG:layout independent input (pone za kirilica) - link s obqsnenie za shortcuts v tmp --done
//++note input enter calls button --done
//++note inpput escape calls hide+clear --done

//centrirane na teksta --done
//sqnka pri vdigane --done

//BUG:pri otvarqne na edit window v edit mode i zatvarqne ot [x] --done
//posle dori da cykne6 m za dr note_file editva posledniq --done

//id-tata da sa integer-i ,za da moga da pravq nevalidni/virtualni i pro4ie --done
//novi zapiski da se pravqt ne sled poslednoto id ,ami na pyrvoto prazno --done

//BUG:delete-vaneto o6te stava na porcii --done

//>otli4itelen znak na prenaso4va6tite zapiski --done

//==========================================================================18.11.12


//test windows --done
//prati na tati --done

//BUG:present a ne show --done

//user compatability:
//>help window - prosto textedit s vs-q text (daje moje da polzvam edit note) --done

//ctrl-z : prosto pazi starite file-ove i pri ctrl-z gi zarejdai --done
//>>reimplement init(NoteFile) ne , drugo be6e --done

//>menu-ta --done

//=================================================END Version 1 ,break, 26.11.12

//>prati na tati --done
//>neednakva skorost na scroll za razl viso4ini - ne --done

//>sloji tr() navsqkyde pri "tekstovete" ,za da se mahnat preduprejdeniqta --done
//clear screen dokato se zarejdat nf --done
//BUG:Clear settings and quit ne quit-va --done

//>this_note_points_to button --done
//BUG:link_to_selected moje da svyrzva zapisa sama sys sebesi --done

//===================================================3.12.12

//BUG:ne se dava fokus na text edit poleto pri edit/new link --done
//>copy-paste-cut - znes i links ,no bez visq6ti links --done

//BUG:segmentira pri copirane/cut na pove4e ot 1 note --done
//BUG:dava lo6a poziciq , no ima nqkakva zakonomernost --done

//build na Windows --done
//razpra6tane --done

//END Version 1.1 Hard Break===================================
//samo BUG deinost (+cvetove :D) ---------------------------

//BUG:ne se dava fokus na text edit pri make link --done
//BUG:help-a ne ba4ka na Windows --done
//dobavi orazmerqvaneto v help-a --done

//23.02.13===============================================resume
//zagotovki za ver.2 --------------------------

//podredi zada4ite po prioritet --done
//BUG: pri ry4en delete link ne se save-a nf --done
//splash screen --done
//marker v nf 4e e na4alen --done
//da ne e "enter a directory to store notes in " a primerno "enter a folder for the files with notes" --done
//smqna na window title na edit note window za new/edit note deistvie --done
//~set starting position , koito da raboti s make_all_notes_relative (ili tam kakvato be6e funkciqta v nf) --done
//mahai prazni prostranstva ot kraq na zapiskata --done
//pri nov file s enter da se dava ok --done
//shortcut za make link --done
//v class Note promeni nf na nf_id --done

//>iz4istvane na licencing-a --done
//version control --done

//BUG:da ima i izbirane na papka kato za beli hora --done

//nov parser - mnogo griji ima ... --done

//prevodi na angl i bg:--done
//>nadpisi v programata --done
//>>sloji tr navsqkyde --done
//>>izpolzvai linguist za prevoda --done
//>prevod na help NF --done
//>izpolzvane na noviq help pri F1 --done

//BUG:add new dir ne ba4ka --done

//quit s Q --done
//debugging (ebasi kolko zor be6e) --done

//nqkolko direktorii da mogat da se vkarvat (s menu za smqna?)--done
//remove current folder; --done
//ezici v settings + translator-a --done

//windows build --done

//sourceforge
//>setup git
//>setup binary download

//gledai za promeni v papkata i reload-vai

//video za predstavqne na angl i bg

//----release ver1+build na Win------------------------------------------
//razprostranenie

//BUG:opravqne na algoritma za orazmerqvane na teksta
//BUG:pri orazmerqvane na neselektirana zapiska se orazmerqva selektiranata

//za dolnite vij shemata v misli/misli
//>vkarvane na tekstovi fail , vkarvane na kartinka (s include_text_file:...)- otnositelno lesni (osobeno 1to)
//>cvetove: sinio,zeleno,4erveno,sivo,4erno,prazno
//>link file-ove s tekst razli4en ot imeto na file (text: atribut na nov red)



//-------------Late features--------------------:
//command line reset - ako se preebe kato pri kosio + kato udari nqkyde critical - da wipe-va settings
//Search + tags
//>avtoorazmerqvane na nova zapiska
//kontekstovi menu-ta s edit/delete...
//>config window i vkarvane na raznite #definirani ne6ta v settings
//wave select s ctrl+shift ili ne6to takova (selectirane na vs dy6terni zapiski pri click)
//alignment na text-a v zapiskite
//rename nf
//>preview na notefile-a pri markirane na prenaso4va6ta zapiska
//>izpisvane na datite (made/mod)
//>dialog za edit na link
//>opravqne skysqvaneto na teksta v linkovete
//>risuvane text-a na linkovete
//>link position set (auto,left,right,top,bottom)+ izvivane
//>zapiski po4ervenqva6ti s datata
//ako nqma zapiski na ekrana - naso4vane kym nai-blizkite
//keyboard navigation (sys centrirane na mi6kata ako se polzva za da izlizat zapiskite v centyra)

//da pomislq za max line lenght
//>da opravq render funkciqta 4e e mn skalypena
//>>BUG:pusni depth bufera za da ne sa strelkite pod senkite
//BUG: strelkite ne si update-vat posokata (na vyrhovete samo) pri mestene

//>semi-kanonizirane na koda
//>translations

//////////////////////////////////////////////////////////////////////////////////////////////////////////

//Maybe:
//BUG:na golemiq komp nqma multisampling
//>~font change
//minimum resize da e kolkto 3 bukvi za x i kolkoto viso4inata na reda + spacing za y

//Belejki:
//trqbva da se puska RCC pri promqna na nqkoi ot resursnite failove (moje izkustveno da promenq ne6to v .qrc file-a i toi sam vika rcc pri build)
//pri nf->save texta bi sledvalo da se obry6ta ne vyv std::string , a v utf8 , no tova dava gre6en output po nqkakva pri4ina
//pri promeni v petko10.h/.cpp trqbva da update-vam ry4no win/linux
//ideq : backlight (kato neonovite svetlini pod kolite) za note-ovete ,za da se razgrani4at nqkolko oblasti ot note-file-a vizualno (vsqka sys svoi cvqt)
//pri dobavqneto na novi promenlivi (izmqna na strukturata na notes file-ovete) da slagam if(!has_key()){set default;skip get_key()}
//pri dyljina okolo 81 (v realni koordinati) texturata se precakva -- trqbva o6te testvane na teq granici
//pri promqna na vectora pointeri kym obekti v nego so4at kym s4upeni obekti
//politikata za semicolon-i (to4ki zapetai) e ,4e v teksta na linkovete ne sa pozvoleni (obry6tat se na ":"), a v teksta na note ne pre4at


#include <QApplication>
#include <QSplashScreen>
#include <QFont>
#include <QTextCodec>

#include "common.h"
#include "misliwindow.h"
#include "note.h"
#include "notefile.h"

int main(int argc, char *argv[])
{

    QApplication a(argc, argv);

    a.setOrganizationName("p10");
    a.setApplicationName("misli");

    QTextCodec::setCodecForCStrings(QTextCodec::codecForName("utf8"));
    QTextCodec::setCodecForTr(QTextCodec::codecForName("utf8"));

    QTranslator translator;
    QSettings settings;

    if(settings.contains("language")){
        if(settings.value("language").toString()!=QString("en")){
            QString qstr="misli_"+settings.value("language").toString();
            translator.load(qstr,QString(":/translations/"));
            a.installTranslator(&translator);
        }
    }

    QPixmap pixmap(":/img/icon.png");
    QSplashScreen *splash = new QSplashScreen(pixmap);
    splash->show();
    a.processEvents();

    MisliWindow msl_w(&a);

    splash->finish(&msl_w);

    return a.exec();
}

