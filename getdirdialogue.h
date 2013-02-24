#ifndef GETDIRDIALOGUE_H
#define GETDIRDIALOGUE_H

#include <QtGui>
#include <QFileDialog>
#include "misliinstance.h"

namespace Ui {
class GetDirDialogue;
}

class GetDirDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    GetDirDialogue(MisliInstance *misl_inst,QWidget *parent = 0);
    ~GetDirDialogue();

    //Variables
    MisliInstance *misl_i;
    QShortcut *shEnter,*shEscape;
    QFileDialog fileDialogue;

public slots:
    void input_done();
    void get_dir_dialogue();
    
private:
    Ui::GetDirDialogue *ui;
};

#endif // GETDIRDIALOGUE_H
