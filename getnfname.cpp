/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "getnfname.h"

#include "common.h"
#include "misliinstance.h"

//Constructor
GetNFName::GetNFName(MisliInstance *misl_inst)
{
    misl_i=misl_inst;

    //Init elements
    label = new QLabel("Enter a notefile name :");
    entry = new QLineEdit;
    button = new QPushButton("Ok");
    label2 = new QLabel("Use no extention (.txt/.misl ,etc.), just a valid file name.");

    //Connect the button
    connect(button,SIGNAL(clicked()),this,SLOT(input_done()));

    //Shortcuts
    //--------Enter(return) - submit ---------------
    shEnter = new QShortcut(QKeySequence(Qt::Key_Return),this);
    connect(shEnter,SIGNAL( activated() ),button,SIGNAL( clicked() ) ); //edit the first selected note
    //-------Escape
    shEscape = new QShortcut(QKeySequence(Qt::Key_Escape),this);
    connect(shEscape,SIGNAL( activated() ),this,SLOT( close() ) ); //edit the first selected note

    //Setup layout
    QVBoxLayout *mainLayout = new QVBoxLayout;
    mainLayout->addWidget(label);
    mainLayout->addWidget(entry);
    mainLayout->addWidget(button);
    mainLayout->addWidget(label2);

    setLayout(mainLayout);

}

//Functions

void GetNFName::new_nf()
{
    entry->setText("");
    label2->setText("Use no extention (.txt/.misl ,etc.), just a valid file name.");
    show();
    raise();
    activateWindow();
}

int GetNFName::input_done()
{
    QString name = entry->text(),file_addr;
    name=name.trimmed();

    if( misl_i->make_notes_file( name.toUtf8().data() ) != true ) {
        label2->setText("Error making notefile , exclude bad symbols from the name (; < >  ... )");
        return 1;
    }else {
        file_addr=misl_i->notes_dir;
        file_addr+="/";
        file_addr+=name;
        file_addr+=".misl";

        misl_i->note_file.push_back(null_note_file); //nov obekt (vajno e pyrvo da go napravim ,za6toto pri dobavqneto na notes se zadava pointer kym note-file-a i toi trqbva da e kym realniq nf vyv vectora

        misl_i->note_file.back().init(misl_i,name.toUtf8().data(),file_addr.toUtf8().data());
        misl_i->note_file.back().set_to_current();

        close();
    }
    return 0;
}
