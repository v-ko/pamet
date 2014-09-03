/*  This file is part of Misli.

    Misli is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Misli is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "getdirdialogue.h"
#include "ui_getdirdialogue.h"
#include "mislidesktopgui.h"

GetDirDialogue::GetDirDialogue(MisliDesktopGui *misli_dg_):
    ui(new Ui::GetDirDialogue)
{
    ui->setupUi(this);
    misli_dg=misli_dg_;
    addAction(ui->actionEscape);//the action is defined in the .ui file and is not used . QActions must be added to a widget to work

    if(misli_dg->first_program_start){
        //Setup the language combo box
        ui->comboBoxChooseLanguage->addItem(QString("English"));
        ui->comboBoxChooseLanguage->addItem(QString("Български"));
    }else{
        ui->comboBoxChooseLanguage->hide();
    }

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

    if( !dir.cd(path) ){ //if the dir is non existent or inaccessible cd returns false

        QMessageBox msg;

        msg.setText(tr("Directory doesn't exist or is inaccessible"));
        msg.setStandardButtons(QMessageBox::Ok);
        msg.setIcon(QMessageBox::Warning);
        msg.exec();
        return;
    }else{

        //Then handle the language (very hacky..)
        if(ui->comboBoxChooseLanguage->currentText()=="English"){
            if(misli_dg->language!="en"){
                misli_dg->misli_w->language="en";
                misli_dg->language="en";
                misli_i()->add_dir(dir.absolutePath());
                misli_dg->misli_w->export_settings();
                //Restart
                QProcess::startDetached(misli_dg->applicationFilePath());
                misli_dg->exit(0);
            }
        }else if(ui->comboBoxChooseLanguage->currentText()=="Български"){
            if(misli_dg->language!="bg"){
                misli_dg->misli_w->language="bg";
                misli_dg->language="bg";
                misli_i()->add_dir(dir.absolutePath());
                misli_dg->misli_w->export_settings();
                //Restart
                QProcess::startDetached(misli_dg->applicationFilePath());
                misli_dg->exit(0);
            }
        }else{
            misli_i()->add_dir(dir.absolutePath());
            misli_dg->misli_w->export_settings();
            close();
        }
    }

}

void GetDirDialogue::get_dir_dialogue()
{
    ui->lineEdit->setText(fileDialogue.getExistingDirectory(this,tr("Choose directory")));
}

MisliInstance *GetDirDialogue::misli_i()
{
    return misli_dg->misli_i;
}
