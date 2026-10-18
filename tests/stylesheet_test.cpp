// 五套主题的样式表都必须能被 Qt 完整解析: 样式表原始字符串里混进 C++ 风格
// 注释会让整份表解析失败, Qt 只打一句 "Could not parse stylesheet",
// 界面静默回退成默认(浅色)外观, 现场很难发现。
#include "appui.h"
#include <QApplication>
#include <QWidget>
#include <QDebug>
#include <cstdio>
#include <QTest>

static int g_warnings = 0;
static void warningHandler(QtMsgType type, const QMessageLogContext &, const QString &msg)
{
    if (msg.contains("Could not parse stylesheet"))
        ++g_warnings;
    fprintf(stderr, "[%d] %s\n", type, qPrintable(msg));
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    qInstallMessageHandler(warningHandler);
    const QStringList themes = { "standard", "low_light", "high_contrast",
                                 "graphite", "harmony" };
    int fail = 0;
    for (const QString &theme : themes) {
        g_warnings = 0;
        // 必须显式切主题: 不设 displayTheme 的话五次循环构造的都是同一套
        // (配置里的当前值), 名为"五主题"实则只测一套 —— 低光主题样式表里
        // 混进 // 注释导致整表作废, 就是这样漏过去的(现场从没报错,
        // 因为被测的那套恰好是好的)。
        AppConfig::instance().general().displayTheme = theme;
        // 走与程序相同的入口: 构造主窗口即会挂上整套主题样式
        MainWindow w;
        w.show();
        qApp->processEvents();
        printf("  主题 %-14s 样式表解析告警=%d %s\n",
               qPrintable(theme), g_warnings, g_warnings == 0 ? "✅" : "❌");
        if (g_warnings != 0) ++fail;
    }
    printf("\n%s\n", fail == 0 ? "✅ 五套主题样式表全部解析通过"
                               : "❌ 有主题样式表解析失败");
    return fail == 0 ? 0 : 1;
}
