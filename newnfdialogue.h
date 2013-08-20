/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef NEWNFDIALOGUE_H
#define NEWNFDIALOGUE_H

#include <QWidget>
#include <QMessageBox>

#include "misliwindow.h"
#include "misliinstance.h"

namespace Ui {
class NewNFDialogue;
}

class NewNFDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    NewNFDialogue(MisliWindow *misli_w_);
    ~NewNFDialogue();

    //Variables
    MisliWindow *misli_w;
    MisliInstance *misli_i;
    NoteFile * nf_for_rename;

public slots:
    void new_nf();
    void rename_nf(NoteFile * nf);
    int input_done();

private:
    Ui::NewNFDialogue *ui;
};

#endif // NEWNFDIALOGUE_H
