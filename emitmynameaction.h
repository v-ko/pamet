/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef EMITMYNAMEACTION_H
#define EMITMYNAMEACTION_H

#include <QAction>
#include <QMenu>

class EmitMyNameAction : public QAction
{
    Q_OBJECT
public:
    EmitMyNameAction(QString name_, QMenu *qmenu_);
    ~EmitMyNameAction();

    //Variables
    QMenu *qmenu;
    QString name;

signals:
    void triggered_with_name(QString);
public slots:
    void emit_triggered_with_name();
    void check_only_me();
};

#endif // EMITMYNAMEACTION_H
