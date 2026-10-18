# UI 测试公共配置: chart_test / stylesheet_test / password_test / feature_test
# 这四个都要实例化真实的界面控件, 因此链主程序全部源码(与 controlalgorithm_test
# 只链算法层不同)。qmake 会自动为 HEADERS 里带 Q_OBJECT 的类生成 moc,
# 不需要像本机手工编译那样显式列 moc_*.o。
#
# 本地跑法(与 AGENTS.md 记录一致):
#   qmake -o Makefile.ct tests/chart_test.pro && make -f Makefile.ct
#   QT_QPA_PLATFORM=offscreen ./chart_test
# 注意必须是 offscreen 平台: 模态 exec() 在该平台下不转 QTimer,
# 而测试里有对话框场景(见 password_test)。

QT += core gui widgets serialport testlib

TEMPLATE = app
CONFIG += console c++11

INCLUDEPATH += ../src

SOURCES += \
    ../src/appui.cpp \
    ../src/applogic.cpp \
    ../src/controlalgorithm.cpp \
    ../src/rs485device.cpp

HEADERS += \
    ../src/appui.h \
    ../src/applogic.h \
    ../src/controlalgorithm.h \
    ../src/rs485device.h

# 中间产物与可执行文件统一放 build 目录，避免污染源码树。
# 用 $$_PRO_FILE_PWD_ 取本 .pri 所在目录(tests/)再拼相对路径 —— qmake 的相对
# 路径是相对"运行 qmake 的目录"解释的，写死 ../build 会在仓库根和在 build/tests
# 里分别落到不同位置(实测就踩过: 根目录跑 qmake 时产物没进 build/tests)。
# 仓库根 .gitignore 已忽略整个 build/, 不需要为每个测试单加忽略条目。
MOC_DIR     = $$_PRO_FILE_PWD_/../build/moc
OBJECTS_DIR = $$_PRO_FILE_PWD_/../build/obj
RCC_DIR     = $$_PRO_FILE_PWD_/../build/rcc
UI_DIR      = $$_PRO_FILE_PWD_/../build/ui
DESTDIR     = $$_PRO_FILE_PWD_/../build/tests
