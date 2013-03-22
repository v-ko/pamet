#-------------------------------------------------
#
# Project created by QtCreator 2012-10-29T22:16:53
#
#-------------------------------------------------

QT += core gui

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = misli
TEMPLATE = app

SOURCES += main.cpp\
    misliinstance.cpp \
    notefile.cpp \
    note.cpp \
    ../../petko10.cpp \
    link.cpp \
    ../../petko10q.cpp \
    getdirdialogue.cpp \
    editnotedialogue.cpp \
    newnfdialogue.cpp \
    misliwindow.cpp \
    emitmynameaction.cpp \
    filesystemwatcher.cpp \
    canvas.cpp

HEADERS  += \
    misliinstance.h \
    notefile.h \
    note.h \
    ../../petko10.h \
    link.h \
    common.h \
    ../../petko10q.h \
    getdirdialogue.h \
    editnotedialogue.h \
    newnfdialogue.h \
    misliwindow.h \
    emitmynameaction.h \
    filesystemwatcher.h \
    canvas.h

OTHER_FILES += \
    help/text.txt \
    license.txt \
    README \
    help/help_en.misl \
    help/help_bg.misl \
    translations/misli_bg.ts \
    translations/misli_bg.qm

win32{
    QMAKE_LFLAGS += -static-libgcc
}

RESOURCES +=   misli.qrc

FORMS += \
    getdirdialogue.ui \
    editnotedialogue.ui \
    newnfdialogue.ui \
    misliwindow.ui

CODECFORTR = UTF-8
TRANSLATIONS += ./translations/misli_bg.ts
