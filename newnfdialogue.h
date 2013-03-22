#ifndef NEWNFDIALOGUE_H
#define NEWNFDIALOGUE_H

#include <QWidget>
#include <QMessageBox>

#include "misliwindow.h"

namespace Ui {
class NewNFDialogue;
}

class NewNFDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    NewNFDialogue(MisliWindow *msl_w_);
    ~NewNFDialogue();

    //Variables
    MisliWindow *msl_w;
    NoteFile * nf_for_rename;

public slots:
    void new_nf();
    void rename_nf(NoteFile * nf);
    int input_done();

private:
    Ui::NewNFDialogue *ui;
};

#endif // NEWNFDIALOGUE_H
