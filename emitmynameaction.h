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
