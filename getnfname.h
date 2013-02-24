/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef GETNFNAME_H
#define GETNFNAME_H

#include <QtGui>

class MisliInstance;

class GetNFName :  public QWidget
{
    Q_OBJECT
public:
    //Functions
    GetNFName(MisliInstance*);

    //Variables
    MisliInstance *misl_i;


    QLabel *label,*label2;
    QLineEdit *entry;
    QPushButton *button;

    QShortcut *shEnter,*shEscape;

signals:

public slots:
    void new_nf();
    int input_done();
};

#endif // GETNFNAME_H
