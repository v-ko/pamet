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
    canvas.cpp \
    mislidir.cpp \
    mislidesktopgui.cpp \
    notessearch.cpp \
    notedetailswindow.cpp

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
    canvas.h \
    mislidir.h \
    mislidesktopgui.h \
    notessearch.h \
    notedetailswindow.h

OTHER_FILES += \
    help/text.txt \
    license.txt \
    README \
    help/help_en.misl \
    help/help_bg.misl \
    translations/misli_bg.ts \
    translations/misli_bg.qm \
    other/misli.desktop \
    android/version.xml \
    android/src/org/qtproject/qt5/android/bindings/QtApplication.java \
    android/src/org/qtproject/qt5/android/bindings/QtActivity.java \
    android/src/org/kde/necessitas/ministro/IMinistroCallback.aidl \
    android/src/org/kde/necessitas/ministro/IMinistro.aidl \
    android/AndroidManifest.xml \
    android/res/values-zh-rTW/strings.xml \
    android/res/values-ja/strings.xml \
    android/res/values-fa/strings.xml \
    android/res/values-es/strings.xml \
    android/res/values-de/strings.xml \
    android/res/values-id/strings.xml \
    android/res/values-nl/strings.xml \
    android/res/values-rs/strings.xml \
    android/res/values/strings.xml \
    android/res/values/libs.xml \
    android/res/values-el/strings.xml \
    android/res/layout/splash.xml \
    android/res/values-et/strings.xml \
    android/res/values-nb/strings.xml \
    android/res/values-fr/strings.xml \
    android/res/values-ms/strings.xml \
    android/res/values-ru/strings.xml \
    android/res/values-it/strings.xml \
    android/res/values-pt-rBR/strings.xml \
    android/res/values-zh-rCN/strings.xml \
    android/res/values-pl/strings.xml \
    android/res/values-ro/strings.xml

win32{
    QMAKE_LFLAGS += -static-libgcc
}

RESOURCES +=   misli.qrc

FORMS += \
    getdirdialogue.ui \
    editnotedialogue.ui \
    newnfdialogue.ui \
    misliwindow.ui \
    notedetailswindow.ui

CODECFORTR = UTF-8
TRANSLATIONS += ./translations/misli_bg.ts
