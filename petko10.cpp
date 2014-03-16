#include <sstream>
#include "petko10.h"

//spomen:Nova sistema za opredelqne na posoka (na gledane napr) v gradusi : na koordinatnata sistema horizontalniqt ygyl vyrvi ot z kym x osta (ygyl=0 = z osta) . vertikalniqt ygyl trygva pak ot z (tam e 0) nadolo kym "na4aloto" na y osta . Praviloto e 4e yglite se vyrtqt okolo osite po 4asovnikovata. v GRAV3D ne e taka.

double pi=3.1415926535897932384626433832795028841971693993751058209749;
double AngleOfSight=45;
double GravConst=6.6738481; //gravitacionna const


int pouse=1;
float speed=0.2; //tuk e za6toto lense to eye e tuka
int error=0,stopid=0; //za sybirane na gre6ki
int dbg=0;



char *true_false_to_string(int x){
    if(x){return strdup("TRUE");}
    else if(x==0){return strdup("FALSE");}
    else return strdup("true_false_to_string:out of range");
}
/*
char *GetTextBetween(char *source_string, char A, char B, int length) { //vry6ta pointer kym teksta mejdu A i B (dvata markera trqbva da sa v blizkite length bukvi. Ako se podade R na A - zapisva ot na4alo ,a ako se podade E na B zapisva do kraq

int br=0; //broq4
char ch='>'; //bukva koqto se gleda v momenta
int recording=0; //flag dali sme m/u znacite za zapis
int startrec=0 ; //poziciq na na4aloto na zpisa
char *target; //extractnat zapis

if(A=='R'){recording=1;}
if(source_string==NULL){return NULL;}

for (br=0;br<=length;br++){  //extractvame imeto
    if(source_string[br]=='\0'){break;}// end of the string
    ch=source_string[br];
    if( (ch==A) && (!recording) ) { //ako vidi6 kraq na taga zapo4ni da "zapisva6"
        recording=1;
        startrec=br+1;
        continue;
    } else if((ch==B) && recording){ //ako vidi6 na4aloto na sledva6tiq tag prikliu4i zapisa
        recording=0;
        target=strndup(&source_string[startrec],br-startrec);
        return target;
    }

}

if((recording==1) && (B=='E')) {return strndup(&source_string[startrec],br-startrec);} //ako vtoriqt tag e E zapisva do kraq na string-a

return NULL;

}
char *GetTextBetween(char *source_string, char A, int length) { //vry6ta pointer kym teksta mejdu A i B (dvata markera trqbva da sa v blizkite length bukvi. Ako se podade R na A - zapisva ot na4alo ,a ako se podade E na B zapisva do kraq
                                                                //tazi vry6ta do kraq
int br=0; //broq4
char ch='>'; //bukva koqto se gleda v momenta
int recording=0; //flag dali sme m/u znacite za zapis
int startrec=0 ; //poziciq na na4aloto na zpisa

if(A=='R'){recording=1;}
if(source_string==NULL){return NULL;}

for (br=0;br<=length;br++){  //extractvame imeto
    if(source_string[br]=='\0'){break;}// end of the string
    ch=source_string[br];
    if( (ch==A) && (!recording) ) { //ako vidi6 kraq na taga zapo4ni da "zapisva6"
        recording=1;
        startrec=br+1;
        continue;
    }

}

if((recording==1) ) {return strndup(&source_string[startrec],br-startrec);} //ako vtoriqt tag e E zapisva do kraq na string-a

return NULL;

}
*/
bool FileExist(const char* FileName)
{
struct stat my_stat;
return (stat(FileName, &my_stat) == 0);
}

int sign (float x){ //nulata q vry6ta polojitelna
if (x>=0){return 1;}
else {return (-1);}
}

int toggle(int x,int t1,int t2){ //toggle-va m/u t1 i t2
    if(x==t1){return t2;
    }
    else if(x==t2){
        return t1;
    }
    else{
        printf("toggle:out of range x:%i",x);
        return -1;
    }}

int d(const char * ch){printf("%s\n",ch);return 0;}

float stop(float x,float min, float max){ //ako x e izvyn range-a min-max go vry6ta na syotvetnata granica
stopid++;

if (x<min) {

//printf("STOP %i dade otklonenie pod minimuma %f, vry6tam min:%f\n",stopid,x-min,min);
x=min;

}
else if (x>max){

//printf("STOP %i dade otklonenie nad maximuma %f, vry6tam max:%f\n",stopid,x-max,max);
x=max;

}

return x;
}
/*
int stop(int x,int min, int max){ //ako x e izvyn range-a min-max go vry6ta na syotvetnata granica
stopid++;

if (x<min) {

//printf("STOP %i dade otklonenie pod minimuma %f, vry6tam min:%f\n",stopid,x-min,min);
x=min;

}
else if (x>max){

//printf("STOP %i dade otklonenie nad maximuma %f, vry6tam max:%f\n",stopid,x-max,max);
x=max;

}

return x;
}*/

float prelei(float& x,float maxX,float& y){ //dobavq y v x i ako se stigne do maxX return-va ostatyka (y se izprazva)
float tmp;

x+=y;
y=0;

if (x>maxX){
    tmp=x-maxX;
    x=maxX;
    return tmp;
}
else {return 0;}

}

int prelei(long int& x,long int maxX,long int& y){ //dobavq y v x i ako se stigne do maxX return-va ostatyka (y se izprazva)
int tmp;

x+=y;
y=0;

if (x>maxX){
    tmp=x-maxX;
    x=maxX;
    return tmp;
}
else {return 0;}

}

float mod(float x){

if (x>=0){return x;}
else {return -x;}

}

float rnd(float range){
    if(range==0){return 0;}
    return float((double(rand())/double(RAND_MAX))*double(range));
}

float Scale(float Interval_1,float Interval_2,float Stoinost) // vry6ta 4isloto zaema6to sy6tata 4ast ot Interval_2 kakto Stoinost zaema ot Interval_1
{
    Stoinost = Stoinost*Interval_2/Interval_1;
    return Stoinost;
}

bool point_intersects_with_rectangle(float x, float y, float rx1,float ry1, float rx2,float ry2){ // to4ka (x,y) i pravoygylnik s dolen ygyl (rx1,ry1) i goren ygyl rx2,ry2

if ( (x>=rx1 && y>=ry1) &&  (x<=rx2 && y<=ry2 ) ) { return 1; }
else return 0;

}

int iiTranslatef (float& x , float& y , float& z , float vectorx , float vectory , float vectorz){ //premestvame to4ka (x,y,z) s vector (0,0,0)-(vectorx,vectory,vectorz)

x += vectorx;
y += vectory;
z += vectorz;

return 0;
}

int prenesi(float x0,float y0,float x1,float y1,float x2,float y2,float& x3,float& y3) //prenasq vektora (v to4ki) (1;0) na poziciq (2;3) (zapazvat se posokata i dyljinata)
{
    x3 = x2 - (x1 - x0);
    y3 = y2 - (y1 - y0);
    return 0;
}

int prenesi3(float x0,float y0,float z0,float x1,float y1,float z1,float x2,float y2,float z2,float& x3,float& y3,float& z3)
{
    x3 = x2 - (x1 - x0);
    y3 = y2 - (y1 - y0);
    z3 = z2 - (z1 - z0);
    return 0;
}

int roun(double a) {
if(a>=0){return int(a + 0.5);}
else {return int(a-0.5);}
}

int roun(float a) {
if(a>=0){return int(a + 0.5);}
else {return int(a-0.5);}
}

float dottodot (float ax,float ay,float bx,float by)
{
    float tX,tY;

    tX = bx - ax;
    tY = by - ay;

    return (sqrt( pow(tX ,2) + pow(tY, 2) ));
}

/*double dottodot (float ax,float ay,float bx,float by) //ax,ay sa samo formalno float za da se razli4avat 2te funkcii - float/double
{
    float tX,tY;
    double F;

    tX = bx - ax;
    tY = by - ay;

    return (sqrt( pow(double(tX) ,2) + pow(double(tY), 2) ));
}*/

float dottodot3 (float ax,float ay,float az,float bx,float by,float bz)
{
    float tX,tY,tZ;
    float F;

    tX = bx - ax;
    tY = by - ay;
    tZ = bz - az;

    F = sqrt( pow(tX ,2) + pow(tZ, 2) );
    F = sqrt( pow(F ,2) + pow(tY, 2) );
    return (F);
}

int TochkaOtPrava(float ax,float ay,float az,float bx,float by,float bz,float& x,float& y,float& z,float A){ //vryshta to4ka ot pravata a-b ,koqto e na razstoqnie A ot a
float a;
a=dottodot3(ax,ay,az,bx,by,bz);
x=bx-ax;
y=by-ay;
z=bz-az;

x=ax+Scale(a,x,A);
y=ay+Scale(a,y,A);
z=az+Scale(a,z,A);

return 0;
}

float corr(float Ang){ //dyrji ygyla v ramkite na 0-360 (no ne kato stop , a prosto vse edno prevyrta strelkata)
 if (Ang>=360 && Ang<720){return (Ang-360);}
 else if (Ang<0 && Ang>=-360){return (360+Ang);}
 else if (Ang>=0 && Ang<=360){return Ang;}
 else {printf("corr:ERROR:angle bug, angle: %f\n",Ang);return 0;}
}
double corr(double Ang){
     if (Ang>=360 && Ang<720){return (Ang-360);}
     else if (Ang<0 && Ang>=-360){return (360+Ang);}
     else if (Ang>=0 && Ang<=360){return Ang;}
     else {printf("corr:ERROR:angle bug, angle: %f\n",Ang);return 0;}
}

double distance_to_line(double x,double y,double z,double lx1,double ly1,double lz1,double lx2,double ly2,double lz2)//there's only one closest distance from a point to a line and this func returns it
{

    double a,b,c,s,h;

    a=dottodot3(lx1,ly1,lz1,lx2,ly2,lz2);
    b=dottodot3(x,y,z,lx2,ly2,lz2);
    c=dottodot3(x,y,z,lx1,ly1,lz1);
    s=(a+b+c)/2;

    h = ( 2*sqrt( s*(s-a)*(s-b)*(s-c) ) )/a;

    return h;
}

int Inv(int ScrX,int x) //ako x e 1ta 4ast ot intervala ScrX razdelen na 2 , to funkciqta vry6ta 2ta
{
    x=ScrX-x;
    return x;
}

float Inv(float ScrX,float x)
{
    x=ScrX-x;
    return x;
}

double Inv(double ScrX,double x)
{
    x=ScrX-x;
    return x;
}

int Kvadrant(float ax ,float ay,float bx,float by) // 1..4 - kvadranta v koito e B sprqmo A
{                                          // 5..8 - ako B e na nqkoq ot nulite m/u kvadrantite - syotvetno 5 m/u I/II ,6 m/u II/III ...
    float tbx=bx-ax ;                        // 9 - ako A i B syvpadat
    float tby=by-ay ;

    if(tbx>0)
    {
        if(tby>0) {return 1;}
        if(tby<0) {return 4;}
    }
    if(tbx<0)
    {
        if(tby>0) {return 2;}
        if(tby<0) {return 3;}
    }

    if(tbx==0)
    {
        if(tby>0) {return 5;}
        if(tby<0) {return 7;}
    }

    if(tby==0)
    {
        if(tbx>0) {return 8;}
        if(tbx<0) {return 6;}
    }

    if( (tbx==0)&&(tby==0) ) {return 9;}
    else {return 0;}

}

int GetFunc (float ox,float oy,float ax,float ay,float bx,float by,float& a,float& c) //zadavat se 2 to4ki (A i B) ot lineina funkciq
                                                                          //(ot tipa y=ax+c) i se polu4avat a i c na funkciqta
                                                                          //to4kite se izravnqvat po ox,oy (ox,oy e 0-ta)
{
    ax=ax-ox;
    ay=ay-oy;
    bx=bx-ox;
    by=by-oy;

    if (bx==ax){error++;return ax;}                                 //ako funkciqta e otvesna liniq GetFunc=x na vs to4ki ot liniqta

    a = ((by-ay))/((bx-ax)) ;
    c = ay - a*ax;

return 0;
}

float GetInverse(float bx,float by,float ax,float ay,float cx,float cy) //vry6ta: 1 ako ygyla BAC<180,2 ako BAC>180 i 0,90,180,270 syotvetno ako BAC=0,90,180,270 (vyrti po 4asonikovata)
{   //testvana                                                         //ako ima gre6ka vry6ta GetInverse>360 (gre6kite sa opisani na mqsto) vry6ta nula pri syvpadenie na to4kite
    int KvBA,KvCA,tmp ; //kvadranta v koito e B sprqmo A i syotv. C sprqmo A
    float a=0,c=0; // za funkciite
    KvBA = Kvadrant(ax,ay,bx,by);
    KvCA = Kvadrant(ax,ay,cx,cy);

if ( (KvBA<=4)&&(KvCA<=4) ) //ako nqma ni6to po liniite (osite)
{
    if( KvBA != KvCA ) //ako sa razl kvadranti
    {

        switch (KvBA-KvCA)
        {
            case 1:
            case (-3):
            return 2;

            break;

            case (-1):
            case 3:
            return 1;
            break;

            case 2:
            GetFunc(ax,ay,bx,by,cx,cy,a,c);
            if ( ( (a>0)&&(c>0) ) || ( (a<0)&&(c<0) ) ) {return 2;}
            else if (c==0) {return 180;}
            else {return 1;}
            break;

            case (-2):
            GetFunc(ax,ay,bx,by,cx,cy,a,c);
            if ( ( (a>0)&&(c>0) ) || ( (a<0)&&(c<0) ) ) {return 1;}
            else if (c==0) {return 180;}
            else {return 2;}
            break;
        }

    }
    else //ako sa ednakvi kvadranti
    {

        GetFunc(cx,cy,ax,ay,bx,by,a,c);
        if (c==0) { return 0;}
        if (ay>by)
        {
            if ( ( (a<0)&&(c>0) ) || ( (a>0)&&(c<0) ) ) {return 2;}
            else {return 1;}
        }
        else
        {
            if ( ( (a<0)&&(c>0) ) || ( (a>0)&&(c<0) ) ) {return 1;}
            else {return 2;}
        }
    }
}
else if ( (KvBA==9)||(KvCA==9) ) {return 0;} //ako C ili B syvpada s A
else if ((KvBA>=5)&&(KvCA<=4)) //ako B e na liniq ,a C v kvadrant
    {
        switch ((KvBA-4)-KvCA) {
        case 1:
        case 0:
        case (-3):
        return 2;
        break;
        default:
        return 1;
        }
    }
else if ((KvBA<=4)&&(KvCA>=5)) //ako C e na liniq a B v kvadrant
    {
        switch ((KvBA-4)-KvCA) {
        case 0:
        case 1:
        case (-3):
        return 1;
        default:
        return 2;
        break;
        }    }
else if ((KvBA>=5)&&(KvCA>=5)) //ako B i C sa na liniq
    {

        tmp=KvBA-KvCA;
        switch (tmp)
        {
            case (-1):
            case 3:
            return 90;
            break;

            case 2:
            case (-2):
            return 180;
            break;

            case 1:
            case (-3):
            return 270;
            break;

            case 0:
            return 0;
            break;
        }
    return 361; //error nqkoi ot 2ta kvadranta ne si e v stoinostite i syotv razlikata ne e zalovena ot switch
    }
return 362; //stignat e kraq na funkciqta bez da e ustanoven ygyla
} //krai na func

float GetAng(float bx,float by,float ax,float ay,float cx,float cy) //vry6ta ygyla skliu4en mejdu to4kite BAC (po 4asovnikovata)
{   //testvana                                                     //ako se okaje 4e tova bugva Render mu kaji da vry6ta ygli samo m/u 0 i 180

    int inverse = GetInverse(bx,by,ax,ay,cx,cy);
    float tA,tB,tC,cos,Ang=0; //temp strani

    if ( (inverse==1)|(inverse==2) ) {

    tA = dottodot(bx,by,cx,cy);
    tB = dottodot(ax,ay,cx,cy);
    tC = dottodot(ax,ay,bx,by);

    cos = (pow(tB,2) + pow(tC,2) - pow(tA,2))/(2*tB*tC);
    Ang = (acos(cos)*180)/pi;
    }
    else{
    Ang=inverse;
    }

    if (inverse==2) {Ang = 360-Ang;}
    return (Ang);

}

float g1(lense L,Point T,float size) //smqta goleminata na obekta
{
float h = T.z - L.z;
float g1;
if (h==0) {return 0;}

g1 = Scale(pi,180,atan((float(size) / 2) / sqrt(2*pow(float(h),2)))) * float(L.Scr1) / float(L.s1);
return g1;
}

int Rotation(float ox,float oy,float& x,float& y,double alfa) //gre6ki ne dava ,vry6ta samo 0 za sega
{
    if(alfa==0||alfa==360){return 0;}
    double c,tX=0,tY=0;

    c = dottodot(ox,oy,x,y);

    alfa += double(GetAng(ox+100,oy,ox,oy,x,y));
    alfa = (corr(alfa)*pi)/180;// popravka ako e izvyn intervala i obry6tane v radiani

    tX = cos(alfa)*c;
    x = ox + float(tX);
    tY = sin(alfa)*c;
    y = oy + float(tY);

    return 0;
}

int Render(lense L,Point T,float& x, float& y)
{
    float h,v;
    float c = dottodot(0,0,T.x,T.z);

    // Izravnqvane
    T.x-=L.x;
    T.y-=L.y;
    T.z-=L.z;

      //3te rotacii

    error+=Rotation(0,0,T.x,T.z,L.h);
    error+=Rotation(0,0,T.x,T.y,L.r);
    error+=Rotation(0,0,c,T.y,corr(-L.v)); //minus za6toto rotation-a vyrti na obratno

    h = GetAng(100,0,0,0,T.x,T.z);
    T.x=cos(h*pi/180)*c;
    T.z=sin(h*pi/180)*c;

    //display

      // namirane na vektora LT izrazen v ygli
    //h e namereno gore
    v = GetAng(0,100,0,0,c,T.y);

     //proverka dali to4kata e v zritelnoto pole

    float grH1,grH2,grV1,grV2; //granici

    grH1=(180-float(L.s1))/2;
    grH2=(180+float(L.s1))/2;
    grV1=(180-float(L.s2))/2;
    grV2=(180+float(L.s2))/2;


    if ( (h>=grH1)&&(h<=grH2)&&(v>=grV1)&&(v<=grV2) )
    {
        h-=grH1;
        v-=grV1;

        h=Inv(float(L.s1),h);
        //v si ostava za6toto se izobrazqva po obratnata s-ma

        x=Scale(L.s1,L.Scr1,h);
        y=Scale(L.s2,L.Scr2,v);

        return 0;
    }
    else
    {
        x=0;
        y=0;
        return 1; //to4kata e izvyn zritelnoto pole
    }
error+=1;return 0; //po nqkakva pri4ina e presko4ena proverkata i e stignat kraq
}

int LenseToEye (lense L, Eye& eye){ //obry6ta yglite na gledane ot lense vyv up i scene vectori na eye

float sceneR=speed; //razstoqnie do scenata

eye.x=L.x;
eye.y=L.y;
eye.z=L.z;

eye.scenex = L.x;
eye.sceney = L.y;
eye.scenez = L.z + sceneR;
Rotation (L.x,L.z,eye.scenex,eye.scenez,L.h); //zavyrtame v horizontalnata ravnina
Rotation (L.y,0,eye.sceney,sceneR,corr(-L.v)); //zavyrtame v ravninata na osite y i r (polu4ena pri prednoto zavyrtane posoka) (L.v e naobratno 6toto komp ekranyt e skapan i e otgore nadolo
//printf("R: %f \n",sceneR);
eye.scenex = L.x + sin(L.h*pi/180)*sceneR; //namirame 2ta koordinata ot poziciqta na to4kata po osta r
eye.scenez = L.z + cos(L.h*pi/180)*sceneR;

return 0;
}

void check_vital_string(std::string string, const char* model_value)
{
    if(string.compare(model_value)!=0) {
        std::cerr<<"Vital string didnt check: "<<string<<";should have been : "<<model_value;
        exit(-1);
    }
}
