#include "newnfdialogue.h"
#include "ui_newnfdialogue.h"

NewNFDialogue::NewNFDialogue(MisliWindow * msl_w_) :
    ui(new Ui::NewNFDialogue)
{
    ui->setupUi(this);
    msl_w=msl_w_;
    nf_for_rename=NULL;
}

NewNFDialogue::~NewNFDialogue()
{
    delete ui;
}

void NewNFDialogue::new_nf()
{
    nf_for_rename=NULL;
    setWindowTitle(tr("New notefile"));
    ui->lineEdit->setText("");
    show();
}
void NewNFDialogue::rename_nf(NoteFile * nf)
{
    nf_for_rename=nf;
    setWindowTitle(tr("Rename notefile"));
    ui->lineEdit->setText("");
    show();
}

int NewNFDialogue::input_done()
{
    QString name = ui->lineEdit->text(),file_addr,qstr1,qstr2,old_name;
    name=name.trimmed();
    NoteFile * nf;
    Note *nt;

    if(msl_w->curr_misli()->nf_by_name(name)!=NULL){
        ui->helpLabel->setText(tr("A notefile with this name exists."));
        return -1;
    }

    file_addr=msl_w->curr_misli()->notes_dir;
    file_addr+="/";
    file_addr+=name;
    file_addr+=".misl";

    if(nf_for_rename==NULL){

        if( msl_w->curr_misli()->make_notes_file( name ) != true ) {
            ui->helpLabel->setText(tr("Error making notefile , exclude bad symbols from the name (; < >  ... )"));
            return -1;
        }else {
            msl_w->curr_misli()->note_file.push_back(NoteFile()); //nov obekt (vajno e pyrvo da go napravim ,za6toto pri dobavqneto na notes se zadava pointer kym note-file-a i toi trqbva da e kym realniq nf vyv vectora
            msl_w->curr_misli()->note_file.back().init(msl_w->curr_misli(),name,file_addr);
            msl_w->curr_misli()->note_file.back().set_to_current();
        }

    }else{ //If we're renaming
        old_name=nf_for_rename->name;

        qstr1=old_name+".misl";
        qstr2=name+".misl";

        QFile file(nf_for_rename->full_file_addr);

        if(file.copy(file_addr)){
            nf_for_rename->full_file_addr=file_addr;
            nf_for_rename->name=name;
            nf_for_rename->save();
            msl_w->switch_current_nf();
            nf_for_rename=NULL;

            //Now change all the notes that point to this one too
            for(unsigned int i=0;i<msl_w->curr_misli()->note_file.size();i++){
                nf = &msl_w->curr_misli()->note_file[i];
                for(unsigned int n=0;n<nf->note->size();n++){
                    nt=&((*nf->note)[n]);
                    if(nt->type==1){
                        if(nt->short_text==old_name){
                            nt->text="this_note_points_to:"+name;
                            nt->init();
                        }
                    }
                }
            }

        }else{
            QMessageBox msg;
            msg.setText(tr("Error while renaming file."));
            msg.exec();
        }
        file.remove();
    }

    close();

    return 0;
}
