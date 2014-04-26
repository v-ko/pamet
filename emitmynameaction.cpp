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

#include "emitmynameaction.h"

EmitMyNameAction::EmitMyNameAction(QString name_,QMenu *qmenu_):
    QAction(qmenu_)
{
    setCheckable(1);
    qmenu=qmenu_;
    name=name_;
    setText(name);
    connect(this,SIGNAL(triggered()),this,SLOT(emit_triggered_with_name()));
}
EmitMyNameAction::~EmitMyNameAction()
{
}

void EmitMyNameAction::emit_triggered_with_name()
{
    check_only_me();
    emit triggered_with_name(name);
}

void EmitMyNameAction::check_only_me()
{
    for(int i=0;i<qmenu->actions().size();i++){
        qmenu->actions().at(i)->setChecked(0);
    }
    setChecked(1);
}
