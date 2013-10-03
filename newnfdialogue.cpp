/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "newnfdialogue.h"
#include "ui_newnfdialogue.h"
#include "mislidesktopgui.h"

NewNFDialogue::NewNFDialogue(MisliDesktopGui * misli_dg_) :
    ui(new Ui::NewNFDialogue)
{
    ui->setupUi(this);
    addAction(ui->actionEscape);//the action is defined in the .ui file and is not used . QActions must be added to a widget to work
    misli_dg=misli_dg_;

    nf_for_rename=NULL;
}

MisliInstance * NewNFDialogue::misli_i()
{
    return misli_dg->misli_i;
}
MisliWindow * NewNFDialogue::misli_w()
{
    return misli_dg->misli_w;
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
    move(misli_w()->x()+misli_w()->width()/2-width()/2,misli_w()->y()+misli_w()->height()/2-height()/2); //center the window in the misliWindow
    show();
    raise();
    activateWindow();
}
void NewNFDialogue::rename_nf(NoteFile * nf)
{
    nf_for_rename=nf;
    setWindowTitle(tr("Rename notefile"));
    ui->lineEdit->setText("");
    show();
    raise();
    activateWindow();
}

int NewNFDialogue::input_done()
{
    QString name = ui->lineEdit->text(),file_addr,qstr1,qstr2,old_name;
    name=name.trimmed();
    NoteFile * nf;
    Note *nt;

    if(misli_i()->curr_misli_dir()->nf_by_name(name)!=NULL){
        ui->helpLabel->setText(tr("A notefile with this name exists."));
        return -1;
    }

    file_addr=misli_i()->curr_misli_dir()->notes_dir;
    file_addr+="/";
    file_addr+=name;
    file_addr+=".misl";

    if(nf_for_rename==NULL){

        if( misli_i()->curr_misli_dir()->make_notes_file( name ) != 0 ) {
            ui->helpLabel->setText(tr("Error making notefile , exclude bad symbols from the name (; < >  ... )"));
            return -1;
        }else{
            misli_i()->curr_misli_dir()->reinit_notes_pointing_to_notefiles();
            misli_i()->curr_misli_dir()->set_current_note_file( misli_i()->curr_misli_dir()->note_file.back()->name );
        }

    }else{ //If we're renaming
        old_name=nf_for_rename->name;

        qstr1=old_name+".misl";
        qstr2=name+".misl";

        QFile file(nf_for_rename->full_file_addr);


        if( file.copy(QDir(misli_i()->curr_misli_dir()->notes_dir).filePath(qstr2)) ){
            nf_for_rename->full_file_addr = QDir(misli_i()->curr_misli_dir()->notes_dir).filePath(qstr2);
            nf_for_rename->name=name;
            nf_for_rename->save();
            misli_w()->switch_current_nf();
            nf_for_rename=NULL;

            //Now change all the notes that point to this one too
            for(unsigned int i=0;i<misli_i()->curr_misli_dir()->note_file.size();i++){
                nf = misli_i()->curr_misli_dir()->note_file[i];
                for(unsigned int n=0;n<nf->note.size();n++){
                    nt=nf->note[n];
                    if(nt->type==NOTE_TYPE_REDIRECTING_NOTE){
                        if(nt->text_for_display==old_name){
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
