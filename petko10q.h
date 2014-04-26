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

#ifndef PETKO10Q_H
#define PETKO10Q_H

#include <QString>
#include <QStringList>

char * q_get_text_between(char *source_string, char A, char B, int length);
char * q_get_text_between(const char *source_string, char A, char B, int length);
QString q_get_text_between(QString txt, char A, char B, int length=-1);
int q_get_value_for_key(QString string, QString key, QString& result); //string should be a list of INI type key-value pairs
int q_get_value_for_key(QString string, QString key, float& result);
int q_get_value_for_key(QString string, QString key, int& result);
int q_get_value_for_key(QString string, QString key, unsigned int& result);
int q_get_value_for_key(QString string, QString key, bool& result);
int q_get_value_for_key(QString string, QString key, QStringList& result);
int q_get_groups(QString string,QStringList& names,QStringList& groups);
//char *q_shorten_text(boxA,boxB,char * text,)
#endif // PETKO10Q_H
