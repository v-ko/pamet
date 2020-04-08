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
#include <QFileDialog>
#include <QFileSystemWatcher>
#include <QStandardPaths>

#include "mislidesktopgui.h"
#include "../global.h"
#include "../canvaswidget.h"

MisliDesktopGui::MisliDesktopGui(int argc, char *argv[]) :
    QApplication(argc,argv)
{
    setQuitOnLastWindowClosed(false);

    //Set some creditentials
    setOrganizationName("p10"); //this is needed for proper settings access in windows
    setApplicationName("misli");
    setApplicationVersion(MISLI_VERSION);

    //Construct the splash screen
    QSplashScreen splash(QPixmap(":/img/icon.png"));
    splash.show();

    //Ask for a language on first program start
    if(!QSettings().contains("language")){
        QWidget dummyWidget;
        QString newLanguage = QInputDialog::getItem(&dummyWidget,
                                                    tr("Set the language"),
                                                    tr("Language:/Език:"),
                                                    QStringList() << "English" << "Български", 0,
                                                    false);
        if(newLanguage == "English") setLanguage("en");
        else if(newLanguage == "Български") setLanguage("bg");
    }else{
        updateTranslator();
    }

    //Stuff to do before quitting
//    connect(this, &MisliDesktopGui::aboutToQuit, [&]{

//    });

    QStringList notesDirs;

    //------Extract the directory paths from the settings----------
    if(QSettings().contains("notes_dir")){
        notesDirs = QSettings().value("notes_dir").toStringList();
        qDebug()<<"Loading notes dirs:" <<  notesDirs;
    }

    if(notesDirs.size() != 1){
        qDebug() << "Bad notes dirs size (!=1)";
        if(notesDirs.size()>1){ //Get the firs from the old config if present
            notesDirs = QStringList(notesDirs[0]);
        }else{ // Or request a folder
            QWidget dummyWidget;
            QString storageChoice = QInputDialog::getItem(&dummyWidget,
                                                        tr("Set the storage folder"),
                                                        tr("Set the storage folder:"),
                                                        QStringList() << "Use default folder" << "Choose folder", 0,
                                                        false);
            if(storageChoice == "Use default folder"){
                notesDirs = QStringList(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation));
            }else{
                QString storageFolder = QFileDialog::getExistingDirectory(&dummyWidget,
                                                            tr("Choose a storage folder"),
                                                            tr("Choose a storage folder:"));
                if(storageFolder.isEmpty()){
                    notesDirs = QStringList(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation));
                }else{
                    notesDirs = QStringList(storageFolder);
                }
            }
        }
        QSettings().setValue("notes_dir", notesDirs);
    }

    //Construct the misli instance class
    misliLibrary = new Library(notesDirs[0]);

    misliWindow = new MisliWindow(this);
    misliWindow->showMaximized();
    if(misliLibrary->defaultNoteFile() != nullptr){
        misliWindow->openNoteFileInNewTab(misliLibrary->defaultNoteFile());
        misliWindow->ui->tabWidget->setCurrentIndex(0);
    }

    splash.finish(misliWindow);

    workerThread.start(); //Used for search results finding
}
MisliDesktopGui::~MisliDesktopGui()
{
    delete misliWindow;
    delete translator;

    workerThread.quit();
    workerThread.wait();
}

void MisliDesktopGui::updateTranslator()
{
    removeTranslator(translator);
    delete translator;

    translator = new QTranslator;

    if(language() != QString("en")){
        //Generate filename and install translator
        QString file_name = "misli_" + language();

        if( !translator->load(file_name, ":/translations/") ){
            qDebug()<<"[MisliDesktopGui::updateTranslator]Error loading the translations file.";
        }else{
            installTranslator(translator);
        }
    }

    if(misliWindow != nullptr){
        // FIX this to save the last open nf (might just be handled by the state preservation mechanism on close at some point)
//        bool showHelp = false;
//        if(misliWindow->currentCanvas()->noteFile() == misliWindow->helpNoteFile){
//            showHelp = true;
//        }
        misliWindow->deleteLater();
        misliWindow = new MisliWindow(this);
        misliWindow->showMaximized();

//        if(showHelp == true){
//            misliWindow->currentCanvas()->setNoteFile(misliWindow->helpNoteFile);
//        }
    }
}

void MisliDesktopGui::setLanguage(QString newLanguage)
{
    if(newLanguage != language()){
        QSettings().setValue("language", newLanguage);
        QSettings().sync();

        updateTranslator();
    }
}

QString MisliDesktopGui::language()
{
    return QSettings().value("language",QVariant("en")).toString();
}
