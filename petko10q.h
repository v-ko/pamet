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
float q_version_string_to_number(QString version);
#endif // PETKO10Q_H
