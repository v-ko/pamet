#-------------------------------------------------
#
# Project created by QtCreator 2012-10-29T22:16:53
#
#-------------------------------------------------

QT += core gui widgets network xml multimedia sql

QT -= webkit

CONFIG += C++11

INCLUDEPATH += /home/p10/Dropbox/Pepi/C++

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

win32{
    QMAKE_LFLAGS += -static-libgcc
}

RESOURCES +=   ../misli.qrc

CODECFORTR = UTF-8
TRANSLATIONS += ../translations/misli_bg.ts

HEADERS += \
    ../canvas.h \
    ../common.h \
    ../link.h \
    ../mislidir.h \
    ../misliinstance.h \
    ../note.h \
    ../notefile.h \
    ../notessearch.h \
    editnotedialogue.h \
    mislidesktopgui.h \
    misliwindow.h \
    ../petko10.h \
    ../petko10q.h \
    timelinewidget.h \
    timeline.h \
    timelinemodule.h \
    communicationsmodule.h \
    notesmodule.h \
    photomodule.h \
    archivemodule.h \
    statisticsmodule.h

SOURCES += \
    ../canvas.cpp \
    ../link.cpp \
    ../mislidir.cpp \
    ../misliinstance.cpp \
    ../note.cpp \
    ../notefile.cpp \
    ../notessearch.cpp \
    editnotedialogue.cpp \
    main.cpp \
    mislidesktopgui.cpp \
    misliwindow.cpp \
    ../petko10.cpp \
    ../petko10q.cpp \
    timelinewidget.cpp \
    timeline.cpp \
    timelinemodule.cpp \
    communicationsmodule.cpp \
    notesmodule.cpp \
    photomodule.cpp \
    archivemodule.cpp \
    statisticsmodule.cpp

FORMS += \
    editnotedialogue.ui \
    misliwindow.ui \
    timelinewidget.ui

DISTFILES += \
    ../installer/config/config.xml \
    ../installer/packages/com.p10.misli/meta/installscript.qs \
    ../installer/packages/com.p10.misli/meta/package.xml

RC_FILE = ../misli_icon.rc
