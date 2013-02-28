/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef LINK_H
#define LINK_H

#include <GL/gl.h>
#include <QString>

class Link
{
public:
    //Functions
    Link();

    //Hard variables
    QString text;
    int id;

    //Program variables
    float x1,y1,z1,x2,y2,z2;
    char *short_text;
    bool selected;
    GLuint texture;
};

#endif // LINK_H
