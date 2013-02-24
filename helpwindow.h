/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#ifndef HELPWINDOW_H
#define HELPWINDOW_H

#include <QWidget>

class QTextBrowser;

class HelpWindow : public QWidget
{
public:
    HelpWindow();

    QTextBrowser *text_edit;
};

#endif // HELPWINDOW_H
