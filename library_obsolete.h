///*  This file is part of Misli.

//    Misli is free software: you can redistribute it and/or modify
//    it under the terms of the GNU General Public License as published by
//    the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.

//    Misli is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU General Public License for more details.

//    You should have received a copy of the GNU General Public License
//    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
//*/

//#ifndef MISLIINSTANCE_H
//#define MISLIINSTANCE_H

//#include <QSettings>
//#include <QtDebug>

//#include "mislidir.h"

//class MisliDesktopGui;
//class MisliWindow;

//class MisliInstance : public QObject
//{
//    Q_OBJECT

//public:
//    //Functions
//    MisliInstance();
//    ~MisliInstance();

//    Library *addDir(QString path);
//    Library *loadDir(QString path);
//    void removeDir(Library *dir);
//    void unloadDir(Library *dir);

//    //Properties
//    QList<Library*> misliDirs();

//    //Variables
//    QSettings settings;
//    QString fileStoragePath;

//signals:
//    void misliDirsChanged();

//public slots:
//    void loadStoredDirs();
//    void saveDirsToSettings();

//private:
//    QList<Library*> misliDirs_m;
//};

//#endif // MISLIINSTANCE_H
