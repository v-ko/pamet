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

#include <QMessageBox>
#include <QFileSystemWatcher>

#include "mislidesktopgui.h"
#include "../common.h"

MisliDesktopGui::MisliDesktopGui(int argc, char *argv[]) :
    QApplication(argc,argv)
{
    QMessageBox msg;
    QPixmap pixmap(":/img/icon.png");
    int successful_start,user_reply;

    //Some pointer safeties
    misli_i=NULL;
    misli_w=NULL;
    dir_w=NULL;
    newnf_w=NULL;
    edit_w=NULL;
    note_details_w=NULL;
    splash=NULL;
    notes_search=NULL;

    //Set some creditentials
    setOrganizationName("p10"); //this is needed for proper settings access in windows
    setApplicationName("misli");
    setApplicationVersion("1.2.0");

    //Init the settings
    settings = new QSettings(this);

    //Construct the splash screen
    splash = new QSplashScreen(pixmap);
    splash->show();
    qDebug()<<"Constructed the splash screen.";

    //Check for the first_start flag
    if(!settings->contains("first_start")){
        qDebug()<<"No key 'first_start' found - assuming it's the first program start";
        first_program_start=true;
        settings->setValue("first_start",QVariant(true));
        settings->sync();

    }else{
        first_program_start=false;
    }

    //Check if there's a series of failed starts and suggest clearing the settings
    if(settings->contains("successful_start")){

        successful_start=settings->value("successful_start").toInt();
        qDebug()<<"MisliDesktopGui:Retrieved successful_start from settings: "<<successful_start;

        if(successful_start<=-2){ //if there's been more than two closes that are not accounted for

            msg.setText(QObject::tr("There have been two unsuccessful starts of the program. Clearing the program settings will probably solve the issue . Persistent program crashes are mostly caused by corrupted notefiles , so you can try to manually narrow out the problematic notefile (remove the notefiles from the work directories one by one). The last one edited is probably the problem (you can try to correct it manually with a text editor to avoid loss of data).\n To clear the settings press OK . To continue with starting up the program press Cancel."));
            msg.setStandardButtons(QMessageBox::Ok|QMessageBox::Cancel);
            msg.setDefaultButton(QMessageBox::Ok);
            msg.setIcon(QMessageBox::Warning);
            user_reply=msg.exec();

            if(user_reply==QMessageBox::Ok){ //if the user pressed Ok
                qDebug()<<"MisliDesktopGui:User chose to clear settings and exit upon prompt.";
                settings->clear();
                settings->sync();
                //qDebug()<<"Settings SYNC status: "<<settings->status();
                exit(0);
            }
        }
    }else{
        successful_start = 0;
    }



    //Load the language from settings and setup the translator
    if( settings->contains("language") ){

        qDebug()<<"MisliDesktopGui:Retrieved the language from settings"<<language;
        language = settings->value("language").toString();

        if( !language.isEmpty() ){
            if(language!=QString("en")){
                //Generate filename and install translator
                QString file_name = "misli_"+settings->value("language").toString();
                translator.load(file_name,QString(":/translations/"));
                installTranslator(&translator);
            }
        }else{ //if the 'language' is empty
            qDebug()<<"Setting 'language' to 'en'.";
            settings->setValue("language",QVariant("en"));
            settings->sync();
            language = "en";
        }
    }else{
        qDebug()<<"No key 'language' found";
        qDebug()<<"Setting 'language' to 'en'.";
        settings->setValue("language",QVariant("en"));
        settings->sync();
        language = "en";
    }

    float default_eye_z = settings->value("eye_z",QVariant(0)).toFloat();
    qDebug()<<"[MisliDesktopGUI]From settings: eye_z = "<<default_eye_z;

    if( default_eye_z<=0 ){
        settings->setValue("eye_z",QVariant(INITIAL_EYE_Z));
        settings->sync();
    }
    
    //Assume we won't start successfully , if we do - the value gets +1-ed on close
    successful_start--;
    settings->setValue("successful_start",QVariant(successful_start));
    settings->sync();
    qDebug()<<"MisliDesktopGui:successful_start lowered to: "<<settings->value("successful_start").toInt();

    //Construct the windows for the application
    edit_w = new EditNoteDialogue(this);
    misli_w = new MisliWindow(this);
    dir_w = new GetDirDialogue(this);

    newnf_w = new NewNFDialogue(this);
    note_details_w = new NoteDetailsWindow();
    qDebug()<<"Constructed all window objects.";

    //Construct the misli instance class and search class
    notes_search = new NotesSearch;
    notes_search->moveToThread(&workerThread);
    misli_i = new MisliInstance(this);
    misli_i->moveToThread(&workerThread);

    //Connections
    connect(&workerThread,SIGNAL(started()), misli_i,SLOT(load_all_dirs()));

    connect(misli_i,SIGNAL(notes_dir_changed()),misli_w,SLOT(recheck_for_dirs()));
    connect(misli_i,SIGNAL(load_all_dirs_finished()),misli_w,SLOT(recheck_for_dirs()));

    connect(misli_i,SIGNAL(notes_dir_added(QString)),misli_w,SLOT(add_menu_entry_for_dir(QString)));
    connect(notes_search,SIGNAL(search_complete(QString)),misli_w,SLOT(display_results(QString)));

    //Start worker thread
    workerThread.start();
    qDebug()<<"Started worker thread.";
}
MisliDesktopGui::~MisliDesktopGui()
{
    delete misli_i;
    delete misli_w;
    delete dir_w;
    delete newnf_w;
    delete edit_w;
    delete note_details_w;
    delete splash;
    delete notes_search;

    workerThread.quit();
    workerThread.wait();
}

void MisliDesktopGui::show_warning_message(QString message)
{
    QMessageBox msg;
    msg.setText(message);
    msg.exec();
}
