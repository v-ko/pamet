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
    setQuitOnLastWindowClosed(false);

    //Set some creditentials
    setOrganizationName("p10"); //this is needed for proper settings access in windows
    setApplicationName("misli");
    setApplicationVersion("3.0.0");

    //Construct the splash screen
    QSplashScreen splash(QPixmap(":/img/icon.png"));
    splash.show();

    //Init the settings
    settings = new QSettings;

    //Assume we won't start successfully , if we do - the value gets -1-ed on close
    setFailedStarts(failedStarts()+1);

    //Ask for a language on first program start
    if(!settings->contains("language")){
        QWidget dummyWidget;
        QString newLanguage = QInputDialog::getItem(&dummyWidget,tr("Set the language"),tr("Language:/Език:"),QStringList()<<"English"<<"Български",0,false);
        if(newLanguage=="English") setLanguage("en");
        if(newLanguage=="Български") setLanguage("bg");
    }
    updateTranslator();

    //Stuff to do before quitting
    connect(this, &MisliDesktopGui::aboutToQuit, [&]{
        if(clearSettingsOnExit){
            settings->clear();
            settings->sync();
        }else{
            setFailedStarts(0);
        }
    });


    //Construct the misli instance class
    misliInstance = new MisliInstance();
    //Start worker thread as soon as the main loop starts
    //(so that we first show the splash screen and then start work)
    misliInstance->loadStoredDirs();
    misliWindow = new MisliWindow(this);
    splash.finish(misliWindow);
    misliWindow->showMaximized();

    workerThread.start(); //Used for search results finding
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

    if(misliWindow != NULL){
        bool showHelp = false;
        if(misliWindow->currentCanvas_m->noteFile() == misliWindow->helpNoteFile){
            showHelp = true;
        }
        misliWindow->deleteLater();
        misliWindow = new MisliWindow(this);
        misliWindow->showMaximized();

        if(showHelp == true){
            misliWindow->currentCanvas_m->setNoteFile(misliWindow->helpNoteFile);
        }
    }
}

int MisliDesktopGui::failedStarts()
{
    return settings->value("failed_starts",QVariant(0)).toInt();
}

QString MisliDesktopGui::language()
{
    return settings->value("language",QVariant("en")).toString();
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

        updateTranslator();
    }
}

void MisliDesktopGui::showWarningMessage(QString message)
{
    QMessageBox msg;
    msg.setText(message);
    msg.exec();
}
