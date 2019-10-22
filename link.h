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

#ifndef LINK_H
#define LINK_H

#include <QString>
#include <QLineF>
#include <QPointF>
#include <QPainterPath>

class Note;

class Link
{
public:
    //Functions
    Link(int id_, QPointF controlPoint_, QString text_);
    Link(int id_);

    QPointF middleOfTheLine();
    QPointF realControlPoint();
    static Link fromJsonObject(QJsonObject obj);
    QJsonObject toJsonObject();

    //Hard variables
    int id;
    QString text; //include a check for semicolons when saving the text!

    //Program variables
    QLineF line, autoLine;
    QPointF controlPoint;
    QPainterPath path;
    bool isSelected = false;
    bool usesControlPoint = false;
    bool controlPointIsSet = false;
    bool controlPointIsChanged = true;
};

#endif // LINK_H
