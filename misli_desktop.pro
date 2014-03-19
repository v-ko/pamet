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
    license.txt \
    README \
    help/help_en.misl \
    help/help_bg.misl \
    translations/misli_bg.ts \
    translations/misli_bg.qm \
    other/misli.desktop \
    LOG.txt \
    README.md

#win32{
#    QMAKE_LFLAGS += -static-libgcc
#}

RESOURCES +=   misli.qrc

CODECFORTR = UTF-8
TRANSLATIONS += ./translations/misli_bg.ts

HEADERS += \
    canvas.h \
    common.h \
    emitmynameaction.h \
    filesystemwatcher.h \
    link.h \
    mislidir.h \
    misliinstance.h \
    note.h \
    notefile.h \
    notessearch.h \
    petko10.h \
    petko10q.h \
    misli_desktop/editnotedialogue.h \
    misli_desktop/getdirdialogue.h \
    misli_desktop/main.h \
    misli_desktop/mislidesktopgui.h \
    misli_desktop/misliwindow.h \
    misli_desktop/newnfdialogue.h \
    misli_desktop/notedetailswindow.h

SOURCES += \
    canvas.cpp \
    emitmynameaction.cpp \
    filesystemwatcher.cpp \
    link.cpp \
    mislidir.cpp \
    misliinstance.cpp \
    note.cpp \
    notefile.cpp \
    notessearch.cpp \
    petko10.cpp \
    petko10q.cpp \
    misli_desktop/editnotedialogue.cpp \
    misli_desktop/getdirdialogue.cpp \
    misli_desktop/main.cpp \
    misli_desktop/mislidesktopgui.cpp \
    misli_desktop/misliwindow.cpp \
    misli_desktop/newnfdialogue.cpp \
    misli_desktop/notedetailswindow.cpp

FORMS += \
    misli_desktop/editnotedialogue.ui \
    misli_desktop/getdirdialogue.ui \
    misli_desktop/misliwindow.ui \
    misli_desktop/newnfdialogue.ui \
    misli_desktop/notedetailswindow.ui
