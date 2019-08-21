#include "photomodule.h"

#include "timeline.h"

PhotoModule::PhotoModule(Timeline *timeline_):
    TimelineModule(timeline_),
    reloadButton("Load photo library")
{
    controlWidget = &reloadButton;
    connect(&reloadButton, &QPushButton::clicked, this, &PhotoModule::updateNotesForDisplay);
    connect(&this->loadFuture, SIGNAL(finished()), this, SLOT(afterLoadingIsDone()));

    libraryIsLoaded = false;
}

void PhotoModule::afterLoadingIsDone()
{
    for(Note *nt: notesForDisplay) delete nt;
    notesForDisplay.clear();
    notesForDisplay.append(tmpNotes);
    tmpNotes.clear();
}

void PhotoModule::loadToTmp(qint64 positionInMSecs, qint64 viewportSizeInMSecs)
{
    // /sync/Снимки
    QDirIterator iterator("/sync/gsm_photos", QStringList()<<"*.jpg", QDir::Files, QDirIterator::Subdirectories);
    QProcess process;
    Note *nt;
    QColor txt_col,bg_col;
    txt_col.setRgbF(0,0,1,1);
    bg_col.setRgbF(0,0,1,0.1);

    reloadButton.setEnabled(false);

    int counter = 0;
    if(!libraryIsLoaded){
        while(iterator.hasNext()){
            QString filePath = iterator.next();
            QString execString = "exiv2 -g DateTimeOriginal -Pv \""+filePath+"\"";
            execString = execString.trimmed();
            //qDebug()<<"Executing: "+execString;
            process.start(execString);

            if(!process.waitForFinished(10000)){
                qDebug()<<"Process did not finish:"<<execString;
                process.kill();
            }else{
                counter++;
                if( (counter%10) == 0){
                    reloadButton.setText(QString::number(counter));
                }

            }
            QString error(process.readAllStandardError());
            if(!error.isEmpty()){
                qDebug()<<"Reading photo metadata returned error:"<<error;
            }
            QString out(process.readAllStandardOutput());
            out = out.trimmed();
            QDateTime timeMade = QDateTime::fromString(out,"yyyy:MM:dd hh:mm:ss");
            QString text = "define_picture_note:"+filePath;

            if( !timeMade.isValid() ) {
                qDebug()<<"Invalid DateTime:"<<out;
                continue;
            }

            //qDebug()<<"Valid picture:"<<filePath<<",with DateTime:"<<out;

            nt=new Note();
            nt->id = 0;
            nt->text_m = text;
            nt->setRect(QRectF(0,0,100,100));
            nt->timeMade = timeMade;
            nt->timeModified = timeMade.addMSecs(days/20);
            nt->textColor_m = txt_col;
            nt->backgroundColor_m = bg_col;

            library.append(nt);
        }
        libraryIsLoaded = true;
    }

    //Cache only the pictures in the viewport
    counter = 0;
    for(int i=0; i<library.size(); i++){
        counter++;
        Note *nt = new Note(library[i]);

        if( (counter%100) == 0){
            reloadButton.setText(QString::number(counter));
        }

        if( abs(nt->timeMade.toMSecsSinceEpoch()-positionInMSecs)>(viewportSizeInMSecs/2)  )
        {
            continue;
        }

        delete nt->img;
        QImage img(nt->addressString);
        nt->img = new QImage( img.scaled(100,100,Qt::KeepAspectRatio) ); //Make thumbnail
        tmpNotes.append(nt);
    }

    reloadButton.setText("Reload pictures");
    reloadButton.setEnabled(true);
}

void PhotoModule::updateNotesForDisplay()
{
    QFuture<void> future = QtConcurrent::run(this, &PhotoModule::loadToTmp, timeline->positionInMSecs, timeline->viewportSizeInMSecs);
    loadFuture.setFuture(future);
}
