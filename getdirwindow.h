/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef GETDIRWINDOW_H
#define GETDIRWINDOW_H

#include <QtGui>

class MisliInstance;

class GetDirWindow : public QWidget
{
    Q_OBJECT
public:
    //Functions
    GetDirWindow(MisliInstance*);
    
    //Variables
    MisliInstance *misl_i;

protected:
    QLabel *label,*label2;
    QLineEdit *entry;
    QPushButton *button;

signals:
    
public slots:
    void input_done();
};

#endif // GETDIRWINDOW_H
