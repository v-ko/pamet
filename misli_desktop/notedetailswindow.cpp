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

#include "notedetailswindow.h"
#include "ui_notedetailswindow.h"

NoteDetailsWindow::NoteDetailsWindow() :
    ui(new Ui::NoteDetailsWindow)
{
    ui->setupUi(this);
}

NoteDetailsWindow::~NoteDetailsWindow()
{
    delete ui;
}

void NoteDetailsWindow::updateInfo(Note &nt)
{
    ui->idLabel->setText(QVariant(nt.id).toString());
    ui->xLabel->setText(QVariant(nt.x).toString());
    ui->yLabel->setText(QVariant(nt.y).toString());
    ui->zLabel->setText(QVariant(nt.z).toString());
    ui->aLabel->setText(QVariant(nt.a).toString());
    ui->bLabel->setText(QVariant(nt.b).toString());
    ui->t_madeLabel->setText(nt.t_made.toString("d.M.yyyy H:m:s"));
    ui->t_modLabel->setText(nt.t_mod.toString("d.M.yyyy H:m:s"));
    ui->text_for_shorteningLabel->setText(nt.text_for_shortening);
    ui->text_for_displayLabel->setText(nt.text_for_display);
    ui->address_stringLabel->setText(nt.address_string);
    ui->typeLabel->setText(QVariant(nt.type).toString());
    ui->selectedLabel->setText(QVariant(nt.selected).toString());
    ui->text_is_shortenedLabel->setText(QVariant(nt.text_is_shortened).toString());

    QString inlinks_txt,outlinks_txt;

    for(unsigned int i=0;i<nt.inlink.size();i++){
        inlinks_txt+=QVariant(nt.inlink[i]).toString();
        inlinks_txt+=";";
    }
    for(unsigned int i=0;i<nt.outlink.size();i++){
        outlinks_txt+=QVariant(nt.outlink[i].id).toString();
        outlinks_txt+=";";
    }
    ui->outlinksLabel->setText(outlinks_txt);
    ui->inlinksLabel->setText(inlinks_txt);
}
