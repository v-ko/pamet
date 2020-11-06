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
#include "../global.h"

Timeline::Timeline(TimelineWidget *timelineWidget_) :
    QWidget(timelineWidget_),
    slider(Qt::Horizontal, this),
    archiveModule(this)
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
    positionInMSecs =  QDateTime::currentDateTime().toMSecsSinceEpoch(); //QDateTime(QDate(2009,2,19)).toMSecsSinceEpoch();

    //Visual change on new notes
    connect(&archiveModule.noteFile, SIGNAL(visualChange()), this, SLOT(update()));
}
Timeline::~Timeline()
{
    for (TimelineModule *module: modules) delete module;
}

int Timeline::scaleToPixels(qint64 miliseconds)
{
    return int(miliseconds * ( double(rect().width())/double(viewportSizeInMSecs) ));
}

double Timeline::scaleToMSeconds(qint64 pixels)
{
    return pixels * ( double(viewportSizeInMSecs)/double(rect().width()) );
}

int Timeline::toPixelsFromMSecs(qint64 miliseconds)
{
    qint64 leftViewportEdge = positionInMSecs - viewportSizeInMSecs/2;
    qint64 offsetInMSecs = miliseconds - leftViewportEdge;
    return scaleToPixels(offsetInMSecs);
}

void Timeline::drawDelimiter(QPainter *painter, qint64 delimiterInMSecs, double lineHeight)
{
    double offset = toPixelsFromMSecs(delimiterInMSecs);
    double y1 = baselineY() - lineHeight/2;
    double y2 = baselineY() + lineHeight/2;

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
    double opacity = 1;

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
            drawDelimiter(&painter, delimeterPosition, scaleToPixels( double(1*days)/10) );
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
            drawDelimiter(&painter, delimeterPosition, scaleToPixels( double(months)/10) );

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
            drawDelimiter(&painter, delimeterPosition, scaleToPixels( double(years)/10) );

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

    painter.setOpacity(1);

    //Draw all modules except the archive module
    QList<Note*> nts;
    for(TimelineModule *module: modules){
        nts.append(module->notesForDisplay);
    }
    //Remove notes that are not onscreen
    for(int i=0; i<nts.size(); i++){
        Note *nt = nts[i];
        double x = scaleToPixels( nt->timeMade.toMSecsSinceEpoch() - leftEdgeInMSecs() );
        QRectF tmpRect = nt->rect();
        tmpRect.moveCenter( QPointF(x, 0) );
        tmpRect.moveBottom( baselineY()-5 );

        if( !tmpRect.intersects(rect()) ){
            nts.removeOne(nt);
            i--;
            continue;
        }
    }
    //Draw
    for(Note *nt: nts){
        painter.drawImage(nt->rect().topLeft(), *nt->img);
    }

    //Draw archive notes
    nts.clear();
    usedNotes.clear();
    nts.append( archiveModule.noteFile.notes );

    //Remove notes that are not onscreen, too small or too large
    for(int i=0; i<nts.size(); i++){
        Note *nt = nts[i];
        nt->fontSize = fontSizeForNote(nt);
        double x = scaleToPixels( nt->timeMade.toMSecsSinceEpoch() - leftEdgeInMSecs() );
        double w = scaleToPixels( nt->timeMade.msecsTo(nt->timeModified) );
        nt->rect_m.setRect(x, baselineY(), w, rect().height()-baselineY());

        if( ( !nt->rect().intersects(rect()) ) |
            ( nt->fontSize<1) |
            ( nt->rect().width()>rect().width() ) ){
            nt->setRect(QRectF()); //clear the position so it doesn't parttake in the selection
            nts.removeOne(nt);
            i--;
            continue;
        }
    }

    while( !nts.isEmpty() )
    {
        Note *nt = nts[0];

        //Get the largest note
        for( Note *testNote: nts){
            if( testNote->fontSize > nt->fontSize ){
                nt = testNote;
            }
        }

        QFont font("Nimbus Sans");
        font.setPointSizeF( nt->fontSize );
        painter.setFont( font );
        QRectF boundingRect = painter.boundingRect( nt->textRect(), Qt::TextWordWrap | nt->alignment() | Qt::AlignVCenter, nt->text() );
//        qDebug() << "bounding vs note, fontsize" << boundingRect.width() << nt->rect_m.width() << nt->fontSize;
        nt->rect_m.setHeight( boundingRect.height() * 1.6 ); //Hacky fix for bad textfield calculations

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
        nt->drawNote(painter);

        usedNotes.append(nt);
        nts.removeOne( nt );
    }

    //Call modules' paint events
    for(TimelineModule *module: modules){
        module->paintRoutine(painter);
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
    qint64 zoomCenter = positionInMSecs - viewportSizeInMSecs/2 + scaleToMSeconds( event->pos().x() );
    positionInMSecs -= double(positionInMSecs - zoomCenter)*double(viewportSizeChange)/double(viewportSizeInMSecs);
    update();
}

void Timeline::mouseDoubleClickEvent(QMouseEvent *event)
{
    Note *nt = getNoteUnderMouse( event->pos() );

    slider.setGeometry(event->x(), baselineY(), rect().width(), 10);
    slider.setMaximum( rect().width() );

    if( nt==nullptr){
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
        positionInMSecs -= scaleToMSeconds( event->x() - lastMousePos );
    }
    lastMousePos = event->x();
    update();
}
void Timeline::mouseReleaseEvent(QMouseEvent *event)
{
    for(Note *nt: archiveModule.noteFile.notes){
        nt->setSelected(false);
        if( nt->rect().contains( event->pos() ) ){
            nt->setSelected(true);
        }
    }
}

void Timeline::addModule(TimelineModule *module)
{
    timelineWidget->ui->sidebar->addWidget(module->controlWidget);
    modules.append(module);
}

qint64 Timeline::leftEdgeInMSecs()
{
    return positionInMSecs - viewportSizeInMSecs/2;
}
double Timeline::baselineY()
{
    return baselinePositionCoefficient*rect().height();
}
double Timeline::fontSizeForNote(Note *nt)
{
    double fontSize = scaleToPixels( (nt->timeModified.toMSecsSinceEpoch() - nt->timeMade.toMSecsSinceEpoch())/40 );
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
    return nullptr;
}
