#include "newnfdialogue.h"
#include "ui_newnfdialogue.h"

NewNFDialogue::NewNFDialogue(MisliWindow * msl_w_) :
    ui(new Ui::NewNFDialogue)
{
    ui->setupUi(this);
    msl_w=msl_w_;
}

NewNFDialogue::~NewNFDialogue()
{
    delete ui;
}

void NewNFDialogue::new_nf()
{
    ui->lineEdit->setText("");
    show();
    raise();
    activateWindow();
}

int NewNFDialogue::input_done()
{
    QString name = ui->lineEdit->text(),file_addr;
    name=name.trimmed();

    if(msl_w->curr_misli()->nf_by_name(name.toUtf8().data())!=NULL){
        ui->helpLabel->setText(tr("A notefile with this name exists."));
        return -1;
    }

    if( msl_w->curr_misli()->make_notes_file( name.toUtf8().data() ) != true ) {
        ui->helpLabel->setText(tr("Error making notefile , exclude bad symbols from the name (; < >  ... )"));
        return -1;
    }else {
        file_addr=msl_w->curr_misli()->notes_dir;
        file_addr+="/";
        file_addr+=name;
        file_addr+=".misl";

        msl_w->curr_misli()->note_file.push_back(NoteFile()); //nov obekt (vajno e pyrvo da go napravim ,za6toto pri dobavqneto na notes se zadava pointer kym note-file-a i toi trqbva da e kym realniq nf vyv vectora

        msl_w->curr_misli()->note_file.back().init(msl_w->curr_misli(),name,file_addr);
        msl_w->curr_misli()->note_file.back().set_to_current();

        close();
    }
    return 0;
}
