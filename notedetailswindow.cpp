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
