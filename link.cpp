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

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#include "link.h"
#include "global.h"
#include "note.h"

Link::Link(int id_, QPointF controlPoint_, QString text_)
{
    id = id_;
    controlPoint = controlPoint_;
    text = text_;
    usesControlPoint = true;
    controlPointIsSet = true;
}
Link::Link(int id_)
{
    id = id_;
}

QPointF Link::middleOfTheLine()
{
    return QPointF( line.p1()+(line.p2()-line.p1())/2 );
}

QPointF Link::realControlPoint()
{
    return 2*controlPoint - line.p1()/2 - line.p2()/2;
}

Link Link::fromJsonObject(QJsonObject obj){
    QJsonArray cp_arr = obj["cp"].toArray();
    QPointF cp(cp_arr[0].toDouble(), cp_arr[1].toDouble());

    return Link(obj["to_id"].toInt(), cp, obj["text"].toString());
}
QJsonObject Link::toJsonObject()
{
    QJsonObject json;
    json["to_id"] = id;
    json["text"] = text;

    QJsonArray cp;
    cp.append(controlPoint.x());
    cp.append(controlPoint.y());

    json["cp"] = cp;

    return json;
}
