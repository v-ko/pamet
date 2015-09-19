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

#ifndef MISLIDESKTOPGUI_H
#define MISLIDESKTOPGUI_H

#include <QApplication>
#include <QTranslator>
#include <QSettings>
#include <QSplashScreen>
#include <QFutureWatcher>
#include <QThread>

#include "misliwindow.h"

class MisliDesktopGui : public QApplication
{
    Q_OBJECT

    Q_PROPERTY(bool firstProgramStart READ firstProgramStart WRITE setFirstProgramStart)
    Q_PROPERTY(int failedStarts READ failedStarts WRITE setFailedStarts)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY languageChanged)

public:
    //Functions
    MisliDesktopGui(int argc, char *argv[]);
    ~MisliDesktopGui();

    //Properties
    bool firstProgramStart();
    int failedStarts();
    QString language();

    //Variables
    MisliWindow *misliWindow;
    MisliInstance *misliInstance;
    QSettings *settings;
    QSplashScreen *splash;
    QThread workerThread;
    bool clearSettingsOnExit;

signals:
    void languageChanged(QString newLanguage);

private:
    QTranslator *translator;

public slots:
    //Properties
    void setFirstProgramStart(bool);
    void setFailedStarts(int);
    void setLanguage(QString);
    void updateTranslator();

    //Other
    void showWarningMessage(QString message);
    void stuffToDoBeforeQuitting();
};

#endif // MISLIDESKTOPGUI_H
