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

#include "link.h"
#include "common.h"
#include "note.h"

Link::Link(int id_,QPointF controlPoint_)
{
    id=id_;
    controlPoint = controlPoint_;
    usesControlPoint = true;
    isSelected=false;
    controlPointIsSet = true;
    controlPointIsChanged = true;
}
Link::Link(int id_)
{
    id=id_;
    usesControlPoint = false;
    isSelected=false;
    controlPointIsSet = false;
    controlPointIsChanged = true;
}

QPointF Link::middleOfTheLine()
{
    return QPointF( line.p1()+(line.p2()-line.p1())/2 );
}

QPointF Link::realControlPoint()
{
    return 2*controlPoint - line.p1()/2 - line.p2()/2;
}
