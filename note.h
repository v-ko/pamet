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

#ifndef NOTE_H
#define NOTE_H

#include <QDate>
#include <QImage>
#include <QObject>
#include <QRectF>
#include <QColor>

#include "link.h"

class NoteFile;
class Library;

enum class NoteType {
    normal,
    redirecting,
    textFile,
    picture,
    systemCall,
    webPage
};

class Note : public QObject
{    
Q_OBJECT

    //------Properties that are read/written on the file------------
    Q_PROPERTY(QString text READ text WRITE changeText NOTIFY textChanged)
    Q_PROPERTY(QRectF rect READ rect WRITE setRect NOTIFY rectChanged)
    //------Properties needed only for the program----------------
    Q_PROPERTY(QString textForDisplay READ textForDisplay WRITE setTextForDisplay NOTIFY textForDisplayChanged)
    Q_PROPERTY(bool isSelected READ isSelected WRITE setSelected NOTIFY selectedChanged)

public:
    //Functions
    Note(Note *nt);
    Note(int id_, QString text);
    static Note * fromJsonObject(QJsonObject json);
    static Note * fromIniString(int id_, QString iniString);
    ~Note();

    void checkTextForNoteFileLink(); //gets called from Library only
    void checkTextForFileDefinition();
    void checkTextForSystemCallDefinition();
    void checkTextForWebPageDefinition();

    void autoSize(QPainter &painter);
    QJsonObject toJsonObject();
    QString toIniString();
    QRectF textRect();

    //Accessing properties
    QString text();
    QRectF &rect();
    QString textForDisplay();
    bool isSelected();

    QColor textColor();
    QColor backgroundColor();

    //Calculated properties
    Qt::AlignmentFlag alignment();

    //------Variables that are read/written on the file------------
    int id;

    QRectF rect_m;
    QString text_m;

    double fontSize = 1;
    QDateTime timeMade = QDateTime::currentDateTime();
    QDateTime timeModified = QDateTime::currentDateTime();
    QColor textColor_m = QColor::fromRgbF(0,0,1,1);
    QColor backgroundColor_m = QColor::fromRgbF(0,0,1,0.1);
    QList<Link> outlinks;
    QStringList tags;

    //------Variables needed only for the program----------------
    QString textForShortening;
    QString textForDisplay_m; //this gets drawn in the note
    QString addressString;

    QPointF posBeforeMove;

    QImage *img = nullptr;


    NoteType type = NoteType::normal;

    bool isSelected_m = false;
    bool textIsShortened = false;
    bool requestAutoSize = false;

signals:
    //Property changes
    void textChanged(QString);
    void rectChanged(QRectF);
    void textForShorteningChanged(QString);
    void textForDisplayChanged(QString);
    void selectedChanged(bool);

    //Other
    void propertiesChanged();
    void visualChange();
    void linksChanged();

public slots:
    //Set properties
    void changeText(QString);
    void changeTextAndTimestamp(QString);
    void setRect(QRectF newRect);
    void setColors(QColor newTextColor, QColor newBackgroundColor);
    void setTextForDisplay(QString text_);
    void setSelected(bool value);

    //Other
    void checkForDefinitions();
    QRectF adjustTextSize(QPainter &p);
    void drawNote(QPainter &painter);
    void drawLink(QPainter &painter, Link &ln);

    bool addLink(Link newLink);
    void removeLink(int linkId);
};

#endif // NOTE_H
