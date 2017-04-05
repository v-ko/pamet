#ifndef COMMUNICATIONSMODULE_H
#define COMMUNICATIONSMODULE_H

#include <QtSql/QSqlDatabase>
#include <QListWidget>

#include "timelinemodule.h"

class CommunicationsModule : public TimelineModule
{
    Q_OBJECT
public:
    //Functions
    CommunicationsModule(Timeline *timeline_);

    //Variables
    QWidget chatWidget, controlsWidget;
    QPushButton queryButton,importFBChatsButton;
    QSqlDatabase dataBase;
    QListWidget chats, messages;

public slots:
    void queryCommunications();
    void loadChatMessages(QString chatText);
    void importFBChats();
};

#endif // COMMUNICATIONSMODULE_H
