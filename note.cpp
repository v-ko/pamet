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

#include "petko10.h"

Note::Note()
{
    x=0;
    y=0;
    z=0;
    a=12;
    b=a/A_TO_B_NOTE_SIZE_RATIO;
    font_size=1;
    selected=false;
    nf_name="";
    type=NOTE_TYPE_NORMAL_NOTE;
    txt_col[0]=0;//r
    txt_col[1]=0;//g
    txt_col[2]=1;//b
    txt_col[3]=1;//a
    bg_col[0]=0;
    bg_col[1]=0;
    bg_col[2]=1;
    bg_col[3]=0.5;
    img = new QImage(1,1,QImage::Format_ARGB32_Premultiplied);//so we have a dummy pixmap for the first init
    text_is_shortened=false;
    auto_sizing_now=false;
}
Note::~Note()
{
    delete img;
}

int Note::calculate_coordinates()
{
    //Coordinates for the note rectangle
    rx=x+a;
    ry=y+b;
    pixm_real_size_x = a*FONT_TRANSFORM_FACTOR; //pixmap real size (bloated to have better quality on zoom)
    pixm_real_size_y = b*FONT_TRANSFORM_FACTOR;

    return 0;
}
int Note::store_coordinates_before_move()
{
    move_orig_x=x; //store the coordinates before a move command
    move_orig_y=y;

    return 0;
}
int Note::adjust_text_size()
{
    int base_it,max_it,probe_it; //iterators for the shortening algorythm

    //-------Init painter for the text shortening----------
    QRectF text_field(0,0,a*FONT_TRANSFORM_FACTOR,b*FONT_TRANSFORM_FACTOR),text_field_needed;
    QString txt = text_for_shortening;

    QFont font("Halvetica");
    font.setPixelSize(font_size*FONT_TRANSFORM_FACTOR);

    QPainter p(img);//just a dummy painter
    p.setFont(font);

    //------Determine alignment---------------
    if(text_for_shortening.contains("\n")){//if there's more than one row
        has_more_than_one_row=true;
        alignment = Qt::AlignLeft;
    }else{
        has_more_than_one_row=false;
        alignment = Qt::AlignCenter;
    }

    //=========Shortening the text in the box=============
    text_is_shortened=false; //assume we don't need shortening

    p.setFont(font);

    txt=text_for_shortening;
    base_it=0;
    max_it=text_for_shortening.size();
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
        txt=text_for_shortening;
    }

    text_is_shortened=true;
    txt.resize(max_it-3);
    txt+="...";

    after_shortening:
    text_for_display=txt;

    return 0;
}
int Note::check_text_for_links(MisliDir *md) //there's an argument , because search inits the notes out of their dir and still needs that function (the actual linking functionality is not needed then)
{
    //-------Check if we have a link to a file-----------
    if (text.startsWith(QString("this_note_points_to:"))){
        address_string=q_get_text_between(text,':',0,200); //get text between ":" and the end
        address_string=address_string.trimmed(); //remove white spaces from both sides
        text_for_shortening = address_string; //set the note file name as text for displaying
        type=NOTE_TYPE_REDIRECTING_NOTE;
        if(md->nf_by_name(address_string)==NULL){//if we have a wrong/missing name
            text_for_shortening=QObject::tr("missing note file");
        }
    }
    return 0;
}
int Note::check_for_file_definitions()
{
    //QString string;
    QFile file;

    if (text.startsWith(QString("define_text_file_note:"))){
        //if(type==NOTE_TYPE_TEXT_FILE_NOTE){return 0;} //if we've defined the file already - we don't need to read it a thousand times
        address_string=q_get_text_between(text,':',0,200); //get text between ":" and the end
        address_string=address_string.trimmed(); //remove white spaces from both sides
        file.setFileName(address_string);
        if(file.open(QIODevice::ReadOnly)){
            text_for_shortening = file.read(10000); //10 kb max
        }else{
            text_for_shortening = "Failed to open file.";
        }
        type=NOTE_TYPE_TEXT_FILE_NOTE;
        return 0;
    }

    if (text.startsWith(QString("define_picture_note:"))){
        //if(type==NOTE_TYPE_PICTURE_NOTE){return 1;}
        address_string=q_get_text_between(text,':',0,200); //get text between ":" and the end
        address_string=address_string.trimmed(); //remove white spaces from both sides
        text_for_shortening = "";
        type=NOTE_TYPE_PICTURE_NOTE;
        //draw_pixmap();//inits the image only here , so we don't open the file a thousand times
    }

    return 0;
}
int Note::check_text_for_system_call_definition()
{
    if (text.startsWith(QString("define_system_call_note:"))){
        address_string=q_get_text_between(text,':',0,200); //get text between ":" and the end
        address_string=address_string.trimmed(); //remove white spaces from both sides
        text_for_shortening = address_string;
        type=NOTE_TYPE_SYSTEM_CALL_NOTE;
        return 1;
    }
    return 0;
}
int Note::draw_pixmap()
{
    if(type==NOTE_TYPE_PICTURE_NOTE){
        delete img;
        img = new QImage(address_string);
        if( !img->isNull() ) {
            return 0;
        }
        else {
            text_for_shortening="Not a valid picture.";
            text_for_display="Not a valid picture.";
            type=NOTE_TYPE_NORMAL_NOTE;
        }
    }

    delete img;
    img = new QImage(pixm_real_size_x,pixm_real_size_y,QImage::Format_ARGB32_Premultiplied);
    img->fill(Qt::transparent);

    QFont font("Halvetica");
    font.setPixelSize(font_size*FONT_TRANSFORM_FACTOR);
    font.setStyleStrategy(QFont::PreferAntialias); //style aliasing

    QPainter p(img);
    p.setFont(font);
    p.setRenderHint(QPainter::TextAntialiasing);

    //Draw the note field
    p.fillRect(0,0,pixm_real_size_x,pixm_real_size_y,QBrush(QColor(bg_col[0]*255,bg_col[1]*255,bg_col[2]*255,bg_col[3]*255)));

    //Draw the text
    p.setPen(QColor(txt_col[0]*255,txt_col[1]*255,txt_col[2]*255,txt_col[3]*255)); //set color
    p.setBrush(Qt::SolidPattern); //set fill style
    p.drawText(QRectF(NOTE_SPACING*FONT_TRANSFORM_FACTOR,NOTE_SPACING*FONT_TRANSFORM_FACTOR,a*FONT_TRANSFORM_FACTOR,b*FONT_TRANSFORM_FACTOR),Qt::TextWordWrap | alignment,text_for_display);

    return 0;
}


int Note::init() //calculate the coords of the box around the note , shortens the text and draw them in a pixmap
{
    if(!misli_dir->using_gui){return 0;} //if there's no gui we don't need init()
    calculate_coordinates();

    //if(misli_dir->misli_i->misli_w->canvas->move_on){return 0;} //if we're moving the note there's no need to redraw it
    store_coordinates_before_move();

    if(text.size()>MAX_NOTE_TEXT_SIZE) text_for_shortening = text.left(MAX_NOTE_TEXT_SIZE);
    else text_for_shortening=text;

    type=NOTE_TYPE_NORMAL_NOTE; //assuming the note isn't special

    check_text_for_links(misli_dir);
    check_for_file_definitions();
    check_text_for_system_call_definition();

    adjust_text_size();

    //if(auto_sizing_now){return 0;} //in auto_size we need only the above routine to calculate when the size is right
    //if( (type==NOTE_TYPE_PICTURE_NOTE) && (text_for_display.size()==0) ){ return 0;} //we don't need to load the file again, since the resizing is done in the rendering function
    draw_pixmap();

    return 0;

}
void Note::auto_size() //practically a cut down version of init that only changes a and b if there's not enough space for the text and calls init() afterwards
{
    auto_sizing_now=true;
    while(text_is_shortened){
        a+=2;
        b=a/A_TO_B_NOTE_SIZE_RATIO;

        adjust_text_size();
    }
    while(!text_is_shortened){
        if(b<=MIN_NOTE_B){break;}
        b--;
        adjust_text_size();
    }
    b++;init();

    while(!text_is_shortened){
        if(a<=MIN_NOTE_A){break;}
        a--;
        adjust_text_size();
    }
    a++;

    auto_sizing_now=false;
    a=stop(a,MIN_NOTE_A,MAX_NOTE_A);
    b=stop(b,MIN_NOTE_B,MAX_NOTE_B);
    calculate_coordinates();
    store_coordinates_before_move();
    adjust_text_size();
    draw_pixmap();
}

int Note::init_links(){ //smqta koordinatite

    float lx1,ly1,lx2,ly2;
    float a2,b2,x2,y2,z2,r2x1,r2x2,r2y1,r2y2;
    Link *ln;

    lx1=rx-(rx-x)/2; //koordinati na sredata na poleto (izpolzvam gi za linkovete)
    ly1=ry-(ry-y)/2;

    for(unsigned int n=0;n<outlink.size();n++){

    //---------Smqtane na koordinatite za link-a---------------
    ln = &outlink[n];
    Note *target_note=misli_dir->nf_by_name(nf_name)->get_note_by_id(ln->id);
    if(target_note==NULL){ //if there's no note with the specified link id
        qDebug()<<"In notefile '"<<nf_name<<"' , note '"<<text<<"' (id:"<<id<<") has an invalid outlink, id:"<<ln->id;
        continue;
    }
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
int Note::correct_links()
{
    Note *ntt;
    //korigirame izhodq6tite linkove
    init_links();

    //korigirame vhodq6tite linkove
    for(unsigned int l=0;l<inlink.size();l++){
        int inl=inlink[l];
        ntt=misli_dir->nf_by_name(nf_name)->get_note_by_id(inl);
        ntt->init_links();
    }

    return 0;
}
int Note::link_to_selected()
{
    if(nf_name!=misli_dir->curr_nf()->name){d("bad call for link_to_selected");exit(1);} //if the function is called for a note that's not displayed

    Link ln;

    for(unsigned int i=0;i<misli_dir->curr_nf()->note.size();i++){ //za vseki note ot current
        if( misli_dir->curr_nf()->note[i]->selected && ( misli_dir->curr_nf()->note[i]->id != id ) ){ //ako e selectiran
            inlink.push_back( misli_dir->curr_nf()->note[i]->id ); //dobavi na noviq link edin inlink s id-to na selectiraniq
            ln.id=id; //dobavi na selectiraniq edin outlink s id-to na noviq
            misli_dir->curr_nf()->note[i]->outlink.push_back(ln);
            misli_dir->curr_nf()->note[i]->init_links();
        }

    }


    return 0;
}

int Note::add_link(Link *ln) //adds the link (+inlink), doesn't init it
{
    Link lnk;

    if(misli_dir->nf_by_name(nf_name)->get_note_by_id(ln->id)!=NULL){ //if the note at the given id exists - create the link

        lnk.id=ln->id;
        lnk.text=ln->text;
        outlink.push_back(lnk); //in the note

        misli_dir->nf_by_name(nf_name)->get_note_by_id(ln->id)->inlink.push_back(id); //in the target note
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

    Note *nt=misli_dir->nf_by_name(nf_name)->get_note_by_id(outlink[position].id); //delete the target's inlink first
    nt->delete_inlink_for_id(id);

    outlink.erase(outlink.begin()+position); //delete the outlink

    return 0;
}
void Note::center_eye_on_me()
{
    if(misli_dir->using_gui){


        misli_dir->nf_by_name(nf_name)->eye_x = x+a/2;
        misli_dir->nf_by_name(nf_name)->eye_y = y+b/2;
        misli_dir->set_current_note_file(nf_name); //set the parent note file as current
        misli_dir->misli_i->set_current_misli_dir(misli_dir->notes_dir); //set this notes dir as current
        //misli_dir->misli_i->misli_dg->misli_w->canvas->update();
    }
}
