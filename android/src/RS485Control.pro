# ============================================================
# RS485Control Android qmake project
# 生成 libRS485Control.so，供 androiddeployqt 打包成 APK
# ============================================================

QT += core gui widgets serialport androidextras

TARGET = RS485Control
TEMPLATE = app
CONFIG += c++11

# Android ABI / SDK
ANDROID_ABIS = arm64-v8a
ANDROID_TARGET_SDK_VERSION = 33
ANDROID_SDK_ROOT = $$(ANDROID_SDK_ROOT)
ANDROID_PACKAGE_SOURCE_DIR = $$PWD/../package
ANDROID_VERSION_CODE = 1
ANDROID_VERSION_NAME = 1.0

# 源码在上一级目录的 src/ 下
INCLUDEPATH += ../../
DEPENDPATH  += ../../

DEFINES += QT_DEPRECATED_WARNINGS

SOURCES += \
    ../../src/main.cpp \
    ../../src/controlalgorithm.cpp \
    ../../src/appui.cpp \
    ../../src/applogic.cpp \
    ../../src/rs485device.cpp

HEADERS += \
    ../../src/controlalgorithm.h \
    ../../src/appui.h \
    ../../src/applogic.h \
    ../../src/rs485device.h
