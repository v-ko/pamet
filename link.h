/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef LINK_H
#define LINK_H

#include <QString>

class Link
{
public:
    //Functions
    Link();
    ~Link();

    //Hard variables
    int id;
    QString text;

    //Program variables
    float x1,y1,z1,x2,y2,z2;
    bool selected;
};

#endif // LINK_H
