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

#ifndef NEWNFDIALOGUE_H
#define NEWNFDIALOGUE_H

#include <QWidget>
#include <QMessageBox>

#include "misliwindow.h"
#include "../misliinstance.h"

namespace Ui {
class NewNFDialogue;
}

class NewNFDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    NewNFDialogue(MisliDesktopGui *misli_dg_);
    ~NewNFDialogue();

    MisliInstance *misli_i();
    MisliWindow *misli_w();

    //Variables
    MisliDesktopGui *misli_dg;
    NoteFile * nf_for_rename;

public slots:
    void new_nf();
    void rename_nf(NoteFile * nf);
    int input_done();

private:
    Ui::NewNFDialogue *ui;
};

#endif // NEWNFDIALOGUE_H
