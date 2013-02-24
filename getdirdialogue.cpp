#include "getdirdialogue.h"
#include "ui_getdirdialogue.h"

GetDirDialogue::GetDirDialogue(MisliInstance *misl_inst,QWidget *parent):
    QWidget(parent),
    ui(new Ui::GetDirDialogue)
{
    ui->setupUi(this);
    misl_i=misl_inst;
    //fileDialogue = new QFileDialog()

}

GetDirDialogue::~GetDirDialogue()
{
    delete ui;
}

//Functions
void GetDirDialogue::input_done()
{
    QString path = ui->lineEdit->text();
    QDir dir;

    if(path.size()!=0){ //if path is empty the current dir is used and we don't want that
    dir.cd(path);}

    if( !dir.exists() ){
        ui->explainLabel->setText("Directory doesn't exist");
        return;
    }else {
        misl_i->notes_dir = path;
        misl_i->settings->setValue("notes_dir",QVariant(misl_i->notes_dir));
        misl_i->settings->sync();

        emit misl_i->settings_ready_publ();
        close();
    }
}

void GetDirDialogue::get_dir_dialogue()
{
    ui->lineEdit->setText(fileDialogue.getExistingDirectory(this,"Choose directory"));
}
