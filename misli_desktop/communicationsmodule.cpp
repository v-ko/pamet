#include "communicationsmodule.h"

#include <QtSql/QSqlQuery>
#include <QtSql/QSqlRecord>
#include <QLayout>
#include <QFileDialog>
#include <QMessageBox>

#include "timeline.h"

CommunicationsModule::CommunicationsModule(Timeline *timeline_):
    TimelineModule(timeline_),
    queryButton("Search chats"),
    importFBChatsButton("Import FB chats")
{
    QLayout *controlLayout = new QVBoxLayout(&controlsWidget);
    controlLayout->addWidget(&queryButton);
    controlLayout->addWidget(&importFBChatsButton);
    controlsWidget.setLayout(controlLayout);

    controlWidget = &controlsWidget;

    QLayout *chatLayout = new QHBoxLayout(&chatWidget);
    chatLayout->addWidget(&chats);
    chatLayout->addWidget(&messages);
    chatWidget.setLayout(chatLayout);
    messages.setWordWrap(true);

    dataBase = QSqlDatabase::addDatabase("QSQLITE");
    dataBase.setDatabaseName("/sync/arhiv/communication/communications.db");
    if( !dataBase.open() ) qDebug()<<"Error on opening db";

    //Connections
    connect(&queryButton, &QPushButton::clicked, this, &CommunicationsModule::queryCommunications);
    connect(&chats, SIGNAL(currentTextChanged(QString)), this, SLOT(loadChatMessages(QString)));
    connect(&importFBChatsButton, SIGNAL(clicked(bool)),this, SLOT(importFBChats()));
}

void CommunicationsModule::queryCommunications()
{
    QString options = " WHERE timestamp<";
    options += QString::number( (timeline->leftEdgeInMSecs()+timeline->viewportSizeInMSecs)/1000);
    options += " AND timestamp>";
    options += QString::number( timeline->leftEdgeInMSecs()/1000);

    QSqlQuery query = dataBase.exec("SELECT DISTINCT conv_displayname FROM messages"+options);

    if(!query.first()){
        qDebug()<<"No chats at this time:"<<options;
        return;
    }

    chats.clear();
    int counter=0;
    do{
        counter++;
        chats.addItem( query.value(0).toString());
    }while(query.next());
    chatWidget.showMaximized();
}

void CommunicationsModule::loadChatMessages(QString chatText)
{
    QString options = " WHERE timestamp<";
    options += QString::number( (timeline->leftEdgeInMSecs()+timeline->viewportSizeInMSecs)/1000);
    options += " AND timestamp>";
    options += QString::number( timeline->leftEdgeInMSecs()/1000);
    options += " AND conv_displayname='"+chatText.replace("'","")+"'";
    options += " ORDER BY timestamp";

    QSqlQuery query = dataBase.exec("SELECT body_xml, author, author_displayname, timestamp, conv_displayname FROM messages"+options);

    if(!query.first()){
        qDebug()<<"We should not be here, options:"<<options;
        return;
    }

    messages.clear();
    int counter=0;
    do{
        counter++;
        QListWidgetItem *item = new QListWidgetItem(&messages);
        QString text = query.value(0).toString();
        text = text.remove( QRegExp("<[^>]*>") );
        text = text.remove( "&quot;" );
        QString time("["+ QDateTime::fromMSecsSinceEpoch( query.value(3).toLongLong()*1000 ).toString("yyyy:MM:dd hh:mm:ss") +"]");

        if( (query.value(1).toString()=="sk_sk_sk") |
                (query.value(1).toString()=="Petko Ditchev") |
                (query.value(1).toString()=="1048489022@facebook.com") ){
            item->setText( text+time );
            item->setBackgroundColor( QColor(0,255,0,30));
            item->setTextAlignment(Qt::AlignRight);
        }else if( query.value(2).toString().contains("@facebook") &&
                  (query.value(2).toString().split("@facebook").size()<3) ){
            item->setText(time+query.value(4).toString()+": "+text );
        }else{
            item->setText(time+query.value(2).toString()+": "+text );
        }
        messages.addItem(item);
    }while(query.next());
    messages.show();
}

void CommunicationsModule::importFBChats()
{
    QFile csvFile("/home/p10/fbchat.csv"), outFile("/home/p10/fbchat.sql");

    QString messagesFilePath = QFileDialog::getOpenFileName(timeline, "Open the Messages.htm file from the archive", QString(),"messages.htm");
    if(messagesFilePath.isEmpty()) return;

    QProcess process;
    process.setStandardOutputFile("/home/p10/fbchat.csv");
    qDebug()<<"Starting fbcap on"+messagesFilePath;
    process.start("fbcap "+messagesFilePath+" -f csv");
    if(!process.waitForFinished(120000)){
        qDebug()<<"fbcap did not load the chats in two minutes.Terminating";
        qDebug()<<process.readAll();
        return;
    }
    qDebug()<<"fbcap loaded the chats";


    csvFile.open(QIODevice::ReadOnly);
    outFile.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text);

    QTextStream outStream(&outFile);

    outStream<<"BEGIN TRANSACTION;\n";

    QString allData(csvFile.readAll()), values[4];//chat, author, dateTimeString, message;
    bool inQuote=false;
    int atValue=0;

    for(QChar ch: allData){
        if(ch==QChar('\"')){

            if(inQuote){
                inQuote = false;
            }else inQuote = true;

        }else if(ch==QChar(',')){

            if(!inQuote){
                atValue++;
                if(atValue>3) qDebug()<<"Found a 5th value in the csv. This should not happen";
            }else values[atValue]+=ch;

        }else if(ch==QChar('\n')){

            if(!inQuote){
                if(atValue<3) qDebug()<<"Line ending before all values are found.";
                QString execString("INSERT INTO messages(conv_identity,conv_displayname,author,author_displayname,timestamp,body_xml) VALUES(");
                execString += "\""+values[0]+"\","; //conv_identity
                execString += "\"FB:"+values[0]+"\","; //conv_displayname
                execString += "\""+values[1]+"\","; //author
                execString += "\""+values[1]+"\","; //author_displayname
                execString += QString::number(QDateTime::fromString(values[2],Qt::ISODate).toMSecsSinceEpoch()/1000)+",";
                execString += "\""+values[3]+"\");"; //body_xml
                execString.remove("\r");
                execString.replace("\\","\\\\");
                outStream<<execString<<"\n";

                values[0].clear();
                values[1].clear();
                values[2].clear();
                values[3].clear();
                atValue = 0;
            }else values[atValue]+=ch;
        }else values[atValue]+=ch;
    }
    outStream<<"END TRANSACTION;";
    outFile.close();
    csvFile.close();

    QProcess process2;
    qDebug()<<"Starting to import data in the database";
    process2.start("bash", QStringList() << "-c" << "cat /home/p10/fbchat.sql | sqlite3 /sync/arhiv/communication/common.db");
    if(!process2.waitForFinished(100000)){
        qDebug()<<"Process to add chats to db did not finish in 100 sec. Terminating.";
        process2.terminate();
    }else{
        qDebug()<<"Process finished"<<process2.readAll();
    }

    dataBase.exec("delete from messages where id not in ( select min(id) from Messages group by timestamp, body_xml);");
}
