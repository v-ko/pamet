/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef EDITNOTEWINDOW_H
#define EDITNOTEWINDOW_H

#include <QWidget>
#include <QShortcut>

class QLabel;
class QTextEdit;
class QPushButton;
class MisliInstance;
class Note;

class EditNoteWindow : public QWidget
{
    Q_OBJECT

public:
    //Functions
    EditNoteWindow(MisliInstance *m_i);

    //Variables
    MisliInstance *misl_i;
    Note * edited_note;
    double x_on_new_note,y_on_new_note;

    QLabel *label;//,*label2;
    QTextEdit *text_edit;
    QPushButton *button,*makeLinkButton;

    QShortcut *shEnter,*shEscape,*shMakeLink;

public slots:
    void make_link();
    void new_note();
    int edit_note();
    void input_done();


};

#endif // EDITNOTEWINDOW_H
