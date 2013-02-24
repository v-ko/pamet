/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "helpwindow.h"
#include <QtGui>
#include <QFile>

HelpWindow::HelpWindow()
{
    QFile file(":/help/text.txt");
    QString str;

    if(file.open(QIODevice::ReadOnly)){
        QByteArray ba = file.readAll(); //this step is needed for some reason
        str = QString::fromUtf8( ba.data() );
    }else {
        str="Couldn't open help file";
    }

    //set the help text
    text_edit = new QTextBrowser();
    text_edit->setText(str);

    //Set layout
    QVBoxLayout *mainLayout = new QVBoxLayout;
    mainLayout->addWidget(text_edit);

    setLayout(mainLayout);
}
