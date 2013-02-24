/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "getdirwindow.h"
#include "misliinstance.h"

//Constructor
GetDirWindow::GetDirWindow(MisliInstance *misl_inst)
{
    misl_i=misl_inst;

    //Init elements
    label = new QLabel("Enter a folder to store the files with notes in:");
    entry = new QLineEdit;
    button = new QPushButton("Ok");
    label2 = new QLabel("for example:/home/usr/misli/ or C:\\misli");

    //Connect the button
    connect(button,SIGNAL(clicked()),this,SLOT(input_done()));

    //Setup layout
    QVBoxLayout *mainLayout = new QVBoxLayout;
    mainLayout->addWidget(label);
    mainLayout->addWidget(entry);
    mainLayout->addWidget(button);
    mainLayout->addWidget(label2);

    setLayout(mainLayout);

}

//Functions
void GetDirWindow::input_done()
{
    QString path = entry->text();

    QDir dir(path);

    if( !dir.exists() ){
        label2->setText("Directory doesn't exist");
        return;
    }else {
        misl_i->notes_dir = path;
        misl_i->settings->setValue("notes_dir",QVariant(misl_i->notes_dir));
        misl_i->settings->sync();

        emit misl_i->settings_ready_publ();
        close();
    }
}
