/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <QFont>
#include <QRect>
#include <QPainter>
#include <QImage>

#include "common.h"
#include "note.h"
#include "notefile.h"
#include "misliinstance.h"
#include "canvas.h"

#include "../../petko10.h"

Note::Note()
{
    x=0;
    y=0;
    z=0;
    a=10;
    b=4;
    font_size=1;
    selected=false;
    nf_id=0;
    type=0;
    txt_col[0]=0;//r
    txt_col[1]=0;//g
    txt_col[2]=1;//b
    txt_col[3]=1;//a
    bg_col[0]=0;
    bg_col[1]=0;
    bg_col[2]=1;
    bg_col[3]=0.5;
    pixm=NULL;
}

int Note::init(){ //skysqva teksta dokato se vkara v kutiqta i slaga mnogoto4ie nakraq + vkarva koordinatite na kutiqta

    int base_it,max_it,probe_it; //iterators for the shortening algorythm
    float pixm_real_size_x; //pixmap real size
    float pixm_real_size_y;
    Qt::AlignmentFlag alignment;

    //---------Random-----------

    //Coordinates for the note rectangle
    rx=x+a+NOTE_SPACING*2;
    ry=y+b+NOTE_SPACING*2;
    pixm_real_size_x = (rx-x)*FONT_TRANSFORM_FACTOR; //pixmap real size
    pixm_real_size_y = (ry-y)*FONT_TRANSFORM_FACTOR;

    if(misl_i->using_external_classes){
        if(misl_i->canvas->move_on){return 0;}
    }

    move_orig_x=x;
    move_orig_y=y;


    //-------Init painter for the text shortening----------
    QRectF text_field(0,0,a*FONT_TRANSFORM_FACTOR,b*FONT_TRANSFORM_FACTOR),text_field_needed;

    delete pixm;
    pixm = new QPixmap(pixm_real_size_x,pixm_real_size_y);
    pixm->fill(Qt::transparent);

    QString txt = text;

    QPainter p(pixm);
    QFont font("Halvetica");




    //------Adjust alignment---------------
    if(text.contains("\n")){//if there's more than one row
        has_more_than_one_row=true;
        alignment = Qt::AlignLeft;
    }else{
        has_more_than_one_row=false;
        alignment = Qt::AlignCenter;
    }

    //-------Check if we have a link to a file-----------
    if (txt.startsWith(QString("this_note_points_to:"))){
        txt=q_get_text_between(txt,':',0,200); //get text between ":" and the end
        txt=txt.trimmed(); //remove white spaces from both sides
        type=1;
        if(misl_i->nf_by_name(txt)==NULL){//if we have a wrong/missing name
            type=-1;
            txt="missing note file";
        }
        goto after_shortening;
    }else type=0;

    //=========Shortening the text in the box=============
    font.setPixelSize(font_size*FONT_TRANSFORM_FACTOR);
    p.setFont(font);

    txt=text;
    base_it=0;
    max_it=text.size();
    probe_it=base_it + ceil(float(max_it-base_it)/2);

    //-----If there's no resizing needed (common case , that's why it's in front)--------

    text_field_needed=p.boundingRect(text_field, Qt::TextWordWrap | alignment ,txt);
    if( (  text_field_needed.height() <= text_field.height() ) && ( text_field_needed.width() <= text_field.width() ) ){
        goto after_shortening;
    }
    //-----For the shorter than "..." texts (they won't get any shorter)--------------
    if(max_it<=3){
        goto after_shortening;
    }

    //------------Start shortening algorithm---------------------
    while((max_it-base_it)!=1) { //until we pin-point the needed length with accuracy 1

        txt.resize(probe_it); //we resize to the probe iterator
        text_field_needed=p.boundingRect(text_field, Qt::TextWordWrap | alignment ,txt); //get the bounding box for the text (with probe length)

        if( ( text_field_needed.height() > text_field.height() ) | ( text_field_needed.width() > text_field.width() ) ){//if the needed box is bigger than the size of the note
            max_it=probe_it; //if the text doesnt fit - move max_iterator to the current position
        }else{
            base_it=probe_it; //if it does - bring the base iterator to the current pos
        }

        probe_it=base_it + ceil(float(max_it-base_it)/2); //new position for the probe_iterator - optimally in the middle of the dead space
        txt=text;
    }

    txt.resize(max_it-3);
    txt+="...";
    after_shortening:
    short_text=txt;

    //=============Drawing the note===============================
    if(misl_i->using_external_classes){

        font.setStyleStrategy(QFont::PreferAntialias); //style aliasing
        p.setRenderHint(QPainter::TextAntialiasing);

        //Clear color


        //Draw the note field
        p.fillRect(0,0,pixm_real_size_x,pixm_real_size_y,QBrush(QColor(bg_col[0]*255,bg_col[1]*255,bg_col[2]*255,bg_col[3]*255)));

        //Draw the text
        p.setPen(QColor(txt_col[0]*255,txt_col[1]*255,txt_col[2]*255,txt_col[3]*255)); //set color
        p.setBrush(Qt::SolidPattern); //set fill style
        font.setPixelSize(font_size*FONT_TRANSFORM_FACTOR);
        p.setFont(font);
        p.drawText(QRectF(NOTE_SPACING*FONT_TRANSFORM_FACTOR,NOTE_SPACING*FONT_TRANSFORM_FACTOR,a*FONT_TRANSFORM_FACTOR,b*FONT_TRANSFORM_FACTOR),Qt::TextWordWrap | alignment,short_text);

        //if(id==1){//sample for testing
        // d("saving texture");
        // if (!pixm->save("./note.png",NULL,100)){d("bad save");}
        //}
    }

    return 0;

}
int Note::init_links(){ //smqta koordinatite i skysqva teksta (ako trqbva) na vs outlinkove

float lx1,ly1,lx2,ly2;
float a2,b2,x2,y2,z2,r2x1,r2x2,r2y1,r2y2;
Link *ln;
//NoteFile *nf;

lx1=rx-(rx-x)/2; //koordinati na sredata na poleto (izpolzvam gi za linkovete)
ly1=ry-(ry-y)/2;

for(unsigned int n=0;n<outlink.size();n++){

//---------Smqtane na koordinatite za link-a---------------
ln = &outlink[n];
Note *target_note=misl_i->nf_by_id(nf_id)->get_note_by_id(ln->id);
x2=target_note->x;//koordinati na teksta
y2=target_note->y;
z2=target_note->z;
a2=target_note->a;//razmeri na kutiqta na teksta
b2=target_note->b;
r2x1=x2; //koordinati na poleto
r2y1=y2;
r2x2=x2+a2+NOTE_SPACING*2;
r2y2=y2+b2+NOTE_SPACING*2;
lx2=r2x2-(r2x2-r2x1)/2; //koordinati na sredata na poleto (izpolzvam gi za linkovete)
ly2=r2y2-(r2y2-r2y1)/2;

    if( ( ( (rx>=r2x1)&&(x<=r2x1) ) || ( (rx>=r2x2)&&(x<=r2x2) ) ) || ( (x>=r2x1)&&(rx<=r2x2) ) ) { //ako nqkoi ot 2ta ryba na pole 2 zastypwa pole 1 ili ako ednoto pole napravo obhva6ta dr-to (t.e. poletata sa g/d edno nad drugo)

        if(ly1>ly2){ //ako pole 2 e otdolo (tuka ima6e popravka na proba-gre6ka pri prenapisvaneto v qpainter)
            ln->x1=lx1;
            ln->y1=y;
            ln->z1=z;
            ln->x2=lx2;
            ln->y2=r2y2;
            ln->z2=z2;
        }
        else { //ako pole 2 e otgore
            ln->x1=lx1;
            ln->y1=ry;
            ln->z1=z;
            ln->x2=lx2;
            ln->y2=r2y1;
            ln->z2=z2;
        }
    }
    else { //ako pole 2 ne e nad pole 1 slagame ot strani4nite povyrhnosti linkovete

        if(rx<=r2x1){ //ako pole 2 e otdqsno na pole 1
            ln->x1=rx;
            ln->y1=ly1;
            ln->z1=z;
            ln->x2=r2x1;
            ln->y2=ly2;
            ln->z2=z2;
        }

        if(x>=r2x2){ //ako pole 2 e otlqvo na pole 1
            ln->x1=x;
            ln->y1=ly1;
            ln->z1=z;
            ln->x2=r2x2;
            ln->y2=ly2;
            ln->z2=z2;
        }
    }

}

return 0;
}
int Note::correct_links(){

Note *ntt;
//korigirame izhodq6tite linkove
init_links();

//korigirame vhodq6tite linkove
for(unsigned int l=0;l<inlink.size();l++){
    int inl=inlink[l];
    ntt=misl_i->nf_by_id(nf_id)->get_note_by_id(inl);
    ntt->init_links();
}

return 0;
}
int Note::link_to_selected(){

if(nf_id!=misl_i->current_note_file){d("bad call for link_to_selected");exit(1);} //if the function is called for a note that's not displayed

Link ln;

for(unsigned int i=0;i<misl_i->curr_note->size();i++){ //za vseki note ot current
    if((*misl_i->curr_note)[i].selected && ( (*misl_i->curr_note)[i].id != id ) ){ //ako e selectiran
        inlink.push_back((*misl_i->curr_note)[i].id); //dobavi na noviq link edin inlink s id-to na selectiraniq
        ln.id=id; //dobavi na selectiraniq edin outlink s id-to na noviq
        (*misl_i->curr_note)[i].outlink.push_back(ln);
        (*misl_i->curr_note)[i].init_links();
    }

}


return 0;
}

int Note::add_link(Link *ln) //adds the link (+inlink), doesn't init it
{
    Link lnk;

    if(misl_i->nf_by_id(nf_id)->get_note_by_id(ln->id)!=NULL){ //if the note at the given id exists - create the link

        lnk.id=ln->id;
        lnk.text=ln->text;
        outlink.push_back(lnk); //in the note

        misl_i->nf_by_id(nf_id)->get_note_by_id(ln->id)->inlink.push_back(id); //in the target note
    }

    return 0;
}
int Note::delete_inlink_for_id(int id){

for(unsigned int i=0;i<inlink.size();i++){
    if(inlink[i]==id){
        inlink.erase(inlink.begin()+i);
        return 0;
    }
}

return 1;
}
int Note::delete_link(int position){

    Note *nt=misl_i->nf_by_id(nf_id)->get_note_by_id(outlink[position].id); //delete the target's inlink first
    nt->delete_inlink_for_id(id);

    outlink.erase(outlink.begin()+position); //delete the outlink

    return 0;
}
