/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <QMessageBox>
#include <QFileSystemWatcher>

#include "mislidesktopgui.h"

MisliDesktopGui::MisliDesktopGui(int argc, char *argv[]) :
    QApplication(argc,argv)
{
    QMessageBox msg;
    QPixmap pixmap(":/img/icon.png");
    int successful_start=0,user_reply;

    setApplicationName("misli");

    //-----------Construct the splash screen--------------------------
    splash = new QSplashScreen(pixmap);
    splash->show();
    qDebug()<<"Constructed the splash screen.";


    //========Load the language from settings and setup the translator=======
    if(settings.contains("language")){
        language=settings.value("language").toString();
        if(language.size()!=0){
            if(language!=QString("en")){
                QString qstr="misli_"+settings.value("language").toString();
                translator.load(qstr,QString(":/translations/"));
                installTranslator(&translator);
            }
        }else{
            goto setup_language;
        }
    }else{
        setup_language:
        first_program_start=true;
        settings.setValue("language",QVariant("en"));
        settings.sync();
        language="en";
    }

    qDebug()<<"MisliDesktopGui:Retrieved the language from settings"<<settings.value("language").toString();
    
    //=========Check if there's a series of failed starts and suggest clearing the settings=========
    if(settings.contains("successful_start")){
        successful_start=settings.value("successful_start").toInt();
        qDebug()<<"MisliDesktopGui:Retrieved successful_start from settings: "<<successful_start;
        if(successful_start<=-2){ //if there's been more than two closes that are not accounted for
            msg.setText(QObject::tr("There have been two unsuccessful starts of the program. Clearing the program settings will probably solve the issue . Persistent program crashes are mostly caused by corrupted notefiles , so you can try to manually narrow out the problematic notefile (remove the notefiles from the work directories one by one). The last one edited is probably the problem (you can try to correct it manually with a text editor to avoid loss of data).\n To clear the settings press OK . To continue with starting up the program press Cancel."));
            msg.setStandardButtons(QMessageBox::Ok|QMessageBox::Cancel);
            msg.setDefaultButton(QMessageBox::Ok);
            msg.setIcon(QMessageBox::Warning);
            user_reply=msg.exec();
            if(user_reply==QMessageBox::Ok){ //if the user pressed Ok
                qDebug()<<"MisliDesktopGui:User chose to clear settings and exit upon prompt.";
                settings.clear();
                settings.sync();
                exit(0);
            }
        }
    }
    //-----------Prep the successful_start variable-------------------
    successful_start--; //assume we won't start successfully , if we do - the value gets +1-ed on close
    settings.setValue("successful_start",QVariant(successful_start));
    settings.sync();
    qDebug()<<"MisliDesktopGui:successful_start lowered to: "<<settings.value("successful_start").toInt();

    //==================Construct the misli instance class and search class===============================
    notes_search = new NotesSearch;
    notes_search->moveToThread(&workerThread);
    misli_i = new MisliInstance(this);
    misli_i->moveToThread(&workerThread);

    connect(&workerThread,SIGNAL(started()), misli_i,SLOT(load_all_dirs()));
    QObject::connect(misli_i,SIGNAL(load_all_dirs_finished()),this,SLOT(start_GUI()));

    //==================Construct the windows for the application==============================
    misli_w = new MisliWindow(this);
    dir_w = new GetDirDialogue(misli_i);
    edit_w = new EditNoteDialogue(misli_i);
    newnf_w = new NewNFDialogue(misli_w);
    note_w = new NoteDetailsWindow();
    qDebug()<<"Constructed all window objects.Starting worker thread.";
    workerThread.start();
}
MisliDesktopGui::~MisliDesktopGui()
{\
    delete misli_i;
    delete misli_w;
    delete dir_w;
    delete newnf_w;
    delete edit_w;
    delete note_w;
    delete splash;
    delete notes_search;

    workerThread.quit();
    workerThread.wait();
}

void MisliDesktopGui::start_GUI()
{
    qDebug()<<"starting GUI";
    if( misli_i->notes_rdy() ){
        if(first_program_start){ //if it's the first dir we're making go to the help file
            misli_i->curr_misli_dir()->set_current_note_file("HelpNoteFile");
            first_program_start=false;
        }
        misli_w->showMaximized();
        splash->hide(); //end the splash screen
    }
}
