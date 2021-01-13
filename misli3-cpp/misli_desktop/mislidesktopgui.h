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

public:
    //Functions
    MisliDesktopGui(int argc, char *argv[]);
    ~MisliDesktopGui();

    //Properties
    QString language();

    //Variables
    MisliWindow * misliWindow = nullptr;
    Library * misliLibrary;
    QThread workerThread;
    bool clearSettingsOnExit = false;

private:
    QTranslator *translator = nullptr;

public slots:
    //Properties
    void setLanguage(QString);
    void updateTranslator();
};

#endif // MISLIDESKTOPGUI_H
