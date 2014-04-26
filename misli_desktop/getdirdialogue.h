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
    GetDirDialogue(MisliDesktopGui *misli_dg_);
    ~GetDirDialogue();

    MisliInstance *misli_i();

    //Variables
    MisliDesktopGui *misli_dg;
    QFileDialog fileDialogue;

public slots:
    void input_done();
    void get_dir_dialogue();

private:
    void showEvent(QShowEvent *);
    Ui::GetDirDialogue *ui;
};

#endif // GETDIRDIALOGUE_H
