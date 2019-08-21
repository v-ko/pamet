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
#include <QFontMetrics>
#include <QRect>
#include <QPainter>
#include <QImage>
#include <QFile>
#include <QDebug>
#include <QUrl>
#include <QFileInfo>
#include <QDir>

#include "petko10.h"
#include "petko10q.h"

#include "common.h"
#include "note.h"

Note::Note(int id_, QString iniString)
{
    QString tmpString;
    QStringList linkIDStrings,linkCPxStrings, linkCPyStrings, txt_colString,bg_colString;
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

    err += q_get_value_for_key(iniString,"l_id",linkIDStrings);
    //getting the link text should be here
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
    //Process tags
    q_get_value_for_key(iniString, "tags", tags);

    if(err!=0) qDebug()<<"[Note::Note]Some of the note properties were not read correctly.Number of errors:"<<-err;
}
Note::Note(Note *nt)
{
    id = nt->id;
    text_m = nt->text_m;
    rect_m = nt->rect_m;
    timeMade = nt->timeMade;
    timeModified = nt->timeModified;
    fontSize_m = nt->fontSize_m;
    textColor_m = nt->textColor_m;
    backgroundColor_m = nt->backgroundColor_m;
    tags = nt->tags;

    commonInitFunction();
}
Note::Note()
{
    fontSize_m = 1;
    textColor_m.setRgbF(0,0,1,1);
    backgroundColor_m.setRgbF(0,0,1,0.1);
    timeMade = QDateTime::currentDateTime();
    timeModified = QDateTime::currentDateTime();
    commonInitFunction();
}
void Note::commonInitFunction()
{
    //date on which I fixed the property ... (I introduced it ~18.11.2012)
    QDateTime t_default(QDate(2013,3,8),QTime(0,0,0));
    if(!timeMade.isValid()) timeMade=t_default;
    if(!timeModified.isValid()) timeModified=t_default;

    setTextForShortening(text_m);
    checkForDefinitions();
}

Note::~Note()
{
    delete img;
}

QRectF Note::adjustTextSize(QPainter &p)
{
    int leftMargin, rightMargin, testPosition;

    //-------Init painter for the text shortening----------
    QRectF textField = textRect();
    QRectF textFieldNeeded;
    QString textCopy = textForShortening_m;

    //=========Shortening the text in the box=============
    textIsShortened = false; //assume we don't need shortening

    leftMargin = 0;
    rightMargin = textCopy.size();
    testPosition = leftMargin + ceil(float(rightMargin-leftMargin)/2);

    //-----If there's no resizing needed (common case , that's why it's on the top)--------
    textFieldNeeded = p.boundingRect(textField, Qt::TextWordWrap | alignment() | Qt::AlignVCenter ,textCopy);
    if( (  textFieldNeeded.height() <= textField.height() ) && ( textFieldNeeded.width() <= textField.width() ) ){
        goto after_shortening;
    }
    //-----For the shorter than "..." texts (they won't get any shorter)--------------
    if(rightMargin<=3){
        goto after_shortening;
    }

    //------------Start shortening algorithm---------------------
    //Here lie 4 too many hours of debugging
    while( (rightMargin-leftMargin)!=1 ) { //until we converge the margins (the left is the length at which the text fits, the right - at which it doesn't fit)

        textCopy.resize(testPosition-3); //We know the text will be shortened, so we test with the ellipsis
        textCopy+="...";

        textFieldNeeded = p.boundingRect(textField, Qt::TextWordWrap | alignment() | Qt::AlignVCenter ,textCopy);

        if( ( textFieldNeeded.height() > textField.height() ) | ( textFieldNeeded.width() > textField.width() ) ){
            rightMargin=testPosition; //if the text doesnt fit - move max_iterator to the current position
        }else{
            leftMargin=testPosition; //if it does - bring the base iterator to the current pos
        }

        testPosition=leftMargin + ceil(float(rightMargin-leftMargin)/2); //new position for the probe_iterator - optimally in the middle of the interval
        if(testPosition<=3){
            textIsShortened = true;
            textCopy="...";
            goto after_shortening;
        }
        textCopy = textForShortening_m;
    }

    textIsShortened = true;
    textCopy.resize(leftMargin-3);
    textCopy+="...";

    after_shortening:
    setTextForDisplay(textCopy);
    return textFieldNeeded;
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
        if(addressString.startsWith(".")) addressString.remove(0,1).prepend(QDir::currentPath());
        file.setFileName(addressString);
        type = NoteType::textFile;
        if(file.open(QIODevice::ReadOnly)){
            setTextForShortening(QFileInfo(file).fileName()+":\n"+file.read(MAX_TEXT_FOR_DISPLAY_SIZE));
        }else{
            setTextForShortening( tr("Failed to open file:")+addressString);
        }
        file.close();
        return;
    }else if (text_m.startsWith(QString("define_picture_note:"))){
        addressString = q_get_text_between(text_m,':',0,MAX_URI_LENGTH); //get text between ":" and the end
        addressString = addressString.trimmed(); //remove white spaces from both sides
        if(addressString.startsWith(".")) addressString.remove(0,1).prepend(QDir::currentPath());
        setTextForShortening("");
        type = NoteType::picture;
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
void Note::drawNote(QPainter &painter)
{
    QFont font = painter.font();
    QPen pen = painter.pen();
    font.setFamily("Halvetica");
    font.setHintingPreference(QFont::PreferNoHinting);

    QRectF imageRect = rect();

    //If it's a picture note
    //Resize appropriately to fit in the note boundaries
    if( (type==NoteType::picture) && textForDisplay_m.isEmpty() ){

        if(img==NULL){
            img = new QImage(addressString);
        }

        if(img->isNull()){
            delete img;
            img = NULL;
            setTextForShortening( tr("Failed to open file:") + addressString);
            type = NoteType::normal;
        }else{

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

            QRectF projectedRect; //We use the scaled() f-n because it's configurable to a smooth transform
            projectedRect.setWidth(painter.transform().m22()*imageRect.width()); //Use the painter scaling factor
            projectedRect.setHeight(painter.transform().m22()*imageRect.height());
            painter.drawImage(imageRect, img->scaled(projectedRect.width(),projectedRect.height(),Qt::KeepAspectRatio,Qt::SmoothTransformation));
        }

    }

    //Draw the text

    //Point size uses transformations, pixel size is the same on all devices
    //So this is kind of a hack to use pointSize without the text being different size on different (by DPI) displays
    font.setPointSizeF(10000);
    QFontMetrics fm(font);
    font.setPointSizeF( ( fontSize_m *10000/float(fm.height()) )*1.552 ); //the last constant is the pixelSize/pointSize ratio of my laptop
    painter.setFont(font);

    pen.setColor( textColor_m );
    painter.setPen( pen );
    painter.setBrush( Qt::SolidPattern );
    //QRectF adjustedRect =
    adjustTextSize(painter);
    painter.drawText( textRect(), Qt::TextWordWrap | alignment() | Qt::AlignVCenter, textForDisplay_m);

    //For testing
    //painter.drawText(rect().topLeft(),QString::number(fm.height())+"'"+QString::number(fontSize_m *10000/float(fm.height())));
    //QRectF boundingRect = painter.boundingRect( textRect(), Qt::TextWordWrap | alignment() | Qt::AlignVCenter, textForDisplay_m );
    //painter.fillRect( boundingRect, QBrush( QColor(255,0,0,60)));
    //painter.fillRect( textRect() , QBrush( QColor(0,255,0,60))); //shows the probe iterator which may be for the right margin so it's normal if it's a wrong bounding box

    //Draw a border around the appropriate notes
    if( (type==NoteType::redirecting) |
        (type==NoteType::systemCall) |
        (type==NoteType::webPage) |
        (type==NoteType::textFile) )
    {
        pen.setColor(textColor_m);
        painter.setPen(pen);
        painter.setBrush(Qt::NoBrush);
        painter.drawRect(rect());
    }

    //Draw the note field
    if(type!=NoteType::picture){
        painter.fillRect(rect(),QBrush(backgroundColor_m));
    }

    //If it's selected - overpaint with yellow
    if(isSelected_m){
        painter.fillRect(rect(), QBrush(QColor(255,255,0,127)) ); //the yellow marking box
    }
}
void Note::drawLink(QPainter &painter, Link &ln)
{
    QPen pen = painter.pen();
    QColor selectedPenColor(150,150,0,255);
    QColor circleColor = backgroundColor();
    circleColor.setAlpha(60);//same as BG but transparent

    //Make the path if it's not present
    if(ln.path.isEmpty()){
        ln.path.moveTo(ln.line.p1());
        if(ln.usesControlPoint){
            ln.path.quadTo(ln.realControlPoint(),ln.line.p2());
        }else{
            ln.path.lineTo(ln.line.p2());
        }
        ln.path.translate(-ln.line.p1());
    }

    painter.setBrush(Qt::NoBrush);
    painter.save(); //pushMatrix() (not quite but ~)
        painter.translate( ln.line.p1() );
        //Draw the base line
        if(ln.isSelected){ //overpaint with yellow if it's selected
            pen.setColor( selectedPenColor );
            painter.setPen( pen );
            painter.drawPath(ln.path);
        }else{
            pen.setColor( textColor() );
            painter.setPen( pen );
            painter.drawPath(ln.path);
        }
    painter.restore();//pop matrix

    QLineF lastLineFromPath(ln.path.pointAtPercent(0.90),ln.path.pointAtPercent(1));
    //Draw the arrow head
    painter.save(); //pushMatrix() (not quite but ~)
        painter.translate( ln.line.p2() );
        painter.rotate(90-lastLineFromPath.angle());

        if(ln.isSelected){ //overpaint when selected
            pen.setColor( selectedPenColor );
            painter.setPen( pen );
            painter.drawLine(QLineF(0,0,-0.45,0.9)); //both lines for the arrow
            painter.drawLine(QLineF(0,0,0.45,0.9));
        }else{
            pen.setColor( textColor() );
            painter.setPen( pen );
            painter.drawLine(QLineF(0,0,-0.45,0.9)); //both lines for the arrow
            painter.drawLine(QLineF(0,0,0.45,0.9));
        }
    painter.restore();//pop matrix

    //Paint the control point if the link is selected
    if(ln.isSelected){
        painter.setPen(Qt::NoPen);
        painter.setBrush(circleColor);
        if(ln.usesControlPoint){
            painter.drawEllipse(ln.controlPoint,RESIZE_CIRCLE_RADIUS,RESIZE_CIRCLE_RADIUS);
        }else{
            painter.drawEllipse(ln.middleOfTheLine(),RESIZE_CIRCLE_RADIUS,RESIZE_CIRCLE_RADIUS);
        }
        painter.setPen(pen);//restore pen (because of the 'cosmetic' property that enables the matrix width transform
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
        setTextForShortening(text_m);
        checkForDefinitions();
        emit textChanged(text_m);
        emit propertiesChanged();
    }
}
void Note::changeTextAndTimestamp(QString newText)
{
    if(newText!=text_m){
        timeModified=QDateTime::currentDateTime();
        setText(newText);
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
    rect_m.setX( round(float(newRect.x())/SNAP_GRID_INTERVAL_SIZE)*SNAP_GRID_INTERVAL_SIZE );
    rect_m.setY( round(float(newRect.y())/SNAP_GRID_INTERVAL_SIZE)*SNAP_GRID_INTERVAL_SIZE );
    rect_m.setWidth( stop( round(float(newRect.width())/SNAP_GRID_INTERVAL_SIZE)*SNAP_GRID_INTERVAL_SIZE ,MIN_NOTE_A,MAX_NOTE_A) );
    rect_m.setHeight( stop(round(float(newRect.height())/SNAP_GRID_INTERVAL_SIZE)*SNAP_GRID_INTERVAL_SIZE ,MIN_NOTE_B,MAX_NOTE_B) );
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
}
void Note::setTextForDisplay(QString text_)
{
    textForDisplay_m = text_;
}
void Note::setSelected(bool value)
{
    if(value==isSelected_m) return;

    isSelected_m = value;
    emit visualChange();
}
void Note::autoSize(QPainter &painter)
{
    if(type==NoteType::picture){
        rect_m.setWidth(10);
        rect_m.setHeight(10);
        return;
    }

    adjustTextSize(painter);

    //Expand until the text fits or we hit max size
    while(textIsShortened){
        if(rect().width()>=MAX_NOTE_A && rect().height()>=MAX_NOTE_B) break;
        if(rect().width()<=MAX_NOTE_A) rect().setWidth(rect().width()+2);
        if(rect().height()<=MAX_NOTE_B) rect().setHeight(rect().height()+float(2)/A_TO_B_NOTE_SIZE_RATIO);
        adjustTextSize(painter);
    }

    //Reduce height until we overdo it
    while(true){
        int oldSize = textForDisplay_m.size();
        bool shortageBeforeResize = textIsShortened;
        if(rect().height()<=MIN_NOTE_B){break;}
        rect().setHeight(rect().height()-1);
        adjustTextSize(painter);
        //Check if we've ran out of white space to reduce (<= the text size has shrinked)
        if( (oldSize>textForDisplay_m.size()) | (shortageBeforeResize!=textIsShortened) ){
            break;
        }
    }
    rect().setHeight(rect().height()+1);
    adjustTextSize(painter); //Back to fitting in the box (textIsShortened->true)

    //Reduce width until we overdo it
    while(true){
        int oldSize = textForDisplay_m.size();
        bool shortageBeforeResize = textIsShortened;
        if(rect().width()<=MIN_NOTE_A){break;}
        rect().setWidth(rect().width()-1);
        adjustTextSize(painter);
        //Check if we've ran out of white space to reduce (<= the text size has shrinked)
        //There was a bug where for ex.: 'aaaa' shortens to 'a...' (size==4) , so a check on shorting is needed
        if( (oldSize>textForDisplay_m.size()) | (shortageBeforeResize!=textIsShortened) ){
            break;
        }
    }

    rect().setWidth(rect().width()+1);
    setRect(rect()); //Align to grid. Should refactor the above to use a tmpRect

    adjustTextSize(painter);
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

    iniStringStream<<"tags=";
    for(QString tag: tags){
        //Remove ";"s from the text to avoid breaking the ini standard
        tag.replace(";",":");

        //Save the text
        iniStringStream<<tag<<";";
    }
    iniStringStream<<'\n';

    return iniString;
}

Qt::AlignmentFlag Note::alignment()
{
    if(text_m.contains("\n")){//if there's more than one row
        return Qt::AlignLeft;
    }else{
        return Qt::AlignHCenter;
    }
}

QRectF Note::textRect()
{
    QRectF txtRect = rect();
    txtRect.setLeft(rect().left() + NOTE_SPACING);
    txtRect.setTop(rect().top() + NOTE_SPACING );
    txtRect.setHeight(rect().height() - 2*NOTE_SPACING + 1);//dirty fix because boundingRect returns a bigger rect
    txtRect.setWidth(rect().width() - 2*NOTE_SPACING);
    txtRect.moveTop(txtRect.top() - fontSize_m*0.1); // FIXME use fontMetrics to make this correction exact

    return txtRect;
}
