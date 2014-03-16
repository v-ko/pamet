#ifndef PETKO10_H
#define PETKO10_H

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <iostream>
#include <cstring>
#include <fstream>
#include <sstream>
#include <sys/stat.h>

//spomen:Nova sistema za opredelqne na posoka (na gledane napr) v gradusi : na koordinatnata sistema horizontalniqt ygyl vyrvi ot z kym x osta (ygyl=0 = z osta) . vertikalniqt ygyl trygva pak ot z (tam e 0) nadolo kym "na4aloto" na y osta . Praviloto e 4e yglite se vyrtqt okolo osite po 4asovnikovata. v GRAV3D ne e taka.

extern double pi;
extern double AngleOfSight;
extern double GravConst; //gravitacionna const

extern int pouse;
extern float speed; //tuk e za6toto lense to eye e tuka
extern int error,stopid; //za sybirane na gre6ki
extern int dbg ;


struct Eye {

float x, y, z;//mqsto na okoto
float scenex, sceney, scenez;  //vryh na vektora za posoka na okoto
float upx, upy, upz;  //vryh na vektora koito e "gore" za okoto
};

struct lense {
    float x,y,z;
    float h,v,r;//dvata ygyla opredelq6ti posokata na pogleda i r- opredelq6t rotaciqta okolo osta (vektora) na tazi posoka , h- horizontala , v - verticala
    int s1,s2,Scr1,Scr2; //s i Scr sa syotvetno 6iro4ina na le6tata i golemina v pixeli na ekrana za 1 i 2 koito sa syotvetno horizontala i vertikala
};

struct Point {
    float x,y,z;
};

struct SObekt { //sferi4en obekt - ima masa i vektor na dvijenie
    float x0,y0,z0,x,y,z;
    float m;
};

char *true_false_to_string(int x);

char *GetTextBetween(char *source_string, char A, char B, int length); //vry6ta pointer kym teksta mejdu A i B (dvata markera trqbva da sa v blizkite length bukvi. Ako se podade R na A - zapisva ot na4alo ,a ako se podade E na B zapisva do kraq
char *GetTextBetween(char *source_string, char A, int length) ; //tazi vry6ta do kraq

bool FileExist(const char* FileName);

int sign (float x); //nulata q vry6ta polojitelna

int toggle(int x,int t1,int t2); //toggle-va m/u t1 i t2

int d(const char * ch);//printf-s the string-a (debugging)

float stop(float x,float min, float max); //ako x e izvyn range-a min-max go vry6ta na syotvetnata granica

float prelei(float& x,float maxX,float& y); //dobavq y v x i ako se stigne do maxX return-va ostatyka (y se izprazva)
int prelei(long int& x,long int maxX,long int& y);

float mod(float x); //modul

float rnd(float range); //random number from 0 to range

float Scale(float Interval_1,float Interval_2,float Stoinost); // vry6ta 4isloto zaema6to sy6tata 4ast ot Interval_2 kakto Stoinost zaema ot Interval_1

bool point_intersects_with_rectangle(float x, float y, float rx1,float ry1, float rx2,float ry2); // to4ka (x,y) i pravoygylnik s dolen ygyl (rx1,ry1) i goren ygyl rx2,ry2

int iiTranslatef (float& x , float& y , float& z , float vectorx , float vectory , float vectorz); //premestvame to4ka (x,y,z) s vector (0,0,0)-(vectorx,vectory,vectorz)

int prenesi(float x0,float y0,float x1,float y1,float x2,float y2,float& x3,float& y3); //prenasq vektora (v to4ki) (1;0) na poziciq (2;3) (zapazvat se posokata i dyljinata)

int prenesi3(float x0,float y0,float z0,float x1,float y1,float z1,float x2,float y2,float z2,float& x3,float& y3,float& z3);

int roun(double a) ;

int roun(float a) ;

float dottodot (float ax,float ay,float bx,float by);

float dottodot3 (float ax,float ay,float az,float bx,float by,float bz);

int TochkaOtPrava(float ax,float ay,float az,float bx,float by,float bz,float& x,float& y,float& z,float A); //vryshta to4ka ot pravata a-b ,koqto e na razstoqnie A ot a

float corr(float Ang); //dyrji ygyla v ramkite na 0-360 (no ne kato stop , a prosto vse edno prevyrta strelkata)
double corr(double Ang);

double distance_to_line(double x,double y,double z,double x1,double y1,double z1,double x2,double y2,double z2); //there's only one closest distance from a point to a line and this func returns it

int Inv(int ScrX,int x); //ako x e 1ta 4ast ot intervala ScrX razdelen na 2 , to funkciqta vry6ta 2ta

float Inv(float ScrX,float x);

double Inv(double ScrX,double x);

int Kvadrant(float ax ,float ay,float bx,float by); // 1..4 - kvadranta v koito e B sprqmo A
                                          // 5..8 - ako B e na nqkoq ot nulite m/u kvadrantite - syotvetno 5 m/u I/II ,6 m/u II/III ...
                                  // 9 - ako A i B syvpadat

int GetFunc (float ox,float oy,float ax,float ay,float bx,float by,float& a,float& c); //zadavat se 2 to4ki (A i B) ot lineina funkciq
                                                                          //(ot tipa y=ax+c) i se polu4avat a i c na funkciqta
                                                                          //to4kite se izravnqvat po ox,oy (ox,oy e 0-ta)


float GetInverse(float bx,float by,float ax,float ay,float cx,float cy); //vry6ta: 1 ako ygyla BAC<180,2 ako BAC>180 i 0,90,180,270 syotvetno ako BAC=0,90,180,270 (vyrti po 4asonikovata)
   //testvana                                                         //ako ima gre6ka vry6ta GetInverse>360 (gre6kite sa opisani na mqsto) vry6ta nula pri syvpadenie na to4kite

float GetAng(float bx,float by,float ax,float ay,float cx,float cy); //vry6ta ygyla skliu4en mejdu to4kite BAC (po 4asovnikovata)
   //testvana                                                     //ako se okaje 4e tova bugva Render mu kaji da vry6ta ygli samo m/u 0 i 180


float g1(lense L,Point T,float size); //smqta goleminata na obekta

int Rotation(float ox,float oy,float& x,float& y,double alfa); //gre6ki ne dava ,vry6ta samo 0 za sega

int Render(lense L,Point T,float& x, float& y);

int LenseToEye (lense L, Eye& eye);

void check_vital_string(std::string string, const char* model_value);

#endif //PETKO10_H
