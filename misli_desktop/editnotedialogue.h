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

#ifndef EDITNOTEDIALOGUE_H
#define EDITNOTEDIALOGUE_H

#include <QtGui>
#include <QWidget>
#include <QMenu>

class Note;
class MisliInstance;

class MisliDesktopGui;
namespace Ui {
class EditNoteDialogue;
}

class EditNoteDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    EditNoteDialogue(MisliDesktopGui * misli_dg_);
    ~EditNoteDialogue();

    MisliInstance * misli_i();
    
    //Variables
    QMenu linkMenu,chooseNFMenu;
    QAction actionChooseTextFile,actionChoosePicture,actionSystemCallNote;
    MisliDesktopGui *misli_dg;
    Note * edited_note;
    double x_on_new_note,y_on_new_note;
    bool chooseNFMenuIsOpenedFromEditNoteDialogue;

public slots:
    void new_note();
    int edit_note();
    void input_done();
    void set_textEdit_text(QString text); //expose that publically

    void updateLinkMenu();
    void show_link_menu();
    void make_link_note(QAction *act);
    void choose_picture();
    void choose_text_file();
    void set_system_call_prefix();
private:
    Ui::EditNoteDialogue *ui;
};

#endif // EDITNOTEDIALOGUE_H
