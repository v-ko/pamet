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

class MisliWindow;
namespace Ui {
class EditNoteDialogue;
}

class EditNoteDialogue : public QWidget
{
    Q_OBJECT
    
public:
    //Functions
    EditNoteDialogue(MisliWindow * misliWindow_);
    ~EditNoteDialogue();

    MisliInstance * misli_i();
    QString maybeToRelativePath(QString path);
    
    //Variables
    QMenu linkMenu,chooseNFMenu;
    QAction actionChooseTextFile,actionChoosePicture,actionPythonScriptNote,actionWebPageNote;
    MisliWindow *misliWindow;
    Note * edited_note;
    double x_on_new_note,y_on_new_note;

public slots:
    void newNote();
    void editNote();
    void inputDone();
    void setTextEditText(QString text); //expose that publically

    void updateChooseNFMenu();
    void showLinkMenu();
    void makeLinkNote(QAction *act);
    void choosePicture();
    void chooseTextFile();
    void setSystemCallPrefix();
    void closeEvent(QCloseEvent *);
private slots:
    void on_openButton_clicked();

private:
    Ui::EditNoteDialogue *ui;
};

#endif // EDITNOTEDIALOGUE_H
