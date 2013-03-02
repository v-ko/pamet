#-------------------------------------------------
#
# Project created by QtCreator 2012-10-29T22:16:53
#
#-------------------------------------------------

QT += core gui
QT += opengl

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = misli
TEMPLATE = app

SOURCES += main.cpp\
    misliinstance.cpp \
    notefile.cpp \
    note.cpp \
    glwidget.cpp \
    ../../petko10.cpp \
    link.cpp \
    ../../petko10q.cpp \
    getdirdialogue.cpp \
    editnotedialogue.cpp \
    newnfdialogue.cpp \
    misliwindow.cpp \
    emitmynameaction.cpp

HEADERS  += \
    misliinstance.h \
    notefile.h \
    note.h \
    glwidget.h \
    ../../petko10.h \
    link.h \
    common.h \
    ../../petko10q.h \
    getdirdialogue.h \
    editnotedialogue.h \
    newnfdialogue.h \
    misliwindow.h \
    emitmynameaction.h

OTHER_FILES += \
    help/text.txt \
    license.txt \
    README

win32{
    CONFIG += static
    QMAKE_LFLAGS += -static-libgcc
}

unix{
    LIBS += -lGLU
    LIBS += -lGL
}

RESOURCES +=   misli.qrc

FORMS += \
    getdirdialogue.ui \
    editnotedialogue.ui \
    newnfdialogue.ui \
    misliwindow.ui

CODECFORTR = UTF-8
TRANSLATIONS += ./translations/misli_bg.ts
