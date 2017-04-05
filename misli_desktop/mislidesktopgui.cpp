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
#include <QInputDialog>
#include <QFileSystemWatcher>

#include "mislidesktopgui.h"
#include "../common.h"
#include "../canvas.h"

MisliDesktopGui::MisliDesktopGui(int argc, char *argv[]) :
    QApplication(argc,argv)
{
    QWidget dummyWidget; //so I can use the static functions below
    misliWindow = NULL;
    translator = NULL;
    clearSettingsOnExit = false;

    int user_reply;

    //Set some creditentials
    setQuitOnLastWindowClosed(false);
    setOrganizationName("p10"); //this is needed for proper settings access in windows
    setApplicationName("misli");
    setApplicationVersion("2.0.0");

    //Construct the splash screen
    splash = new QSplashScreen(QPixmap(":/img/icon.png"));
    splash->show();

    //Init the settings
    settings = new QSettings;

    //Check if there's a series of failed starts and suggest clearing the settings
    if(failedStarts()>=2){
        user_reply = QMessageBox::question(&dummyWidget,tr("Warning"),tr("There have been two unsuccessful starts of the program. Clearing the program settings will probably solve the issue . Persistent program crashes are mostly caused by corrupted notefiles , so you can try to manually narrow out the problematic notefile (remove the notefiles from the work directories one by one). The last one edited is probably the problem (you can try to correct it manually with a text editor to avoid loss of data).\n Do you want to clear the settings?"));

        if(user_reply==QMessageBox::Ok){ //if the user pressed Ok
            settings->clear();
            settings->sync();
            exit(0);
        }
    }
    //Assume we won't start successfully , if we do - the value gets -1-ed on close
    setFailedStarts(failedStarts()+1);

    if(firstProgramStart()){
        QString newLanguage = QInputDialog::getItem(&dummyWidget,tr("Set the language"),tr("Language:/Език:"),QStringList()<<"English"<<"Български",0,false);
        if(newLanguage=="English") setLanguage("en");
        if(newLanguage=="Български") setLanguage("bg");
    }

    updateTranslator();

    //Construct the misli instance class
    misliInstance = new MisliInstance();

    //Connections
    connect(this,SIGNAL(languageChanged(QString)),this,SLOT(updateTranslator()));
    connect(this,SIGNAL(aboutToQuit()),this,SLOT(stuffToDoBeforeQuitting()));

    //Start worker thread as soon as the main loop starts (so that we first show the splash screen and then start work)
    workerThread.start();
    misliInstance->loadStoredDirs();
    misliWindow = new MisliWindow(this);
    splash->finish(misliWindow);
    misliWindow->showMaximized();
}
MisliDesktopGui::~MisliDesktopGui()
{
    delete misliWindow;
    delete settings;
    delete translator;

    workerThread.quit();
    workerThread.wait();
}

void MisliDesktopGui::updateTranslator()
{
    //processEvents();
    removeTranslator(translator);
    delete translator;

    translator = new QTranslator;

    if(language()!=QString("en")){
        //Generate filename and install translator
        QString file_name = "misli_"+language();
        if( !translator->load(file_name,QString(":/translations/")) ){
            qDebug()<<"[MisliDesktopGui::updateTranslator]Error loading the translations file.";
        }else{
            installTranslator(translator);
        }
    }

    if(misliWindow!=NULL){
        bool showHelp = false;
        if(misliWindow->canvas->noteFile()==misliWindow->helpNoteFile){
            showHelp = true;
        }
        misliWindow->deleteLater();
        misliWindow = new MisliWindow(this);
        misliWindow->showMaximized();

        if(showHelp==true){
            misliWindow->canvas->setNoteFile(misliWindow->helpNoteFile);
        }
    }
}

bool MisliDesktopGui::firstProgramStart()
{
    return settings->value("first_program_start",QVariant(true)).toBool();
}

int MisliDesktopGui::failedStarts()
{
    return settings->value("failed_starts",QVariant(0)).toInt();
}

QString MisliDesktopGui::language()
{
    return settings->value("language",QVariant("en")).toString();
}

void MisliDesktopGui::setFirstProgramStart(bool value)
{
    settings->setValue("first_program_start",QVariant(value));
    settings->sync();
}
void MisliDesktopGui::setFailedStarts(int value)
{
    settings->setValue("failed_starts",QVariant(value));
    settings->sync();
}
void MisliDesktopGui::setLanguage(QString newLanguage)
{
    if(newLanguage!=language()){
        settings->setValue("language",newLanguage);
        settings->sync();

        emit languageChanged(newLanguage);
    }
}

void MisliDesktopGui::showWarningMessage(QString message)
{
    QMessageBox msg;
    msg.setText(message);
    msg.exec();
}
void MisliDesktopGui::stuffToDoBeforeQuitting()
{
    if(clearSettingsOnExit){
        settings->clear();
        settings->sync();
    }else{
        setFailedStarts(0);
        setFirstProgramStart(false);
    }
}
