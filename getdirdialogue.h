/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef GETDIRDIALOGUE_H
#define GETDIRDIALOGUE_H

#include <QtGui>
#include <QFileDialog>
#include "misliwindow.h"

namespace Ui {
class GetDirDialogue;
}

class GetDirDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    GetDirDialogue(MisliWindow *msl_w);
    ~GetDirDialogue();


    //Variables
    MisliWindow *msl_w;
    QFileDialog fileDialogue;

public slots:
    void input_done();
    void get_dir_dialogue();

private:
    void showEvent(QShowEvent *);
    Ui::GetDirDialogue *ui;
};

#endif // GETDIRDIALOGUE_H
