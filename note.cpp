/* This program is licensed under GNU GPL . For the full notice see the
 * license.txt file or google the full text of the GPL*/

#include <QFont>
#include <QRect>
#include <QPainter>
#include <QGLWidget>
#include <QImage>
#include <GL/gl.h>
#include <GL/glu.h>

#include "common.h"
#include "note.h"
#include "notefile.h"
#include "misliinstance.h"

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
}

int Note::init(){ //skysqva teksta dokato se vkara v kutiqta i slaga mnogoto4ie nakraq + vkarva koordinatite na kutiqta

    int base_it,max_it,probe_it; //iterators for the shortening algorythm

    //---------Random-----------

    //Coordinates for the note rectangle
    rx1=x-0.01;
    ry1=y+0.01;
    rx2=x+a+0.01;
    ry2=y-b-0.01;

    if(misl_i->using_external_classes){
        if(misl_i->gl_w->move_on){return 0;}
    }


    move_orig_x=x;
    move_orig_y=y;

    //-------Init drawing tools----------
    double A = a*FONT_TRANSFORM_FACTOR;
    double B = b*FONT_TRANSFORM_FACTOR;

    QRectF rect(0,0,A,B),rect2;
    QImage pixm(A,B,QImage::Format_ARGB32);
    QString txt = text;

    QPainter p(&pixm);
    QFont font("Halvetica");font.setPixelSize(font_size*FONT_TRANSFORM_FACTOR);
    font.setStyleStrategy(QFont::PreferAntialias); //QFont::StyleStrategy(0x0080)); //style aliasing
    p.setFont(font);


    //Check if we have a link to a file
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
    txt=text;
    base_it=0;
    max_it=text.size();
    probe_it=base_it + ceil(float(max_it-base_it)/2);

    //if there's no resizing needed (common case , that's why it's in front)
    rect2=p.boundingRect(rect, Qt::TextWordWrap | Qt::AlignCenter ,txt);
    if( !( ( mod( rect2.height() ) > mod(B) ) | ( mod( rect2.width() ) > mod(A) ) ) ){
        goto after_shortening;
    }
    if(max_it<=3){//for the shorter than "..." texts (they won't get any shorter)
        goto after_shortening;
    }

    //Start shortening algorithm
    while((max_it-base_it)!=1) { //until we pin-point the needed length with accuracy 1

        txt.resize(probe_it); //we resize to the probe iterator
        rect2=p.boundingRect(rect, Qt::TextWordWrap | Qt::AlignCenter ,txt); //get the bounding box for the text (with probe length

        if( ( mod( rect2.height() ) > mod(B) ) | ( mod( rect2.width() ) > mod(A) ) ){//if the needed box is bigger than the size of the note
            max_it=probe_it;
        }else{
            base_it=probe_it;
        }

        probe_it=base_it + ceil(float(max_it-base_it)/2); //POSSIBLE BREAKPOINT| will always be >0
        txt=text;
    }

    txt.resize(max_it-3);
    txt+="...";
    after_shortening:
    short_text=txt;
/*
        again:
    rect2=p.boundingRect(rect, Qt::TextWordWrap | Qt::AlignCenter ,txt);

    if( ( mod( rect2.height() ) > mod(B) ) | ( mod( rect2.width() ) > mod(A) ) ) {
        resized=1;
        txt.resize(txt.size()-1);
        goto again;
    }
    if(resized){
        txt.resize(txt.size()-3);
        txt+="...";
    }

    short_text=txt;
*/


    if(misl_i->using_external_classes){
        //Drawing the text into the pixmap

        p.setPen(QColor(txt_col[0]*255,txt_col[1]*255,txt_col[2]*255,txt_col[3]*255)); //set color
        p.setBrush(Qt::SolidPattern); // set fill style
        pixm.fill(QColor(0,0,0,0)); //clear color to 0
        p.drawText(rect,Qt::TextWordWrap | Qt::AlignCenter,short_text);
        p.end();

        if(id==2){//sample for testing
            d("saving texture");
            if (!pixm.save("./note.jpg",NULL,100)){d("bad save");}
        }
        //Loading it as a texture in GL
        //glEnable( GL_TEXTURE_2D );
            texture=misl_i->gl_w->bindTexture(pixm,GL_TEXTURE_2D,GL_RGBA,QGLContext::DefaultBindOption);
            //glBindTexture(GL_TEXTURE_2D,texture); //the manual way pixelates for some reason
            //pixm=QGLWidget::convertToGLFormat(pixm);
            //gluBuild2DMipmaps(GL_TEXTURE_2D, 4, pixm.width(), pixm.height(),GL_RGBA, GL_UNSIGNED_BYTE, pixm.bits());
        //glDisable( GL_TEXTURE_2D );
    }

    return 0;

}
int Note::init_links(){ //smqta koordinatite i skysqva teksta (ako trqbva) na vs outlinkove

float lx1,ly1,lx2,ly2;
float a2,b2,x2,y2,z2,r2x1,r2x2,r2y1,r2y2;
Link *ln;
//NoteFile *nf;

lx1=rx2-(rx2-rx1)/2; //koordinati na sredata na poleto (izpolzvam gi za linkovete)
ly1=ry2-(ry2-ry1)/2;

for(unsigned int n=0;n<outlink.size();n++){

//---------Smqtane na koordinatite za link-a---------------
ln = &outlink[n];
Note *target_note=misl_i->nf_by_id(nf_id)->get_note_by_id(ln->id);
x2=target_note->x;//koordinati na teksta
y2=target_note->y;
z2=target_note->z;
a2=target_note->a;//razmeri na kutiqta na teksta
b2=target_note->b;
r2x1=x2-0.01; //koordinati na poleto
r2y1=y2+0.01;
r2x2=x2+a2+0.01;
r2y2=y2-b2-0.01;
lx2=r2x2-(r2x2-r2x1)/2; //koordinati na sredata na poleto (izpolzvam gi za linkovete)
ly2=r2y2-(r2y2-r2y1)/2;

    if( ( ( (rx2>=r2x1)&&(rx1<=r2x1) ) || ( (rx2>=r2x2)&&(rx1<=r2x2) ) ) || ( (rx1>=r2x1)&&(rx2<=r2x2) ) ) { //ako nqkoi ot 2ta ryba na pole 2 zastypwa pole 1 ili ako ednoto pole napravo obhva6ta dr-to (t.e. poletata sa g/d edno nad drugo)

        if(ly1<=ly2){ //ako pole 2 e otgore
            ln->x1=lx1;
            ln->y1=ry1;
            ln->z1=z;
            ln->x2=lx2;
            ln->y2=r2y2;
            ln->z2=z2;
        }
        else { //ako pole 2 e ordolo
            ln->x1=lx1;
            ln->y1=ry2;
            ln->z1=z;
            ln->x2=lx2;
            ln->y2=r2y1;
            ln->z2=z2;
        }
    }
    else { //ako pole 2 ne e nad pole 1 slagame ot strani4nite povyrhnosti linkovete

        if(rx2<=r2x1){ //ako pole 2 e otdqsno na pole 1
            ln->x1=rx2;
            ln->y1=ly1;
            ln->z1=z;
            ln->x2=r2x1;
            ln->y2=ly2;
            ln->z2=z2;
        }

        if(rx1>=r2x2){ //ako pole 2 e otlqvo na pole 1
            ln->x1=rx1;
            ln->y1=ly1;
            ln->z1=z;
            ln->x2=r2x2;
            ln->y2=ly2;
            ln->z2=z2;
        }
    }

//--------Skysqvane na teksta v link-a-----------------
/*
    QRect rect(0,0,a*FONT_TRANSFORM_FACTOR,b*FONT_TRANSFORM_FACTOR),rect2;
    QImage pixm(a*FONT_TRANSFORM_FACTOR,b*FONT_TRANSFORM_FACTOR,QImage::Format_ARGB32);
    QPainter p(&pixm);

int resized=0,res;
std::string work_string;
float len=0,link_len=dottodot(ln->x1,ln->y1,ln->x2,ln->y2);

rect2=p.boundingRect(0,0,100,200,Qt::TextWordWrap,QString("..."));

float tochki_len=rect2.x();
if(link_len<tochki_len){
    ln->short_text=strdup("");
    return 0;}

work_string=ln->text;

again:

rect2=p.boundingRect(rect,Qt::TextWordWrap,QString(work_string.c_str()));

if(rect2.x()>link_len) {

resized=1;
work_string.resize(work_string.size()-1);
goto again;
}
if(resized){

res=stop(work_string.size()-3,0,MAX_STRING_LENGTH);
work_string.resize(res);
work_string+="...";
}
ln->short_text=strdup(work_string.c_str());
*/
    //ln->short_text=strdup(ln->text);


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
