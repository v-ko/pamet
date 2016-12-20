#include "timeline.h"
#include <QDebug>
#include <limits>
#include <QDateTime>
#include <QDate>
#include <QTime>
#include <QWheelEvent>
#include <QLayout>

#include "timelinewidget.h"
#include "misliwindow.h"
#include "ui_timelinewidget.h"
#include "../common.h"

Timeline::Timeline(TimelineWidget *timelineWidget_) :
    QWidget(timelineWidget_),
    slider(Qt::Horizontal, this)
{
    //UI stuff
    setMouseTracking(true);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    baselinePositionCoefficient = 0.25;
    slider.setGeometry(0, baselineY(), rect().width(), 10);
    slider.setMaximum( rect().width() );
    slider.hide();

    //Other
    timelineWidget = timelineWidget_;
    viewportSizeInMSecs = 3*days;
    positionInMSecs = QDateTime::currentDateTime().toMSecsSinceEpoch();

    //Visual change on new notes
    connect(&archiveModule.noteFile, SIGNAL(visualChange()), this, SLOT(update()));
}

float Timeline::scaleToPixels(qint64 miliseconds)
{
    return miliseconds*( double(rect().width())/double(viewportSizeInMSecs) );
}

float Timeline::scaleToSeconds(qint64 pixels)
{
    return pixels*( double(viewportSizeInMSecs)/double(rect().width()) );
}

void Timeline::drawDelimiter(QPainter *painter, qint64 delimiterInMSecs, float lineHeight)
{
    qint64 leftViewportEdge = positionInMSecs - viewportSizeInMSecs/2;
    qint64 offsetInMSecs = delimiterInMSecs - leftViewportEdge;
    float offset = scaleToPixels(offsetInMSecs);
    float y1 = baselineY() - lineHeight/2;
    float y2 = baselineY() + lineHeight/2;

    QLineF line(offset, y1, offset, y2);
    painter->drawLine(line);
}

void Timeline::paintEvent(QPaintEvent *)
{
    //Init the painter
    QPainter painter;
    if(!painter.begin((this))){
        qDebug()<<"[Canvas::Canvas]Failed to initialize painter.";
    }
    painter.setRenderHint(QPainter::Antialiasing); //better antialiasing
    painter.setRenderHint(QPainter::TextAntialiasing);
    painter.fillRect(0,0,width(),height(),QColor(255,255,255,255)); //clear background
    QFont font;
    QPen watermarkTextPen( QColor(0,0,0,60) );
    float opacity = 1;

    //Test text + current time
    painter.drawText(1,15, "positionInSecs:"+QString::number(positionInMSecs)+
                     ",viewportSizeInSecs:"+QString::number(viewportSizeInMSecs) );

    //Draw base line
    painter.setPen(Qt::black);
    painter.drawLine( 0, baselineY(), rect().width(), baselineY() );

    //Draw a line to mark the current moment
    painter.setPen(Qt::green);
    drawDelimiter(&painter, QDateTime::currentDateTime().toMSecsSinceEpoch(), 40);

    //Draw day delimiters
    const qint64 daysFirstUpperLimit = 60*days;
    const qint64 daysSecondUpperLimit = 90*days;

    if( viewportSizeInMSecs>daysFirstUpperLimit && viewportSizeInMSecs<daysSecondUpperLimit ){
        opacity = double(daysSecondUpperLimit-viewportSizeInMSecs)/double(daysSecondUpperLimit - daysFirstUpperLimit);
    }

    if( viewportSizeInMSecs<daysSecondUpperLimit){

        //Setup painter
        painter.setOpacity(opacity);

        //Prepare first delimeter
        QDateTime dt = QDateTime::fromMSecsSinceEpoch( leftEdgeInMSecs() ); //get DateTime of the left edge
        dt.setTime(QTime(0,0,0,0));
        int delimeterIndex = 0;
        qint64 delimeterPosition = dt.toMSecsSinceEpoch();

        //Draw and increment for all elements
        while(delimeterPosition<(positionInMSecs + viewportSizeInMSecs/2))
        {
            //Draw delimeters
            painter.setPen(Qt::black);
            drawDelimiter(&painter, delimeterPosition, scaleToPixels( float(1*days)/10) );
            //Draw text
            QRectF textField;
            textField.setWidth( scaleToPixels(days) );
            textField.setHeight( textField.width()/10 );
            textField.moveBottomLeft( QPointF( scaleToPixels(delimeterPosition-positionInMSecs+viewportSizeInMSecs/2), baselineY()) );
            font.setPointSizeF(textField.height()*0.8);
            painter.setFont(font);
            painter.setPen( watermarkTextPen );
            painter.drawText( textField, Qt::AlignCenter, dt.toString("d,dddd"));

            //Increment
            delimeterIndex++;
            dt = dt.addDays(1);
            delimeterPosition = dt.toMSecsSinceEpoch();
        }
    }

    //Draw month delimiters
    const qint64 monthsFirstLowerLimit = 9*days;
    const qint64 monthsSecondLowerLimit = 45*days;
    const qint64 monthsFirstUpperLimit = 24*months;
    const qint64 monthsSecondUpperLimit = 36*months;

    if(viewportSizeInMSecs>monthsFirstLowerLimit && viewportSizeInMSecs<monthsSecondLowerLimit){
        opacity = double(viewportSizeInMSecs-monthsFirstLowerLimit)/double(monthsSecondLowerLimit-monthsFirstLowerLimit);
    }else if(viewportSizeInMSecs>monthsSecondLowerLimit && viewportSizeInMSecs<monthsFirstUpperLimit){
        opacity = 1;
    }else if(viewportSizeInMSecs>monthsFirstUpperLimit && viewportSizeInMSecs<monthsSecondUpperLimit){
        opacity = double(monthsSecondUpperLimit - viewportSizeInMSecs)/double(monthsSecondUpperLimit-monthsFirstUpperLimit);
    }

    if( viewportSizeInMSecs>monthsFirstLowerLimit && viewportSizeInMSecs<monthsSecondUpperLimit){
        //Setup painter
        painter.setOpacity(opacity);

        //Prepare first delimeter
        QDateTime dt = QDateTime::fromMSecsSinceEpoch(positionInMSecs - viewportSizeInMSecs/2); //get DateTime of the left edge
        dt.setTime(QTime(0,0,0,0));
        dt.setDate( QDate(dt.date().year(),dt.date().month(),1)); //set the day to 1
        int delimeterIndex = 0;
        qint64 delimeterPosition = dt.toMSecsSinceEpoch();

        //Draw and increment for all elements
        while(delimeterPosition<(positionInMSecs + viewportSizeInMSecs/2))
        {
            //Draw delimeters
            painter.setPen(Qt::red);
            drawDelimiter(&painter, delimeterPosition, scaleToPixels( float(months)/10) );

            //Draw text
            QRectF textField;
            textField.setWidth( scaleToPixels(months) );
            textField.setHeight( textField.width()/10 );
            textField.moveBottomLeft( QPointF( scaleToPixels(delimeterPosition-positionInMSecs+viewportSizeInMSecs/2), baselineY()) );
            font.setPointSizeF(textField.height()*0.8);
            painter.setFont(font);
            painter.setPen( watermarkTextPen );
            painter.drawText( textField, Qt::AlignCenter, dt.toString("MMMM"));

            //Increment
            delimeterIndex++;
            dt = dt.addMonths(1);
            delimeterPosition = dt.toMSecsSinceEpoch();
        }
    }

    //Draw year delimiters
    const qint64 yearsFirstLowerLimit = 8*months;
    const qint64 yearsSecondLowerLimit = 16*months;
    const qint64 yearsFirstUpperLimit = 80*years;
    const qint64 yearsSecondUpperLimit = 100*years;

    if(viewportSizeInMSecs>yearsFirstLowerLimit && viewportSizeInMSecs<yearsSecondLowerLimit){
        opacity = double(viewportSizeInMSecs-yearsFirstLowerLimit)/double(yearsSecondLowerLimit-yearsFirstLowerLimit);
    }else if(viewportSizeInMSecs>yearsSecondLowerLimit && viewportSizeInMSecs<yearsFirstUpperLimit){
        opacity = 1;
    }else if(viewportSizeInMSecs>yearsFirstUpperLimit && viewportSizeInMSecs<yearsSecondUpperLimit){
        opacity = double(yearsSecondUpperLimit - viewportSizeInMSecs)/double(yearsSecondUpperLimit-yearsFirstUpperLimit);
    }

    if( viewportSizeInMSecs>yearsFirstLowerLimit && viewportSizeInMSecs<yearsSecondUpperLimit){
        //Setup painter
        painter.setOpacity(opacity);

        //Prepare first delimeter
        QDateTime dt = QDateTime::fromMSecsSinceEpoch(positionInMSecs - viewportSizeInMSecs/2); //get DateTime of the left edge
        dt.setTime(QTime(0,0,0,0));
        dt.setDate( QDate(dt.date().year(),1,1));
        int delimeterIndex = 0;
        qint64 delimeterPosition = dt.toMSecsSinceEpoch();

        //Draw and increment for all elements
        while(delimeterPosition<(positionInMSecs + viewportSizeInMSecs/2))
        {
            //Draw delimeters
            painter.setPen(Qt::blue);
            drawDelimiter(&painter, delimeterPosition, scaleToPixels( float(years)/10) );

            //Draw text
            QRectF textField;
            textField.setWidth( scaleToPixels(years) );
            textField.setHeight( textField.width()/10 );
            textField.moveBottomLeft( QPointF( scaleToPixels(delimeterPosition-positionInMSecs+viewportSizeInMSecs/2), baselineY()) );
            font.setPointSizeF(textField.height()*0.8);
            painter.setFont(font);
            painter.setPen( watermarkTextPen );
            painter.drawText( textField, Qt::AlignCenter, dt.toString("yyyy"));

            //Increment
            delimeterIndex++;
            dt = dt.addYears(1);
            delimeterPosition = dt.toMSecsSinceEpoch();
        }
    }

    //Draw all notes
    for(Note *nt: notes){
        if( abs(positionInMSecs - nt->timeMade.toMSecsSinceEpoch())<(viewportSizeInMSecs/2) ){
            painter.drawImage( QPointF(scaleToPixels(nt->timeMade.toMSecsSinceEpoch()-leftEdgeInMSecs()),baselineY()),
                              nt->img->scaled( scaleToPixels(nt->rect().width()*days/30),
                                               scaleToPixels(nt->rect().height()*days/30),
                                              Qt::IgnoreAspectRatio,
                                              Qt::SmoothTransformation));
        }
    }

    //Draw archive notes
    painter.setOpacity(1);

    QList<Note*> nts;
    usedNotes.clear();
    nts.append( archiveModule.noteFile.notes );

    //Remove notes that are not onscreen, too small or too large
    for(Note *nt: nts){
        nt->fontSize_m = fontSizeForNote(nt);
        float x = scaleToPixels( nt->timeMade.toMSecsSinceEpoch() - leftEdgeInMSecs() );
        float w = scaleToPixels( nt->timeMade.msecsTo(nt->timeModified) );
        nt->rect_m.setRect(x, baselineY(), w, rect().height()-baselineY());

        if( ( !nt->rect().intersects(rect()) ) |
            ( nt->fontSize_m<1) |
            ( nt->rect().width()>rect().width() ) ){
            nts.removeOne(nt);
            continue;
        }
    }

    while( !nts.isEmpty() )
    {
        Note *nt = nts[0];

        //Get the largest note
        for( Note *testNote: nts){
            if( testNote->fontSize_m > nt->fontSize_m ){
                nt = testNote;
            }
        }

        QFont font("Sans");
        font.setPointSizeF( nt->fontSize_m );
        painter.setFont( font );
        QRectF boundingRect = painter.boundingRect( nt->rect_m, Qt::TextWordWrap | nt->alignment() | Qt::AlignVCenter, nt->text() );
        nt->rect_m.setHeight( boundingRect.height()+10 );

        //If there are notes intersecting with this one - move it under them
        bool intersectPresent = true;
        while( intersectPresent ){
            if(usedNotes.isEmpty()) intersectPresent = false;

            for(Note *usedNote: usedNotes){
                if( usedNote->rect().intersects(nt->rect()) ){
                    intersectPresent = true;
                    nt->rect_m.moveTop( usedNote->rect().bottom()+5 );
                    break;
                }else{
                    intersectPresent = false;
                }
            }
        }

        nt->textForDisplay_m = nt->text();
        nt->drawNote(&painter);

        usedNotes.append(nt);
        nts.removeOne( nt );
    }
}

void Timeline::wheelEvent(QWheelEvent *event)
{
    int numDegrees = event->delta() / 8;
    int numSteps = numDegrees / 15;

    //Change the viewpoint size
    qint64 viewportSizeChange = viewportSizeInMSecs*numSteps*0.02;
    viewportSizeInMSecs -= viewportSizeChange;

    //Correct the position so the zoom center (fixed point) is the mouse
    qint64 zoomCenter = positionInMSecs - viewportSizeInMSecs/2 + scaleToSeconds( event->pos().x() );
    positionInMSecs -= double(positionInMSecs - zoomCenter)*double(viewportSizeChange)/double(viewportSizeInMSecs);
    update();
}

void Timeline::mouseDoubleClickEvent(QMouseEvent *event)
{
    int x = event->pos().x();
    Note *nt = getNoteUnderMouse( event->pos() );

    slider.setGeometry(x, baselineY(), rect().width(), 10);
    slider.setMaximum( rect().width() );

    if( nt==NULL){

        slider.setValue( scaleToPixels(viewportSizeInMSecs/4));
        timelineWidget->misliWindow->edit_w->newNote();
    }else{
        timelineWidget->misliWindow->edit_w->editNote();
    }

    slider.show();
}
void Timeline::mouseMoveEvent(QMouseEvent *event)
{
    if(event->buttons()==Qt::LeftButton){
        positionInMSecs -= scaleToSeconds( event->x() - lastMousePos );
    }
    lastMousePos = event->x();
    update();
}
void Timeline::mouseReleaseEvent(QMouseEvent *event)
{
    for(Note *nt: usedNotes){
        nt->setSelected(false);
        if( nt->rect().contains( event->pos() ) ){
            nt->setSelected(true);
        }
    }
}

void Timeline::addModule(TimelineModule *module)
{
    timelineWidget->ui->sidebar->addWidget(module->widget);
    modules.append(module);
    QList<Note*> nts = module->loadNotes();
    notes.append(nts);
}

qint64 Timeline::leftEdgeInMSecs()
{
    return positionInMSecs - viewportSizeInMSecs/2;
}
float Timeline::baselineY()
{
    return baselinePositionCoefficient*rect().height();
}
float Timeline::fontSizeForNote(Note *nt)
{
    float fontSize = scaleToPixels( (nt->timeModified.toMSecsSinceEpoch() - nt->timeMade.toMSecsSinceEpoch())/40 );
    if(fontSize<0) fontSize = 0;
    return fontSize;
}
Note *Timeline::getNoteUnderMouse( QPoint mousePosition )
{
    for(Note *nt: usedNotes){
        if( nt->rect().contains( mousePosition ) ){
            return nt;
        }
    }
    return NULL;
}
