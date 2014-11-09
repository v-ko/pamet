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

#include <vector>

#include <QDate>
#include <QImage>

#include "link.h"

class NoteFile;
class MisliDir;

enum class NoteType {
    normal,
    redirecting,
    textFile,
    picture,
    systemCall
};

class Note{

    //------Properties that are read/written on the file------------
    Q_PROPERTY(int id READ id WRITE setId NOTIFY idChanged)

    Q_PROPERTY(float x READ x WRITE setX NOTIFY xChanged)
    Q_PROPERTY(float y READ y WRITE sety NOTIFY yChanged)
    Q_PROPERTY(float z READ z WRITE setz NOTIFY zChanged)
    Q_PROPERTY(float a READ a WRITE seta NOTIFY aChanged)
    Q_PROPERTY(float b READ b WRITE setb NOTIFY bChanged)

    Q_PROPERTY(QString text READ text WRITE setText NOTIFY textChanged)
    Q_PROPERTY(float fontSize READ fontSize WRITE setFontSize NOTIFY fontSizeChanged)
    Q_PROPERTY(QDateTime timeMade READ timeMade WRITE setTimeMade NOTIFY timeMadeChanged)
    Q_PROPERTY(QDateTime timeModified READ timeModified WRITE setTimeModified NOTIFY timeModifiedChanged)
    Q_PROPERTY(QColor textColor READ textColor WRITE setTextColor NOTIFY textColorChanged)
    Q_PROPERTY(QColor bgColor READ bgColor WRITE setBgColor NOTIFY bgColorChanged)

    //------Properties needed only for the program----------------
    Q_PROPERTY(QString textForShortening READ textForShortening WRITE setTextForShortening NOTIFY textForShorteningChanged)
    Q_PROPERTY(QString textForDisplay READ textForDisplay WRITE setTextForDisplay NOTIFY textForDisplayChanged)
    Q_PROPERTY(QString addressString READ addressString WRITE setAddressString NOTIFY addressStringChanged)

    Q_PROPERTY(float xBeforeMove READ xBeforeMove WRITE setXBeforeMove NOTIFY xBeforeMoveChanged)
    Q_PROPERTY(float yBeforeMove READ yBeforeMove WRITE setYBeforeMove NOTIFY yBeforeMoveChanged)

    Q_PROPERTY(float realX READ realX WRITE setRealX NOTIFY realXChanged)
    Q_PROPERTY(float realY READ realY WRITE setRealY NOTIFY realYChanged)
    Q_PROPERTY(float realPixmapWidth READ realPixmapWidth WRITE setRealPixmapWidth NOTIFY realPixmapWidthChanged)
    Q_PROPERTY(float realPixmapHeight READ realPixmapHeight WRITE setRealPixmapHeight NOTIFY realPixmapHeightChanged)

    Q_PROPERTY(QString nfName READ nfName WRITE setNfName NOTIFY nfNameChanged)
    Q_PROPERTY(MisliDir *misliDir READ misliDir WRITE setMisliDir NOTIFY misliDirChanged)
    Q_PROPERTY(QImage image READ image WRITE setImage NOTIFY imageChanged)
    Q_PROPERTY(Qt::AlignmentFlag alignment READ alignment WRITE setAlignment NOTIFY alignmentChanged)
    Q_PROPERTY(NoteType type READ type WRITE setType NOTIFY typeChanged)
    Q_PROPERTY(bool selected READ selected WRITE setSelected NOTIFY selectedChanged)
    Q_PROPERTY(bool hasMoreThanOneRow READ hasMoreThanOneRow WRITE setHasMoreThanOneRow NOTIFY hasMoreThanOneRowChanged)
    Q_PROPERTY(bool textIsShortened READ textIsShortened WRITE setTextIsShortened NOTIFY textIsShortenedChanged)
    Q_PROPERTY(bool autoSizingNow READ autoSizingNow WRITE setAutoSizingNow NOTIFY autoSizingNowChanged)


public:
    //Constructor/destructor
    Note();
    ~Note();

    //Accessing properties
    int id();

    float x();
    float y();
    float z();
    float a();
    float b();

    QString text();
    float fontSize();
    QDateTime timeMade();
    QDateTime timeModified();
    QColor textColor();
    QColor bgColor();
    QString textForShortening();
    QString textForDisplay();
    QString addressString();

    float xBeforeMove();
    float yBeforeMove();

    float realX();
    float realY();
    float realPixmapWidth();
    float realPixmapHeight();

    QString nfName();
    MisliDir *misliDir();
    QImage image();
    Qt::AlignmentFlag alignment();
    NoteType type();
    bool selected();
    bool hasMoreThanOneRow();
    bool textIsShortened();
    bool autoSizingNow();

    //Functions
    //int calculate_coordinates();
    void storeCoordinatesBeforeMove();
    int adjustTextSize();
    void checkTextForLinks(MisliDir *md);
    int checkForFileDefinitions();
    int check_text_for_system_call_definition();
    int draw_pixmap();
    int init();
    void auto_size();
    void center_eye_on_me();

    int init_links();
    int correct_links();
    int link_to_selected();

    int add_link(Link *ln);

    int delete_inlink_for_id(int);
    int delete_link(int); //no need for one that accepts Link* !

public slots:
    //Set properties
    void setId(int);

    void setX(float);
    void setY(float);
    void setZ(float);
    void setA(float);
    void setB(float);

    void setText(QString);
    void setFontSize(float);
    void setTimeMade(QDateTime);
    void setTimeModified(QDateTime);
    void setTextColor(QColor);
    void setBgColor(QColor);
    void setTextForShortening(QString);
    void setTextForDisplay(QString);
    void setAddressString(QString);

    void setXBeforeMove(float);
    void setYBeforeMove(float);

    void updateRealX(float);
    void updateRealY(float);
    void updateRealPixmapWidth(float);
    void updateRealPixmapHeight(float);

    void setNfName(QString);
    void setMisliDir(MisliDir *);
    void setImage(QImage);
    void setAlignment(Qt::AlignmentFlag);
    void setType(NoteType);
    void setSelected(bool);
    void setHasMoreThanOneRow(bool);
    void setTextIsShortened(bool);
    void setAutoSizingNow(bool);

signals:
    //Property changes
    int idChanged(int);

    void xChanged(float);
    void yChanged(float);
    void zChanged(float);
    void aChanged(float);
    void bChanged(float);

    void textChanged(QString);
    void fontSizeChanged(float);
    void timeMadeChanged(QDateTime);
    void timeModifiedChanged(QDateTime);
    void textColorChanged(QColor);
    void bgColorChanged(QColor);
    void textForShorteningChanged(QString);
    void textForDisplayChanged(QString);
    void addressStringChanged(QString);

    void xBeforeMoveChanged(float);
    void yBeforeMoveChanged(float);

    void realXChanged(float);
    void realYChanged(float);
    void realPixmapWidthChanged(float);
    void realPixmapHeightChanged(float);

    void nfNameChanged(QString);
    void misliDirChanged(MisliDir *);
    void imageChanged(QImage);
    void alignmentChanged(Qt::AlignmentFlag);
    void typeChanged(NoteType);
    void selectedChanged(bool);
    void hasMoreThanOneRowChanged(bool);
    void textIsShortenedChanged(bool);
    void autoSizingNowChanged(bool);


private:
    //Properties' internal variables
    int id_m;

    float x_m;
    float y_m;
    float z_m;
    float a_m;
    float b_m;

    QString text_m;
    float fontSize_m;
    QDateTime timeMade_m;
    QDateTime timeModified_m;
    QColor textColor_m;
    QColor bgColor_m;
    QString textForShortening_m;
    QString textForDisplay_m;
    QString addressString_m;

    float xBeforeMove_m;
    float yBeforeMove_m;

    float realX_m;
    float realY_m;

    float realX_m;
    float realY_m;
    float realPixmapWidth_m;
    float realPixmapHeight_m;

    QString nfName_m;
    MisliDir *misliDir_m;
    QImage image_m;
    Qt::AlignmentFlag alignment_m;
    NoteType type_m;
    bool selected_m;
    bool hasMoreThanOneRow_m;
    bool textIsShortened_m;
    bool autoSizingNow_m;

    /*/Nadolo e old stuff, t.e. toq file trqbva da e gotov
public:
    //------Variables that are read/written on the file------------
    int id;

    float x,y,z;//coordinates
    float a, b; //width and height of the box

    QString text;

    float font_size;
    QDateTime t_made,t_mod;
    float txt_col[4],bg_col[4]; //text and background colors
    std::vector<Link> outlink;
    std::vector<int> inlink;

    //------Variables needed only for the program----------------
    QString text_for_shortening;
    QString text_for_display; //this gets drawn in the note
    QString address_string;

    float move_orig_x,move_orig_y,rx,ry;
    float pixm_real_size_x; //pixmap real size
    float pixm_real_size_y;

    QString nf_name;
    MisliDir *misli_dir;

    QImage *img;
    Qt::AlignmentFlag alignment;

    int type; //1=redirecting , 0=normal

    bool selected;
    bool has_more_than_one_row;
    bool text_is_shortened;
    bool auto_sizing_now;

    */

};
typedef std::vector<Note*> NotesVector;


#endif // NOTE_H
