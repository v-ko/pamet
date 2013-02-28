#ifndef EMITMYNAMEACTION_H
#define EMITMYNAMEACTION_H

#include <QAction>
#include <QMenu>

class EmitMyNameAction : public QAction
{
    Q_OBJECT
public:
    explicit EmitMyNameAction(QString name_, QMenu *qmenu_);
    
    QMenu *qmenu;
    QString name;
signals:
    void triggered_with_name(QString);
public slots:
    void emit_triggered_with_name();
    void check_only_me();
};

#endif // EMITMYNAMEACTION_H
