// 五套主题的样式表都必须能被 Qt 完整解析: 样式表原始字符串里混进 C++ 风格
// 注释会让整份表解析失败, Qt 只打一句 "Could not parse stylesheet",
// 界面静默回退成默认(浅色)外观, 现场很难发现。
#include "appui.h"
#include <QApplication>
#include <QWidget>
#include <QDebug>
#include <cstdio>
#include <QTest>
#include <QColor>
#include <QRegularExpression>
#include <cmath>

// CIE L*a*b* 的 ΔE76(欧氏距离), 即感知色差。为什么不用 HSV 的 valueF 或 RGB
// 欧氏距离: valueF 只取 max(R,G,B), 会把"深绿 #0e7a4a vs 饱和蓝 #1668a8"算成
// 只差 0.18、把"近白 #e6f7ed vs 饱和蓝 #007dff"算成只差 0.03, 而这两组在现场
// 都是一眼可分的(第一版就是这么误判的, 把本该通过的低光/鸿蒙主题判成失败);
// RGB 欧氏距离则对暗部不敏感。ΔE 的"刚好可分辨"阈值约 2.3, 这里取 20 —— 现场
// 是 1024×600 的屏、人站在设备前看, 要的是"一眼分出", 不是"盯着看能勉强认出"。
struct Lab { double l, a, b; };

static Lab toLab(const QColor &c)
{
    auto lin = [](int v8) {
        const double v = v8 / 255.0;
        return v <= 0.04045 ? v / 12.92 : std::pow((v + 0.055) / 1.055, 2.4);
    };
    const double r = lin(c.red()), g = lin(c.green()), b = lin(c.blue());
    // 线性 sRGB -> XYZ (D65 白点), 各除以白点使 Y 归一
    const double x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
    const double y =  0.2126 * r + 0.7152 * g + 0.0722 * b;
    const double z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
    auto f = [](double t) {
        return t > 216.0 / 24389.0 ? std::cbrt(t) : (841.0 / 108.0) * t + 4.0 / 29.0;
    };
    const double fx = f(x), fy = f(y), fz = f(z);
    return Lab{ 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz) };
}

static double deltaE76(const QColor &a, const QColor &b)
{
    const Lab la = toLab(a), lb = toLab(b);
    return std::sqrt((la.l-lb.l)*(la.l-lb.l) + (la.a-lb.a)*(la.a-lb.a)
                     + (la.b-lb.b)*(la.b-lb.b));
}

// 从整份样式表里取某条规则的 background 色。找不到(该主题没写这条规则)时
// 返回无效 QColor, 由调用方决定跳过而不是当成失败 —— 各主题本来就允许只覆盖
// 自己关心的规则, 没写的会落到 base 上。
// 必须取**最后**一次匹配: applicationStyleSheet 是 base + 主题覆盖拼接的, 同名
// 规则后出现的赢, 所以第一次匹配拿到的是 base 的值、不是该主题真正生效的值
// (第一版就用 match() 取到了 base 的 #e8f7ee/#1c62b0, 于是每个主题测出来的
// 明度差都一样, 等于没测)。
static QColor pillBackground(const QString &sheet, const QString &selector)
{
    const QRegularExpression re(QRegularExpression::escape(selector)
                                + "\\s*\\{[^}]*background:\\s*([^;]+);",
                                QRegularExpression::InvertedGreedinessOption);
    QColor last;
    QRegularExpressionMatchIterator it = re.globalMatch(sheet);
    while (it.hasNext()) {
        const QRegularExpressionMatch m = it.next();
        const QColor c(m.captured(1).trimmed());
        if (c.isValid())
            last = c;
    }
    return last;
}

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
        // 两个 pill 的激活态必须在明度上分开。现场反馈过"实时数据的背景颜色
        // 跟自检正常一致": 根因是两边都是高亮度低饱和的色块(浅绿 #e8f7ee vs
        // 浅蓝 #e8f1fb), 在 1024×600 的屏上根本分不出来, 而这种失败没有弹窗、
        // 没有告警, 只有现场人看错状态 —— 所以必须由测试守住, 不能靠人记得。
        // 判据用相对亮度差而不是色相差: 蓝和绿的色相本来就不同, 分不清是因为
        // 明度几乎相同, 所以卡明度差而不是卡色相角。
        const QString ss = w.styleSheet();
        const QColor selfHealthy = pillBackground(ss, "QLabel#selfCheckPill[healthy=\"true\"]");
        const QColor realtimeOn = pillBackground(ss, "QPushButton#realtimePill:checked");
        if (selfHealthy.isValid() && realtimeOn.isValid()) {
            const double de = deltaE76(selfHealthy, realtimeOn);
            const bool apart = de > 20.0;
            printf("    自检正常 %s vs 实时选中 %s : ΔE=%.1f %s\n",
                   qPrintable(selfHealthy.name()), qPrintable(realtimeOn.name()),
                   de, apart ? "✅" : "❌");
            if (!apart) ++fail;
        }
    }
    printf("\n%s\n", fail == 0 ? "✅ 五套主题样式表全部解析通过"
                               : "❌ 有主题样式表解析失败");
    return fail == 0 ? 0 : 1;
}
