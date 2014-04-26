#-------------------------------------------------
#
# Project created by QtCreator 2012-10-29T22:16:53
#
#-------------------------------------------------

QT += core gui

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = misli
TEMPLATE = app

OTHER_FILES += \
    ../license.txt \
    ../README \
    ../help/help_en.misl \
    ../help/help_bg.misl \
    ../translations/misli_bg.ts \
    ../translations/misli_bg.qm \
    ../other/misli.desktop \
    ../LOG.txt \
    ../README.md \
    ../other/initial_start_nf_bg.misl \
    ../other/initial_start_nf_en.misl

#win32{
#    QMAKE_LFLAGS += -static-libgcc
#}

RESOURCES +=   ../misli.qrc

CODECFORTR = UTF-8
TRANSLATIONS += ../translations/misli_bg.ts

HEADERS += \
    ../canvas.h \
    ../common.h \
    ../emitmynameaction.h \
    ../filesystemwatcher.h \
    ../link.h \
    ../mislidir.h \
    ../misliinstance.h \
    ../note.h \
    ../notefile.h \
    ../notessearch.h \
    ../petko10.h \
    ../petko10q.h \
    editnotedialogue.h \
    getdirdialogue.h \
    main.h \
    mislidesktopgui.h \
    misliwindow.h \
    newnfdialogue.h \
    notedetailswindow.h

SOURCES += \
    ../canvas.cpp \
    ../emitmynameaction.cpp \
    ../filesystemwatcher.cpp \
    ../link.cpp \
    ../mislidir.cpp \
    ../misliinstance.cpp \
    ../note.cpp \
    ../notefile.cpp \
    ../notessearch.cpp \
    ../petko10.cpp \
    ../petko10q.cpp \
    editnotedialogue.cpp \
    getdirdialogue.cpp \
    main.cpp \
    mislidesktopgui.cpp \
    misliwindow.cpp \
    newnfdialogue.cpp \
    notedetailswindow.cpp

FORMS += \
    editnotedialogue.ui \
    getdirdialogue.ui \
    misliwindow.ui \
    newnfdialogue.ui \
    notedetailswindow.ui
