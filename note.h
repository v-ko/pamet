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
class MisliDir;

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
    Q_PROPERTY(QString text READ text WRITE setText NOTIFY textChanged)
    Q_PROPERTY(float fontSize READ fontSize WRITE setFontSize NOTIFY fontSizeChanged)
    Q_PROPERTY(QRectF rect READ rect WRITE setRect NOTIFY rectChanged)
    //------Properties needed only for the program----------------
    Q_PROPERTY(QString textForShortening READ textForShortening WRITE setTextForShortening NOTIFY textForShorteningChanged)
    Q_PROPERTY(QString textForDisplay READ textForDisplay WRITE setTextForDisplay NOTIFY textForDisplayChanged)
    Q_PROPERTY(bool isSelected READ isSelected WRITE setSelected NOTIFY selectedChanged)

public:
    //Functions
    Note(int id_, QString iniString, bool bufferImage_);
    Note(int id_, QString text_, QRectF rect_, float font_size_, QDateTime t_made_, QDateTime t_mod_, QColor txt_col_, QColor bg_col_, bool bufferImage_);
    void commonInitFunction();
    ~Note();

    void storeCoordinatesBeforeMove();

    void checkTextForNoteFileLink(); //gets called from MisliDir only
    void checkTextForFileDefinition();
    void checkTextForSystemCallDefinition();
    void checkTextForWebPageDefinition();

    void autoSize();
    QString propertiesInIniString();

    //Accessing properties
    QString text();
    QRectF &rect();
    QString textForShortening();
    QString textForDisplay();
    bool isSelected();

    QColor textColor();
    QColor backgroundColor();

    //Calculated properties
    float fontSize();
    Qt::AlignmentFlag alignment();

    //------Variables that are read/written on the file------------
    int id;

    QRectF rect_m;
    QString text_m;

    float fontSize_m;
    QDateTime timeMade,timeModified;
    QColor textColor_m,backgroundColor_m; //text and background colors
    QList<Link> outlinks;

    //------Variables needed only for the program----------------
    QString textForShortening_m;
    QString textForDisplay_m; //this gets drawn in the note
    QString addressString;

    float xBeforeMove,yBeforeMove;

    QImage *img;


    NoteType type;

    bool isSelected_m;
    bool textIsShortened;
    bool bufferImage;
    bool autoSizing;

signals:
    //Property changes
    void textChanged(QString);
    void fontSizeChanged(float);
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
    void setText(QString);
    void setFontSize(float);
    void setRect(QRectF newRect);
    void setColors(QColor newTextColor, QColor newBackgroundColor);
    void setTextForShortening(QString);
    void setTextForDisplay(QString text_);
    void setSelected(bool value);

    //Other
    void checkForDefinitions();
    void adjustTextSize();
    void drawNote(QPainter* painter);

    bool addLink(Link newLink);
    void removeLink(int linkId);
};

#endif // NOTE_H
