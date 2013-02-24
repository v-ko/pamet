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

CONFIG += console

SOURCES += main.cpp\
        noteswindow.cpp \
    misliinstance.cpp \
    getdirwindow.cpp \
    notefile.cpp \
    note.cpp \
    glwidget.cpp \
    ../../petko10.cpp \
    editnotewindow.cpp \
    link.cpp \
    getnfname.cpp \
    helpwindow.cpp \
    common.cpp \
    ../../petko10q.cpp

HEADERS  += noteswindow.h \
    misliinstance.h \
    getdirwindow.h \
    notefile.h \
    note.h \
    glwidget.h \
    ../../petko10.h \
    editnotewindow.h \
    link.h \
    getnfname.h \
    helpwindow.h \
    common.h \
    ../../petko10q.h

OTHER_FILES += \
    program_logic.txt \
    help/text.txt \
    license.txt \
    README


#CONFIG += static

win32{
    QMAKE_LFLAGS += -static-libgcc
}

unix{
    LIBS += -lGLU
    LIBS += -lGL
}

RESOURCES +=   misli.qrc
