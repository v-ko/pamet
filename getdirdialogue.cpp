/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include "getdirdialogue.h"
#include "ui_getdirdialogue.h"

GetDirDialogue::GetDirDialogue(MisliWindow* msl_w_):
    ui(new Ui::GetDirDialogue)
{
    ui->setupUi(this);
    msl_w=msl_w_;
}

GetDirDialogue::~GetDirDialogue()
{
    delete ui;
}

void GetDirDialogue::showEvent(QShowEvent *)
{
  ui->lineEdit->setText("");
}

//Functions
void GetDirDialogue::input_done()
{
    QString path = ui->lineEdit->text();
    QDir dir;

    if(path.size()!=0){ //if path is empty the current dir is used and we don't want that
        dir.cd(path);
    }

    if( !dir.exists() ){
        ui->explainLabel->setText(tr("Directory doesn't exist"));
        return;
    }else {
        msl_w->add_dir(path);

        close();
    }
}

void GetDirDialogue::get_dir_dialogue()
{
    ui->lineEdit->setText(fileDialogue.getExistingDirectory(this,tr("Choose directory")));
}
