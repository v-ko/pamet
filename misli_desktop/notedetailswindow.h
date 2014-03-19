#ifndef NOTEDETAILSWINDOW_H
#define NOTEDETAILSWINDOW_H

#include <QWidget>

#include "note.h"

class MisliDesktopGui;

namespace Ui {
class NoteDetailsWindow;
}

class NoteDetailsWindow : public QWidget
{
    Q_OBJECT
    
public:
    NoteDetailsWindow();
    ~NoteDetailsWindow();

public slots:
    void updateInfo(Note& nt);
    
private:
    Ui::NoteDetailsWindow *ui;
};

#endif // NOTEDETAILSWINDOW_H
