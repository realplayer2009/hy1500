// 本轮三项改动的测试:
// 1) 实时数据呼吸灯(所有页面可见, 有数据时持续渐变)
// 2) 手动模式告警灯闪烁(界面 ⚠ / runState 变色, 不写硬件)
// 3) 手动加热器连续工作满 2 小时强制休息 15 分钟的提示文案
#include "appui.h"
#include <QApplication>
#include <QImage>
#include <QPushButton>
#include <algorithm>   // std::max_element
#include <QVector>
#include <QTest>
#include <QElapsedTimer>
#include <cstdio>

// appui.cpp 匿名 namespace 里的自由函数, 这里补声明用于测试
QString overholdText(const QMap<int, qint64> &restByHeater);

static int fail = 0;
static void check(bool ok, const char *what)
{
    printf("  %-52s %s\n", what, ok ? "✅" : "❌");
    if (!ok) ++fail;
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    // ── 呼吸灯 ──────────────────────────────────────────────────────
    printf("\n=== 呼吸灯: setActive / isActive ===\n");
    {
        LivePulseIndicator ind;
        ind.resize(16, 32);
        check(!ind.isActive(), "初始静止");
        ind.setActive(true);
        check(ind.isActive(), "setActive(true) 后进入呼吸");
        ind.setActive(true);
        check(ind.isActive(), "重复 setActive(true) 不翻转状态");
        ind.setActive(false);
        check(!ind.isActive(), "setActive(false) 后停下");
        // 不崩
        const QImage img = ind.grab().toImage();
        check(img.width() == 16 && img.height() == 32, "尺寸 16x32 且能绘制");
    }

    printf("\n=== 呼吸灯: 渐变(帧间像素不同) ===\n");
    {
        LivePulseIndicator ind;
        ind.resize(16, 32);
        ind.show();
        qApp->processEvents();
        ind.setActive(true);
        // 50ms 一拍, 等 3 拍让相位推进
        QImage a, b;
        for (int i = 0; i < 3; ++i) {
            QTest::qWait(60);
            a = ind.grab().toImage();
        }
        QTest::qWait(60);
        b = ind.grab().toImage();
        int diff = 0;
        for (int y = 0; y < a.height(); ++y)
            for (int x = 0; x < a.width(); ++x)
                if (a.pixel(x, y) != b.pixel(x, y))
                    ++diff;
        check(diff > 0, "呼吸过程中帧间有像素变化(渐变而非恒定)");
        // 静止时两次抓图应完全一致
        ind.setActive(false);
        qApp->processEvents();
        const QImage c = ind.grab().toImage();
        QTest::qWait(120);
        const QImage d = ind.grab().toImage();
        check(c == d, "静止后不再变化(没有空跑定时器)");
    }

    // 呼吸频率: 现场反馈过"闪动频率太低"(原相位步长 0.06 = 5.2 秒一周,
    // 看着像灯坏在半亮)。这里数 2.6 秒内的亮度峰个数, 至少要 2 个,
    // 即一个完整周期不超过约 1.3 秒; 同时不设上限 —— 再快就从"呼吸"
    // 变成"闪烁", 那是另一种(刺眼的)坏, 由上面的"帧间有变化"兜底。
    printf("\n=== 呼吸灯: 频率(一个周期不能太慢) ===\n");
    {
        LivePulseIndicator ind;
        ind.resize(16, 32);
        ind.show();
        qApp->processEvents();
        ind.setActive(true);
        qApp->processEvents();
        QVector<int> greens;
        // 50 ms 一拍, 抓 52 帧 = 2.6 秒
        for (int i = 0; i < 52; ++i) {
            QTest::qWait(50);
            const QImage img = ind.grab().toImage();
            int g = 0;
            for (int y = 0; y < img.height(); ++y)
                for (int x = 0; x < img.width(); ++x) {
                    const QRgb p = img.pixel(x, y);
                    if (qGreen(p) > 120 && qGreen(p) > qRed(p) + 40
                        && qGreen(p) > qBlue(p) + 40)
                        ++g;
                }
            greens.append(g);
        }
        // 数局部极大值(峰): 前后都比它低即算一个峰。
        // 正弦的峰顶/谷底都平坦, 50 ms 采样下会有连续几帧同值, 直接数"局部
        // 极大"会把量化噪声数成假峰(实测 2.6 秒数出 5 个, 而 1.12 秒周期只有
        // 2~3 个)。因此改用谷底: 值低于峰值 25% 记为一帧谷, 连续谷帧合成一个
        // 谷, 相邻两个谷的间隔就是一个完整周期。
        const int peakVal = *std::max_element(greens.begin(), greens.end());
        const int valleyThreshold = peakVal / 4;
        QVector<int> valleyStarts;
        bool inValley = false;
        for (int i = 0; i < greens.size(); ++i) {
            const bool isValley = greens.at(i) <= qMax(1, valleyThreshold);
            if (isValley && !inValley) {
                valleyStarts.append(i);
                inValley = true;
            } else if (!isValley) {
                inValley = false;
            }
        }
        int cycles = 0;
        int cycleFrames = 0;
        if (valleyStarts.size() >= 2) {
            cycles = valleyStarts.size() - 1;
            cycleFrames = valleyStarts.at(1) - valleyStarts.at(0);
        }
        const int cycleMs = cycleFrames * 50;
        printf("  谷底起点帧: ");
        for (int v : valleyStarts) printf("%d ", v);
        printf("\n  完整周期数=%d, 首个周期=%d ms (期望 1 个以上, 且 <=1300 ms)\n",
               cycles, cycleMs);
        check(cycles >= 1 && cycleMs <= 1300,
              "呼吸周期不超过约 1.3 秒(频率不过低)");
    }

    // ── 超持提示文案 ────────────────────────────────────────────────
    printf("\n=== 手动超持提示文案 ===\n");
    {
        check(overholdText(QMap<int, qint64>()).isEmpty(),
              "没有加热器休息时文案为空(label 隐藏)");
        QMap<int, qint64> one;
        one.insert(0 * 4 + 0, 900);   // 子板0 加热器A 休息 15 分钟
        check(overholdText(one) == QString::fromUtf8("⚠ A 超持休息 15:00"),
              "单个加热器: A 15:00");
        QMap<int, qint64> two;
        two.insert(0 * 4 + 0, 900);
        two.insert(0 * 4 + 2, 300);   // A 与 C, C 只剩 5 分钟
        check(overholdText(two) == QString::fromUtf8("⚠ A/C 超持休息 05:00"),
              "多个加热器: A/C 取最短剩余时间");
        QMap<int, qint64> mixed;
        mixed.insert(0 * 4 + 1, 0);   // B 已休息完, 不该出现
        mixed.insert(1 * 4 + 0, 120); // 另一块板的 A
        check(overholdText(mixed) == QString::fromUtf8("⚠ A 超持休息 02:00"),
              "休息完的(rest=0)不出现");
        QMap<int, qint64> multi;
        multi.insert(0 * 4 + 0, 60);
        multi.insert(5 * 4 + 2, 61);
        check(overholdText(multi) == QString::fromUtf8("⚠ A/C 超持休息 01:00"),
              "不同子板的同名加热器都列出来");
    }

    // ── 主窗口能正常构造(顶部新控件已挂上) ─────────────────────────
    printf("\n=== 主窗口构造(顶部新控件) ===\n");
    {
        MainWindow w;
        w.resize(1024, 600);
        w.show();
        qApp->processEvents();
        // 呼吸灯在顶部栏里, 抓整窗不应崩
        const QImage img = w.grab().toImage();
        check(img.width() > 0, "主窗口含呼吸灯/超持提示后仍能整体绘制");
        // 实时数据按钮: 所有页面都可见(默认在总览页也该看得见)
        const QList<QPushButton *> pills = w.findChildren<QPushButton *>();
        bool found = false;
        for (QPushButton *b : pills)
            if (b->text() == QString::fromUtf8("实时数据")) {
                found = true;
                check(b->isVisible(), "\"实时数据\" 在默认页面(总览)也可见");
            }
        check(found, "顶部能找到\"实时数据\"按钮");
    }

    printf("\n════════════════════════\n");
    printf("%s\n", fail == 0 ? "✅ 本轮功能全部通过" : "❌ 有场景不符合预期");
    return fail == 0 ? 0 : 1;
}
