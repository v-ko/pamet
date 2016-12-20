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
#include <QUrl>
#include <QFileInfo>

#include "petko10.h"
#include "petko10q.h"

#include "common.h"
#include "note.h"

Note::Note(int id_, QString iniString, bool bufferImage_)
{
    QString tmpString;
    QStringList linkIDStrings,linkCPxStrings, linkCPyStrings, txt_colString,bg_colString;
    int err=0;
    float x,y,a,b;

    id = id_;
    bufferImage = bufferImage_;

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

    err += q_get_value_for_key(iniString,"l_id",linkIDStrings);
    q_get_value_for_key(iniString,"l_CP_x",linkCPxStrings); //Those two are optional
    q_get_value_for_key(iniString,"l_CP_y",linkCPyStrings);
    int iter = 0;
    for(QString linkString: linkIDStrings){ //getting the links in the notes
        if( linkIDStrings.size()==linkCPxStrings.size() &&
                linkIDStrings.size()==linkCPyStrings.size())
        {//There are control points saved
            addLink( Link( linkString.toInt(), QPointF(linkCPxStrings[iter].toFloat(),linkCPyStrings[iter].toFloat()) ) );
        }else{ //There are no (or corrupted) control points saved
            addLink( Link(linkString.toInt()) );
        }
        iter++;
    }

    if(err!=0) qDebug()<<"[Note::Note]Some of the note properties were not read correctly.Number of errors:"<<-err;
}
Note::Note(int id_,QString text_,QRectF rect_,float font_size_,QDateTime t_made_,QDateTime t_mod_,QColor txt_col_,QColor bg_col_, bool bufferImage_)
{
    id = id_;
    bufferImage = bufferImage_;
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
    autoSizing = false;
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
    if( !bufferImage ) return;

    int base_it,max_it,probe_it; //iterators for the shortening algorythm

    //-------Init painter for the text shortening----------
    QRectF textField(0,0,rect().width()*FONT_TRANSFORM_FACTOR - 2*NOTE_SPACING*FONT_TRANSFORM_FACTOR,
                     rect().height()*FONT_TRANSFORM_FACTOR - 2*NOTE_SPACING*FONT_TRANSFORM_FACTOR);
    QRectF textFieldNeeded;
    QString textCopy = textForShortening_m;

    QFont font("Halvetica");
    font.setPixelSize(fontSize_m*FONT_TRANSFORM_FACTOR);

    QPainter p;
    if(!p.begin(img)){
        qDebug()<<"[Note::adjustTextSize]Failed to initialize painter.";
    }
    p.setFont(font);

    //=========Shortening the text in the box=============
    textIsShortened = false; //assume we don't need shortening

    p.setFont(font);

    base_it = 0;
    max_it = textCopy.size();
    probe_it=base_it + ceil(float(max_it-base_it)/2);

    //-----If there's no resizing needed (common case , that's why it's in front)--------

    textFieldNeeded = p.boundingRect(textField, Qt::TextWordWrap | alignment() ,textCopy);
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
        textFieldNeeded = p.boundingRect(textField, Qt::TextWordWrap | alignment() ,textCopy); //get the bounding box for the text (with probe length)

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
void Note::checkTextForFileDefinition()
{
    QFile file;

    if (text_m.startsWith(QString("define_text_file_note:"))){
        addressString = q_get_text_between(text_m,':',0,MAX_URI_LENGTH); //get text between ":" and the end
        addressString = addressString.trimmed(); //remove white spaces from both sides
        file.setFileName(addressString);
        type = NoteType::textFile;
        if(file.open(QIODevice::ReadOnly)){
            setTextForShortening(QFileInfo(file).fileName()+":\n"+file.read(MAX_TEXT_FOR_DISPLAY_SIZE));
        }else{
            setTextForShortening( tr("Failed to open file."));
        }
        file.close();
        return;
    }else if (text_m.startsWith(QString("define_picture_note:"))){
        addressString = q_get_text_between(text_m,':',0,MAX_URI_LENGTH); //get text between ":" and the end
        addressString=addressString.trimmed(); //remove white spaces from both sides
        type = NoteType::picture;
        setTextForShortening("");
    }
}
void Note::checkTextForSystemCallDefinition()
{
    if (text_m.startsWith(QString("define_system_call_note:"))){
        addressString=q_get_text_between(text_m,':',0,MAX_URI_LENGTH); //get text between ":" and the end
        addressString=addressString.trimmed(); //remove white spaces from both sides
        type=NoteType::systemCall;
        setTextForShortening(addressString);
    }
}
void Note::checkTextForWebPageDefinition()
{
    if (text_m.startsWith(QString("define_web_page_note:"))){
        QString iniString = q_get_text_between(text_m,':',0,2*MAX_URI_LENGTH+20); //URL+name+some identifiers ~= 4100 chars
        int err = q_get_value_for_key(iniString,"url",addressString);
        addressString=addressString.trimmed(); //remove white spaces from both sides
        QString name;
        err+=q_get_value_for_key(iniString,"name",name);

        if(err==0 && QUrl(addressString).isValid()){
            type = NoteType::webPage;
            setTextForShortening(name);
        }else{
            if(err==0){
                setTextForShortening(tr("URL is invalid"));
            }
        }
    }
}
void Note::drawNote(QPainter *painter)
{
    QFont font = painter->font();
    //font.set;
    QPen pen = painter->pen();
    font.setFamily("Sans");

    QRectF imageRect = rect();

    //If it's a picture note - resize appropriately to fit in the note boundaries
    if( (type==NoteType::picture) && textForDisplay_m.isEmpty() ){
        float frame_ratio,pixmap_ratio;
        frame_ratio = rect().width()/rect().height();
        pixmap_ratio = float(img->width())/float(img->height());

        if( frame_ratio > pixmap_ratio ){
            //if the width for the note frame is proportionally bigger than the pictures width
            //we resize the note using the height of the frame and a calculated width
            imageRect.setWidth(imageRect.height()*pixmap_ratio);
            imageRect.moveCenter(rect().center());
        }else if( frame_ratio < pixmap_ratio ){
            //we resize the note using the width of the frame and a calculated height
            imageRect.setHeight(imageRect.width()/pixmap_ratio);
            imageRect.moveCenter(rect().center());
        }


        //Draw image if there is one FIXME
    }

    //Draw the text
    font.setPointSizeF( fontSize_m );
    painter->setFont(font);

    pen.setColor( textColor_m );
    painter->setPen( pen );
    painter->setBrush(Qt::SolidPattern);
    QRectF textRect = rect();
    textRect.moveTop(textRect.top() - fontSize_m*0.2); // Adjust text so it is properly centered
    painter->drawText( textRect, Qt::TextWordWrap | alignment() | Qt::AlignVCenter, textForDisplay_m);

    //For testing
    //QRectF boundingRect = painter->boundingRect( rect_m, Qt::TextWordWrap | alignment(), textForDisplay_m );
    //painter->fillRect( boundingRect, QBrush( QColor(255,0,0,60)));

    //Draw a border around the appropriate notes
    if( (type==NoteType::redirecting) |
        (type==NoteType::systemCall) |
        (type==NoteType::webPage) |
        (type==NoteType::textFile) )
    {
        pen.setColor(textColor_m);
        painter->setPen(pen);
        painter->setBrush(Qt::NoBrush);
        painter->drawRect(rect());
    }

    //Draw the note field
    painter->fillRect(rect(),QBrush(backgroundColor_m));

    //If it's selected - overpaint with yellow
    if(isSelected_m){
        painter->fillRect(rect(), QBrush(QColor(255,255,0,127)) ); //the yellow marking box
    }
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
        qDebug()<<"[Note::setFontSize]Font size out of range. Note text:"<<text_m;
    }else{
        fontSize_m = newFontSize;

        emit visualChange();
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
        qDebug()<<"[Note::setColors]Invalid color. Note text:"<<text_m;
    }else{
        textColor_m = newTextColor;
        backgroundColor_m = newBackgroundColor;

        emit visualChange();
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
    emit visualChange();
}
void Note::setSelected(bool value)
{
    if(value==isSelected_m) return;

    isSelected_m = value;
    emit visualChange();
}
void Note::autoSize()
{
    if(type==NoteType::picture){
        rect_m.setWidth(10);
        rect_m.setHeight(10);
        emit visualChange();
        return;
    }

    autoSizing = true;

    //Expand until the text fits or we hit max size
    while(textIsShortened){
        if(rect().width()>=MAX_NOTE_A && rect().height()>=MAX_NOTE_B) break;
        if(rect().width()<=MAX_NOTE_A) rect().setWidth(rect().width()+2);
        if(rect().height()<=MAX_NOTE_B) rect().setHeight(rect().height()+float(2)/A_TO_B_NOTE_SIZE_RATIO);
        adjustTextSize();
    }

    //Reduce height until we overdo it
    while(true){
        int oldSize = textForDisplay_m.size();
        bool shortageBeforeResize = textIsShortened;
        if(rect().height()<=MIN_NOTE_B){break;}
        rect().setHeight(rect().height()-1);
        adjustTextSize();
        //Check if we've ran out of white space to reduce (<= the text size has shrinked)
        if( (oldSize>textForDisplay_m.size()) | (shortageBeforeResize!=textIsShortened) ){
            break;
        }
    }
    rect().setHeight(rect().height()+1);
    adjustTextSize(); //Back to fitting in the box (textIsShortened->true)

    while(true){
        int oldSize = textForDisplay_m.size();
        bool shortageBeforeResize = textIsShortened;
        if(rect().width()<=MIN_NOTE_A){break;}
        rect().setWidth(rect().width()-1);
        adjustTextSize();
        //Check if we've ran out of white space to reduce (<= the text size has shrinked)
        //There was a bug where for ex.: 'aaaa' shortens to 'a...' (size==4) , so a check on shorting is needed
        if( (oldSize>textForDisplay_m.size()) | (shortageBeforeResize!=textIsShortened) ){
            break;
        }
    }

    rect().setWidth(rect().width()+1);

    adjustTextSize();

    autoSizing = false;
    emit visualChange();
}

void Note::checkForDefinitions()
{
    type=NoteType::normal; //assuming the note isn't special
    checkTextForNoteFileLink();
    checkTextForFileDefinition();
    checkTextForSystemCallDefinition();
    checkTextForWebPageDefinition();
}

bool Note::addLink(Link newLink)
{
    //Check if a link with that ID already exists
    for(Link &ln: outlinks){
        if(ln.id==newLink.id){
            return false;
        }
    }
    outlinks.push_back(newLink);
    emit linksChanged();
    return true;
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
    txt.replace("\n","\\n");
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
        ln.text.replace(";",":");

        //Save the text
        iniStringStream<<ln.text<<";";
    }
    iniStringStream<<'\n';
    iniStringStream<<"l_CP_x=";
    for(Link ln: outlinks){
        if(ln.usesControlPoint){
            iniStringStream<<ln.controlPoint.x()<<";";
        }else{//Safest thing to do - even if the links are not initialized the p1 is always on the line
            iniStringStream<<ln.line.p1().x()<<";";
        }
    }
    iniStringStream<<'\n';
    iniStringStream<<"l_CP_y=";
    for(Link ln: outlinks){
        if(ln.usesControlPoint){
            iniStringStream<<ln.controlPoint.y()<<";";
        }else{
            iniStringStream<<ln.line.p1().y()<<";";
        }
    }
    iniStringStream<<'\n';

    return iniString;
}

Qt::AlignmentFlag Note::alignment()
{
    if(text_m.contains("\n")){//if there's more than one row
        return Qt::AlignLeft;
    }else{
        return Qt::AlignCenter;
    }
}
