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

#include <QFont>
#include <QRect>
#include <QPainter>
#include <QImage>
#include <QFile>
#include <QDebug>

#include "petko10.h"
#include "petko10q.h"

#include "common.h"
#include "note.h"

Note::Note(int id_, QString iniString)
{
    QString tmpString;
    QStringList linkStrings,txt_colString,bg_colString;
    int err=0;
    float x,y,a,b;

    id = id_;

    err += q_get_value_for_key(iniString,"txt",text_m);
        text_m.replace(QString("\\n"),QString("\n"));

    err += q_get_value_for_key(iniString,"x",x);
    err += q_get_value_for_key(iniString,"y",y);
    err += q_get_value_for_key(iniString,"a",a);
        a = stop(a,MIN_NOTE_A,MAX_NOTE_A); //values should be btw 1-1000
    err += q_get_value_for_key(iniString,"b",b);
        b = stop(b,MIN_NOTE_B,MAX_NOTE_B);
    setRect(QRectF(x,y,a,b));

    err += q_get_value_for_key(iniString,"font_size",fontSize_m);
    if(q_get_value_for_key(iniString,"t_made",tmpString)==0){
        timeMade=timeMade.fromString(tmpString,"d.M.yyyy H:m:s");
    }else timeMade = timeMade.currentDateTime();
    if(q_get_value_for_key(iniString,"t_mod",tmpString)==0){
        timeModified=timeModified.fromString(tmpString,"d.M.yyyy H:m:s");
    }else timeModified = timeMade.currentDateTime();
    if(q_get_value_for_key(iniString,"txt_col",txt_colString)==-1){
        txt_colString.clear();
        txt_colString.push_back("0");
        txt_colString.push_back("0");
        txt_colString.push_back("1");
        txt_colString.push_back("1");
    }
    textColor_m.setRgbF(txt_colString[0].toFloat(),
            txt_colString[1].toFloat(),
            txt_colString[2].toFloat(),
            txt_colString[3].toFloat());

    if(q_get_value_for_key(iniString,"bg_col",bg_colString)==-1){
        bg_colString.clear();
        bg_colString.push_back("0");
        bg_colString.push_back("0");
        bg_colString.push_back("1");
        bg_colString.push_back("0.1");
    }
    backgroundColor_m.setRgbF(bg_colString[0].toFloat(),
            bg_colString[1].toFloat(),
            bg_colString[2].toFloat(),
            bg_colString[3].toFloat());

    commonInitFunction();

    setTextForShortening(text_m); //if I call setText there is some complication with the empty strings
    checkForDefinitions();

    err += q_get_value_for_key(iniString,"l_id",linkStrings);
    for(QString linkString: linkStrings){ //getting the links in the notes
        addLink(linkString.toInt());
    }

    if(err!=0) qDebug()<<"[Note::Note]Some of the note properties were not read correctly.Number of errors:"<<-err;
}
Note::Note(int id_,QString text_,QRectF rect_,float font_size_,QDateTime t_made_,QDateTime t_mod_,QColor txt_col_,QColor bg_col_)
{
    id = id_;
    text_m = text_;
    rect_m = rect_;
    timeMade = t_made_;
    timeModified = t_mod_;
    fontSize_m = font_size_;
    textColor_m = txt_col_;
    backgroundColor_m = bg_col_;

    commonInitFunction();

    setTextForShortening(text_); //if I call setText there is some complication with the empty strings
    checkForDefinitions();
}
void Note::commonInitFunction()
{
    //date on which I fixed the property ... (I introduced it ~18.11.2012)
    QDateTime t_default(QDate(2013,3,8),QTime(0,0,0));
    if(!timeMade.isValid()){timeMade=t_default;}
    if(!timeModified.isValid()){timeModified=t_default;}

    isSelected_m=false;
    img = new QImage(1,1,QImage::Format_ARGB32_Premultiplied);//so we have a dummy pixmap for the first init
    textIsShortened=false;
    bufferImage = true;
    type = NoteType::normal;
}

Note::~Note()
{
    delete img;
}

void Note::storeCoordinatesBeforeMove()
{
    xBeforeMove=rect_m.x();
    yBeforeMove=rect_m.y();
}

void Note::adjustTextSize()
{
    int base_it,max_it,probe_it; //iterators for the shortening algorythm

    //-------Init painter for the text shortening----------
    QRectF textField(0,0,rect().width()*FONT_TRANSFORM_FACTOR,rect().height()*FONT_TRANSFORM_FACTOR),textFieldNeeded;
    QString textCopy = textForShortening_m;

    QFont font("Halvetica");
    font.setPixelSize(fontSize_m*FONT_TRANSFORM_FACTOR);

    QPainter p;
    if(!p.begin(img)){
        qDebug()<<"[Note::adjustTextSize]Failed to initialize painter.";
    }
    p.setFont(font);

    //------Determine alignment---------------
    if(textCopy.contains("\n")){//if there's more than one row
        alignment = Qt::AlignLeft;
    }else{
        alignment = Qt::AlignCenter;
    }

    //=========Shortening the text in the box=============
    textIsShortened = false; //assume we don't need shortening

    p.setFont(font);

    base_it = 0;
    max_it = textCopy.size();
    probe_it=base_it + ceil(float(max_it-base_it)/2);

    //-----If there's no resizing needed (common case , that's why it's in front)--------

    textFieldNeeded = p.boundingRect(textField, Qt::TextWordWrap | alignment ,textCopy);
    if( (  textFieldNeeded.height() <= textField.height() ) && ( textFieldNeeded.width() <= textField.width() ) ){
        goto after_shortening;
    }
    //-----For the shorter than "..." texts (they won't get any shorter)--------------
    if(max_it<=3){
        goto after_shortening;
    }

    //------------Start shortening algorithm---------------------
    while((max_it-base_it)!=1) { //until we pin-point the needed length with accuracy 1

        textCopy.resize(probe_it); //we resize to the probe iterator
        textFieldNeeded = p.boundingRect(textField, Qt::TextWordWrap | alignment ,textCopy); //get the bounding box for the text (with probe length)

        if( ( textFieldNeeded.height() > textField.height() ) | ( textFieldNeeded.width() > textField.width() ) ){//if the needed box is bigger than the size of the note
            max_it=probe_it; //if the text doesnt fit - move max_iterator to the current position
        }else{
            base_it=probe_it; //if it does - bring the base iterator to the current pos
        }

        probe_it=base_it + ceil(float(max_it-base_it)/2); //new position for the probe_iterator - optimally in the middle of the dead space
        textCopy = textForShortening_m;
    }

    textIsShortened = true;
    textCopy.resize(max_it-3);
    textCopy+="...";

    after_shortening:
    p.end();
    setTextForDisplay(textCopy);
}

void Note::checkTextForNoteFileLink() //there's an argument , because search inits the notes out of their dir and still needs that function (the actual linking functionality is not needed then)
{
    if (text_m.startsWith(QString("this_note_points_to:"))){
        addressString = q_get_text_between(text_m,':',0,200); //get text between ":" and the end
        addressString = addressString.trimmed(); //remove white spaces from both sides
        type = NoteType::redirecting;
        setTextForShortening(addressString);
    }
}
void Note::checkForFileDefinitions()
{
    QFile file;

    if (text_m.startsWith(QString("define_text_file_note:"))){
        addressString = q_get_text_between(text_m,':',0,200); //get text between ":" and the end
        addressString = addressString.trimmed(); //remove white spaces from both sides
        file.setFileName(addressString);
        type = NoteType::textFile;
        if(file.open(QIODevice::ReadOnly)){
            setTextForShortening(file.read(MAX_TEXT_FOR_DISPLAY_SIZE));
        }else{
            setTextForShortening( tr("Failed to open file."));
        }
        file.close();
        return;
    }else if (text_m.startsWith(QString("define_picture_note:"))){
        addressString = q_get_text_between(text_m,':',0,200); //get text between ":" and the end
        addressString=addressString.trimmed(); //remove white spaces from both sides
        type = NoteType::picture;
        setTextForShortening("");
    }
}
void Note::checkTextForSystemCallDefinition()
{
    if (text_m.startsWith(QString("define_system_call_note:"))){
        addressString=q_get_text_between(text_m,':',0,200); //get text between ":" and the end
        addressString=addressString.trimmed(); //remove white spaces from both sides
        type=NoteType::systemCall;
        setTextForShortening(addressString);
    }
}
void Note::drawPixmap()
{
    if(!bufferImage) return;

    float pixm_real_size_x = rect().width()*FONT_TRANSFORM_FACTOR; //pixmap real size (inflated to have better quality on zoom)
    float pixm_real_size_y = rect().height()*FONT_TRANSFORM_FACTOR;

    if(type==NoteType::picture){
        delete img;
        img = new QImage(addressString);

        if( !img->isNull() ) {
            return;
        }else {
            type=NoteType::normal;
            setTextForShortening("Not a valid picture.");
        }
    }

    delete img;
    img = new QImage(pixm_real_size_x,pixm_real_size_y,QImage::Format_ARGB32_Premultiplied);
    img->fill(Qt::transparent);

    QFont font("Halvetica");
    font.setPixelSize(fontSize_m*FONT_TRANSFORM_FACTOR);
    font.setStyleStrategy(QFont::PreferAntialias); //style aliasing

    QPainter p;
    if(!p.begin(img)){
        qDebug()<<"[Note::drawPixmap]Failed to initialize painter.";
    }
    p.setFont(font);
    p.setRenderHint(QPainter::TextAntialiasing);

    //Draw the note field
    p.fillRect(0,0,pixm_real_size_x,pixm_real_size_y,QBrush(backgroundColor_m));

    //Draw the text
    p.setPen(textColor_m); //set color
    p.setBrush(Qt::SolidPattern); //set fill style
    p.drawText(QRectF(NOTE_SPACING*FONT_TRANSFORM_FACTOR,NOTE_SPACING*FONT_TRANSFORM_FACTOR,rect().width()*FONT_TRANSFORM_FACTOR,rect().height()*FONT_TRANSFORM_FACTOR),Qt::TextWordWrap | alignment,textForDisplay_m);

    p.end();
    emit visualChange();
}

QString Note::text()
{
    return text_m;
}

float Note::fontSize()
{
    return fontSize_m;
}
QRectF& Note::rect()
{
    return rect_m;
    //Dont invoke save here - there's too many operations using the rectangle that don't actually imply saving
}

QColor Note::textColor()
{
    return textColor_m;
}
QColor Note::backgroundColor()
{
    return backgroundColor_m;
}
QString Note::textForShortening()
{
    return textForShortening_m;
}
QString Note::textForDisplay()
{
    return textForDisplay_m;
}
bool Note::isSelected()
{
    return isSelected_m;
}

void Note::setText(QString newText)
{
    if(newText!=text_m){
        text_m = newText;
        timeModified=QDateTime::currentDateTime();
        emit textChanged(text_m);
        emit propertiesChanged();

        setTextForShortening(text_m);
        checkForDefinitions();
    }
}
void Note::setFontSize(float newFontSize)
{
    if( 0>newFontSize && newFontSize>MAX_FONT_SIZE){
        qDebug()<<"[Note::setFontSize]Font size out of range.";
    }else{
        fontSize_m = newFontSize;
        drawPixmap();
        emit fontSizeChanged(newFontSize);
        emit propertiesChanged();
    }
}
void Note::setRect(QRectF newRect)
{
    rect_m = newRect;
}
void Note::setColors(QColor newTextColor, QColor newBackgroundColor)
{
    if(!newTextColor.isValid() | !newBackgroundColor.isValid()){
        qDebug()<<"[Note::setColors]Invalid color.";
    }else{
        textColor_m = newTextColor;
        backgroundColor_m = newBackgroundColor;
        drawPixmap();
        emit propertiesChanged();
    }
}
void Note::setTextForShortening(QString text_)
{
    //Be within the size limit
    if(text_.size()>MAX_TEXT_FOR_DISPLAY_SIZE) textForShortening_m = text_.left(MAX_TEXT_FOR_DISPLAY_SIZE);
    else textForShortening_m=text_;

    adjustTextSize();
}
void Note::setTextForDisplay(QString text_)
{
    textForDisplay_m = text_;
    drawPixmap();
}
void Note::setSelected(bool value)
{
    if(value==isSelected_m) return;

    isSelected_m = value;
    drawPixmap();
}
void Note::autoSize()
{
    while(textIsShortened){ //Expand until the text fits or we hit max size
        if(rect().width()<=MAX_NOTE_A) rect().setWidth(rect().width()+2);
        if(rect().height()<=MAX_NOTE_B) rect().setHeight(rect().height()+float(2)/A_TO_B_NOTE_SIZE_RATIO);

        adjustTextSize();
        if(rect().width()>=MAX_NOTE_A && rect().height()>=MAX_NOTE_B) break;
    }
    while(!textIsShortened){ //Reduce height if there's empty space (a few really long lines)
        if(rect().height()<=MIN_NOTE_B){break;}
        rect().setHeight(rect().height()-1);
        adjustTextSize();
    }
    rect().setHeight(rect().height()+1);
    adjustTextSize(); //Back to fitting in the box (textIsShortened->true)

    while(!textIsShortened){ //Reduce width to fit (many short lines)
        if(rect().width()<=MIN_NOTE_A){break;}
        rect().setWidth(rect().width()-1);
        adjustTextSize();
    }
    rect().setWidth(rect().width()+1);

    adjustTextSize();
    drawPixmap();
}

void Note::checkForDefinitions()
{
    type=NoteType::normal; //assuming the note isn't special
    checkTextForNoteFileLink();
    checkForFileDefinitions();
    checkTextForSystemCallDefinition();
}

void Note::addLink(int linkId)
{
    outlinks.push_back(Link(linkId));
    emit linksChanged();
}
void Note::removeLink(int linkId)
{
    QMutableListIterator<Link> iterator(outlinks);
    while(iterator.hasNext()){
        if(iterator.next().id==linkId) iterator.remove();
    }
    emit linksChanged();
}
QString Note::propertiesInIniString()
{
    QString iniString;
    QTextStream iniStringStream(&iniString);

    iniStringStream<<"["<<id<<"]"<<'\n';
    QString txt=text_m;
    txt.replace("\n","\\n");//(QString("\n"),QString("\\n")); FIXME
    iniStringStream<<"txt="<<txt<<'\n';
    iniStringStream<<"x="<<rect_m.x()<<'\n';
    iniStringStream<<"y="<<rect_m.y()<<'\n';
    iniStringStream<<"z="<<0<<'\n';
    iniStringStream<<"a="<<rect_m.width()<<'\n';
    iniStringStream<<"b="<<rect_m.height()<<'\n';
    iniStringStream<<"font_size="<<fontSize_m<<'\n';
    iniStringStream<<"t_made="<<timeMade.toString("d.M.yyyy H:m:s")<<'\n';
    iniStringStream<<"t_mod="<<timeModified.toString("d.M.yyyy H:m:s")<<'\n';
    iniStringStream<<"txt_col="<<textColor_m.redF()<<";"<<textColor_m.greenF()<<";"<<textColor_m.blueF()<<";"<<textColor_m.alphaF()<<'\n';
    iniStringStream<<"bg_col="<<backgroundColor_m.redF()<<";"<<backgroundColor_m.greenF()<<";"<<backgroundColor_m.blueF()<<";"<<backgroundColor_m.alphaF()<<'\n';

    iniStringStream<<"l_id=";
    for(Link ln: outlinks){
        iniStringStream<<ln.id<<";";
    }
    iniStringStream<<'\n';

    iniStringStream<<"l_txt=";
    for(Link ln: outlinks){
        //Remove ";"s from the text to avoid breaking the ini standard
        ln.text.replace(";",":"); //(QString(";"),QString(":")) FIXME

        //Save the text
        iniStringStream<<ln.text<<";";
    }
    iniStringStream<<'\n';

    return iniString;
}
