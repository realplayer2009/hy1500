// 历史曲线渲染测试: 验证 A/B/C 三路温度实线 + 三路湿度虚线、缺通路时隐藏、
// PT100 未接入时隐藏、曲线上文字标签的数量/位置/不互相遮挡、
// 实时追加不打断十字线。
// 曲线部分只统计绘图区内的序列色像素(排除坐标轴/图例/时间轴);
// 标签部分直接用 HistoryChart::labelBoxes() 的几何结果判定 —— 像素启发式
// 会把浅斜率曲线(每行十几像素的横线)误判成标签边框, 不可靠。
#include "appui.h"
#include <QApplication>
#include <QImage>
#include <QPainter>
#include <QDebug>
#include <cstdio>
#include <cmath>
#include <QMouseEvent>

static HistoryQuery::Record rec(const QVector<QPair<QString, int>> &fields)
{
    HistoryQuery::Record r;
    r.timestamp = QDateTime::currentDateTime();
    r.portIndex = 0;
    r.slaveId = 1;
    r.deviceName = QString::fromUtf8("P0-ID1");
    for (const auto &f : fields)
        r.values[f.first] = f.second;
    return r;
}

// 生成一段时序; has1/2/3 控制该通路是否出现在记录里(模拟未配置加热器),
// humi1/2/3 控制该路湿度是否出现(模拟只有温度没有湿度的探头)
static QVector<HistoryQuery::Record> series(int n, int base1, int base2, int base3,
                                            int h1, int h2, int h3,
                                            int pt1, int pt2,
                                            bool has1, bool has2, bool has3,
                                            bool humi1 = true, bool humi2 = true,
                                            bool humi3 = true)
{
    QVector<HistoryQuery::Record> out;
    for (int i = 0; i < n; ++i) {
        QVector<QPair<QString, int>> f;
        if (has1) { f << qMakePair(QString("th1_temp"), base1 + i * 3);
                    if (humi1) f << qMakePair(QString("th1_humi"), h1 + i); }
        if (has2) { f << qMakePair(QString("th2_temp"), base2 + i * 5);
                    if (humi2) f << qMakePair(QString("th2_humi"), h2 + i); }
        if (has3) { f << qMakePair(QString("th3_temp"), base3 + i * 7);
                    if (humi3) f << qMakePair(QString("th3_humi"), h3 + i); }
        // PT100 用恒定值: 之前写成 pt + i, "未接入"的 0 会变成 0.1/0.2...,
        // 从第二条起就非零, 曲线被画出来, 那是测试数据的 bug 不是代码的
        if (pt1 != -1) f << qMakePair(QString("pt1_temp"), pt1);
        if (pt2 != -1) f << qMakePair(QString("pt2_temp"), pt2);
        HistoryQuery::Record r = rec(f);
        r.timestamp = QDateTime::currentDateTime().addSecs(-n + i);
        out << r;
    }
    return out;
}

// 绘图区(排除左右坐标轴文字、顶部标题、底部时间轴与图例)
static const int kPlotX0 = 58, kPlotX1 = 845, kPlotY0 = 22, kPlotY1 = 250;

static int countNear(const QImage &img, const QColor &c, int tol)
{
    int n = 0;
    for (int y = kPlotY0; y <= kPlotY1 && y < img.height(); ++y) {
        for (int x = kPlotX0; x <= kPlotX1 && x < img.width(); ++x) {
            const QColor p = img.pixelColor(x, y);
            if (std::abs(p.red() - c.red()) + std::abs(p.green() - c.green())
                    + std::abs(p.blue() - c.blue()) < tol)
                ++n;
        }
    }
    return n;
}

struct Target { const char *name; QColor color; bool drawn; };

// 某序列色像素在绘图区内占的垂直跨度(像素), 用于验证纵轴自适应:
// 藏掉别的序列后, 剩下的曲线应该铺满绘图区而不是仍挤在中间一小条
static int verticalSpan(const QImage &img, const QColor &c, int tol)
{
    int minY = 1 << 30, maxY = -1;
    for (int y = kPlotY0; y <= kPlotY1 && y < img.height(); ++y) {
        for (int x = kPlotX0; x <= kPlotX1 && x < img.width(); ++x) {
            const QColor p = img.pixelColor(x, y);
            if (std::abs(p.red() - c.red()) + std::abs(p.green() - c.green())
                    + std::abs(p.blue() - c.blue()) < tol) {
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }
    }
    return maxY < 0 ? 0 : maxY - minY + 1;
}

// 现场配色: A 亮黄 / B 绿 / C 红(深色主题亮档)
static const QColor CA("#ffd54f"), CB("#66bb6a"), CC("#ef5350");
static const QColor PT1("#a1887f"), PT2("#8d6e63");

static int runCase(const char *title,
                   const QVector<HistoryQuery::Record> &records,
                   const QVector<Target> &targets)
{
    HistoryChart chart;
    chart.resize(900, 320);
    chart.setRecords(records);
    chart.show();
    qApp->processEvents();
    const QImage img = chart.grab().toImage();
    printf("\n=== %s ===\n", title);
    int fail = 0;
    for (const Target &t : targets) {
        const int n = countNear(img, t.color, 15);
        const bool ok = t.drawn ? (n >= 200) : (n < 60);
        if (!ok) ++fail;
        printf("  %-10s 像素=%5d  期望=%-8s %s\n",
               t.name, n, t.drawn ? "画出" : "不画", ok ? "✅" : "❌");
    }
    return fail;
}

// 校验标签: 数量、是否在绘图区内、是否两两不重叠
static int checkLabels(HistoryChart &chart, const char *title, int expectCount)
{
    const QVector<QRectF> boxes = chart.labelBoxes();
    printf("\n=== %s ===\n", title);
    printf("  标签框数=%d  期望=%d  %s\n", boxes.size(), expectCount,
           boxes.size() == expectCount ? "✅" : "❌");
    int fail = boxes.size() == expectCount ? 0 : 1;
    bool inside = true;
    for (const QRectF &b : boxes) {
        if (b.left() < 54 || b.right() > 848 || b.top() < 18 || b.bottom() > 253)
            inside = false;
    }
    printf("  全部在绘图区内: %s\n", inside ? "✅" : "❌");
    if (!inside) ++fail;
    int overlaps = 0;
    for (int i = 0; i < boxes.size(); ++i)
        for (int j = i + 1; j < boxes.size(); ++j)
            if (boxes[i].intersects(boxes[j]))
                ++overlaps;
    printf("  互相重叠的框对=%d  期望=0  %s\n", overlaps,
           overlaps == 0 ? "✅" : "❌");
    if (overlaps != 0) ++fail;
    for (int i = 0; i < boxes.size(); ++i)
        printf("    框%d: x[%.0f,%.0f] y[%.0f,%.0f]\n", i + 1,
               boxes[i].left(), boxes[i].right(),
               boxes[i].top(), boxes[i].bottom());
    return fail;
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    int fail = 0;

    // 场景1: 三路齐全, PT100 两路都未接入(读 0)
    // → A/B/C 各一条温度实线 + 一条湿度虚线, 无 PT100;
    //   同色温度与湿度都画, 因此像素数是两者之和; 标签应有 6 个(每路 2 个)
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        printf("\n=== 场景1 三路齐全 / PT100 均未接入 ===\n");
        struct { const char *n; QColor c; bool d; } t[] = {
            { "A温+湿", CA, true }, { "B温+湿", CB, true },
            { "C温+湿", CC, true }, { "PT100 1", PT1, false },
            { "PT100 2", PT2, false } };
        for (const auto &x : t) {
            const int n = countNear(img, x.c, 15);
            const bool ok = x.d ? (n >= 200) : (n < 60);
            if (!ok) ++fail;
            printf("  %-10s 像素=%5d  期望=%-8s %s\n", x.n, n,
                   x.d ? "画出" : "不画", ok ? "✅" : "❌");
        }
        fail += checkLabels(chart, "场景1 标签(3 路 x 温度+湿度 = 6 个)", 6);
    }

    // 场景2: 只有 A 和 C(B 通路缺失, 如未配置加热器) → 无 B 曲线也无 B 标签
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 0, 300, 400, 0, 440, 0, 0,
                                true, false, true));
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        printf("\n=== 场景2 仅 A/C, B 通路缺失 ===\n");
        const int a = countNear(img, CA, 15), c = countNear(img, CC, 15);
        const int b = countNear(img, CB, 15);
        printf("  A温+湿像素=%d(期望画出) %s\n", a, a >= 200 ? "✅" : "❌");
        printf("  C温+湿像素=%d(期望画出) %s\n", c, c >= 200 ? "✅" : "❌");
        printf("  B 像素=%d(期望不画) %s\n", b, b < 60 ? "✅" : "❌");
        if (a < 200 || c < 200 || b >= 60) ++fail;
        fail += checkLabels(chart, "场景2 标签(只有 A/C 两路 = 4 个)", 4);
    }

    // 场景3: PT100 只有第 1 路接入(25.0℃) → 只画 PT100 1
    fail += runCase("场景3 PT100 仅第1路接入",
        series(40, 200, 250, 300, 400, 420, 440, 250, 0, true, true, true),
        { { "PT100 1", PT1, true }, { "PT100 2", PT2, false } });

    // 场景4: A 读数越界(模拟探头故障) → A 温度与 A 湿度都不画, 也无 A 标签
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, -9990, 250, 300, -9990, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        printf("\n=== 场景4 A 读数越界不画 ===\n");
        const int a = countNear(img, CA, 15), b = countNear(img, CB, 15);
        const int c = countNear(img, CC, 15);
        printf("  A 像素=%d(期望不画) %s\n", a, a < 60 ? "✅" : "❌");
        printf("  B 像素=%d(期望画出) %s\n", b, b >= 200 ? "✅" : "❌");
        printf("  C 像素=%d(期望画出) %s\n", c, c >= 200 ? "✅" : "❌");
        if (a >= 60 || b < 200 || c < 200) ++fail;
        fail += checkLabels(chart, "场景4 标签(只剩 B/C 两路 = 4 个)", 4);
    }

    // 场景5: 只有 A 一路且只有温度没有湿度 → 1 条温度 + 1 个标签框
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 0, 0, 400, 0, 0, 0, 0,
                                true, false, false, false, false, false));
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        printf("\n=== 场景5 仅 A 一路且无湿度 ===\n");
        const int a = countNear(img, CA, 15);
        printf("  A温度 像素=%d(期望画出) %s\n", a, a >= 200 ? "✅" : "❌");
        if (a < 200) ++fail;
        fail += checkLabels(chart, "场景5 标签(只有 A温度 = 1 个)", 1);
    }

    // 场景6: "全部子板"聚合记录(mergeFleetRecord 的产物: 三路各自跨子板均值
    // + fleet_temp_min/max 极值带) → 三路温度照画, 极值带也要出现
    {
        QVector<HistoryQuery::Record> fleet;
        for (int i = 0; i < 40; ++i) {
            QVector<QPair<QString, int>> f;
            f << qMakePair(QString("th1_temp"), 200 + i * 3)
              << qMakePair(QString("th2_temp"), 250 + i * 5)
              << qMakePair(QString("th3_temp"), 300 + i * 7)
              << qMakePair(QString("th1_humi"), 400 + i)
              << qMakePair(QString("th2_humi"), 420 + i)
              << qMakePair(QString("th3_humi"), 440 + i)
              << qMakePair(QString("fleet_count"), 2)
              << qMakePair(QString("fleet_temp_min"), 180 + i * 2)
              << qMakePair(QString("fleet_temp_max"), 420 + i * 6);
            HistoryQuery::Record r = rec(f);
            r.timestamp = QDateTime::currentDateTime().addSecs(-40 + i);
            r.portIndex = -1;
            r.slaveId = -1;
            r.deviceName = QString::fromUtf8("全部子板");
            fleet << r;
        }
        fail += runCase("场景6 全部子板聚合(含极值带)", fleet,
            { { "A温+湿", CA, true }, { "B温+湿", CB, true },
              { "C温+湿", CC, true } });
    }

    // 场景7: 实时追加记录不能打断正在查看的十字线/数值提示
    // (现场每秒都在落盘, 旧实现每条新记录都把十字线清掉, 提示闪一下就没了)
    {
        HistoryChart chart;
        chart.resize(900, 320);
        QVector<HistoryQuery::Record> recs =
            series(40, 200, 250, 300, 400, 420, 440, 250, 0, true, true, true);
        chart.setRecords(recs);
        chart.show();
        qApp->processEvents();
        QString tooltip;
        QObject::connect(&chart, &HistoryChart::inspectionChanged,
                         [&tooltip](const QString &s) { tooltip = s; });
        QMouseEvent press(QEvent::MouseButtonPress, QPointF(450, 150),
                          Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &press);
        QMouseEvent release(QEvent::MouseButtonRelease, QPointF(450, 150),
                            Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &release);
        const QString afterTap = tooltip;
        HistoryQuery::Record next = recs.last();
        next.timestamp = next.timestamp.addSecs(1);
        next.values["th1_temp"] = 260;
        chart.appendRecord(next);
        const QString afterAppend = tooltip;
        chart.refreshRecords();
        const QString afterRefresh = tooltip;
        chart.setRecords(recs);
        const QString afterRequery = tooltip;

        printf("\n=== 场景7 实时追加不打断十字线 ===\n");
        const bool tapOk = afterTap.contains("A温度")
            && afterTap.contains("B温度") && afterTap.contains("C温度")
            && afterTap.contains("A湿度") && afterTap.contains("B湿度")
            && afterTap.contains("C湿度")
            && afterTap.contains("PT100-1") && !afterTap.contains("PT100-2");
        const bool appendOk = (afterAppend == afterTap) && !afterAppend.isEmpty();
        const bool refreshOk = afterRefresh == afterTap;
        const bool requeryOk = afterRequery.contains("点击曲线");
        printf("  提示含 A/B/C 温度湿度与 PT100-1、无 PT100-2: %s\n",
               tapOk ? "✅" : "❌");
        printf("  追加记录后提示原样保留: %s\n", appendOk ? "✅" : "❌");
        printf("  聚合同秒原地更新后提示原样保留: %s\n", refreshOk ? "✅" : "❌");
        printf("  重新查询后重置为默认提示: %s\n", requeryOk ? "✅" : "❌");
        if (!tapOk) printf("    提示内容: %s\n", qPrintable(afterTap));
        if (!appendOk) printf("    追加前: %s\n    追加后: %s\n",
                              qPrintable(afterTap), qPrintable(afterAppend));
        if (!tapOk || !appendOk || !refreshOk || !requeryOk) ++fail;
    }

    // 场景8: 点击后图表里必须画出十字竖虚线
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 250, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        QMouseEvent press(QEvent::MouseButtonPress, QPointF(450, 150),
                          Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &press);
        QMouseEvent release(QEvent::MouseButtonRelease, QPointF(450, 150),
                            Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &release);
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        int bestX = -1, bestCount = 0;
        for (int x = 54; x <= img.width() - 52; ++x) {
            int n = 0;
            for (int y = 18; y <= 253 && y < img.height(); ++y) {
                const QColor p = img.pixelColor(x, y);
                if (std::abs(p.red() - 38) + std::abs(p.green() - 38)
                        + std::abs(p.blue() - 40) > 60)
                    ++n;
            }
            if (n > bestCount) { bestCount = n; bestX = x; }
        }
        printf("\n=== 场景8 十字线是否画出 ===\n");
        printf("  非背景最多列 x=%d 共 %d 像素\n", bestX, bestCount);
        const bool ok = bestCount > 40;
        printf("  竖虚线: %s\n", ok ? "✅ 已画出" : "❌ 未画出");
        if (!ok) ++fail;
    }

    // 场景9: 七个标签框(3 温度 + 3 湿度 + PT100 1)不能互相重叠,
    // 且都要落在绘图区内 —— 标签挤在一起正是"互相遮挡"
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 250, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        fail += checkLabels(chart, "场景9 标签不互相遮挡(3 温 + 3 湿 + PT100 = 7 个)",
                            7);
    }

    // 场景10: 每个标签框的外框都必须真的画出来, 且线型与曲线一致 ——
    // 温度是实线(接近整宽连续), 湿度是点线(断成多段)。
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 250, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        const QVector<QRectF> boxes = chart.labelBoxes();
        const QColor cols[5] = { CA, CB, CC, PT1, PT2 };
        auto edgePixels = [&](const QRectF &b, int edge) {
            int total = 0;
            // 外框内缩 0.5 后, 上边落在 top 行、下边落在 bottom-1 行
            const int yy = edge == 0 ? (int)b.top() : (int)b.bottom() - 1;
            for (int x = (int)b.left(); x <= (int)b.right(); ++x) {
                const QColor p = img.pixelColor(x, yy);
                for (const QColor &c : cols) {
                    if (std::abs(p.red() - c.red()) + std::abs(p.green() - c.green())
                            + std::abs(p.blue() - c.blue()) < 60) { ++total; break; }
                }
            }
            return total;
        };
        printf("\n=== 场景10 标签外框已画出(实线/点线并存) ===\n");
        int drawn = 0, solidLike = 0, dotLike = 0;
        for (const QRectF &b : boxes) {
            const int w = (int)b.width();
            const int top = edgePixels(b, 0), bottom = edgePixels(b, 1);
            const int ratio = (top + bottom) * 100 / (2 * qMax(1, w));
            // 点线的节距是 1:2, 覆盖率约 1/3; 实线接近满宽。
            if (ratio >= 20) ++drawn;
            if (ratio >= 85) ++solidLike;
            if (ratio >= 20 && ratio < 70) ++dotLike;
            printf("  框 x[%.0f,%.0f] y[%.0f,%.0f] 上边=%d 下边=%d 宽=%d 覆盖率=%d%%\n",
                   b.left(), b.right(), b.top(), b.bottom(), top, bottom, w, ratio);
        }
        const bool allDrawn = drawn == boxes.size();
        // 温度 3 个实线框 + 湿度 3 个点线框 + PT100 1 个虚线框:
        // 必须同时存在高覆盖率(实线)与低覆盖率(点/虚), 证明外框跟曲线线型走
        const bool bothStyles = solidLike >= 3 && dotLike >= 3;
        printf("  外框画出的框=%d/%d %s\n", drawn, boxes.size(),
               allDrawn ? "✅" : "❌");
        printf("  实线样式框=%d, 点/虚样式框=%d, 两种并存: %s\n",
               solidLike, dotLike, bothStyles ? "✅" : "❌");
        if (!allDrawn || !bothStyles) ++fail;
    }

    // 场景13: 湿度曲线必须是点线, 而且笔宽只有 1px。
    // 判据用一条恒定湿度的曲线: 实线会连成一条通长同色像素, 点线则断成
    // 一段段; 笔宽 1 意味着整条曲线只占一行像素。
    // 扫描区要躲开右侧的文字标签框(同色)与底部图例, 否则数到的是标签不是曲线。
    {
        HistoryChart chart;
        chart.resize(900, 320);
        HistoryQuery::Record r = rec({ qMakePair(QString("th1_humi"), 500) });
        r.timestamp = QDateTime::currentDateTime().addSecs(-40);
        QVector<HistoryQuery::Record> recs;
        for (int i = 0; i < 40; ++i) {
            HistoryQuery::Record c = r;
            c.timestamp = r.timestamp.addSecs(i);
            recs << c;
        }
        chart.setRecords(recs);
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        const int sx0 = 60, sx1 = 760, sy0 = 22, sy1 = 240;   // 绘图区内, 排除标签
        auto isA = [&](int x, int y) {
            const QColor p = img.pixelColor(x, y);
            return std::abs(p.red() - CA.red()) + std::abs(p.green() - CA.green())
                       + std::abs(p.blue() - CA.blue()) < 40;
        };
        int rows = 0, longest = 0, total = 0;
        for (int y = sy0; y <= sy1; ++y) {
            bool rowHas = false;
            int run = 0;
            for (int x = sx0; x <= sx1; ++x) {
                if (isA(x, y)) {
                    rowHas = true; ++run; ++total;
                    if (run > longest) longest = run;
                } else {
                    run = 0;
                }
            }
            if (rowHas) ++rows;
        }
        printf("\n=== 场景13 湿度曲线是点线且笔宽 1px ===\n");
        printf("  占用的行数=%d (期望 1), 最长连续段=%d px, 总像素=%d\n",
               rows, longest, total);
        const bool thin = rows == 1;
        const bool dotted = longest < 10 && total > 200;
        printf("  笔宽 1px(只占一行): %s  点线断续(最长段<10): %s\n",
               thin ? "✅" : "❌", dotted ? "✅" : "❌");
        if (!thin || !dotted) ++fail;
    }

    // 场景14: 温度曲线保持实线 2px —— 与湿度的点线形成线型对比,
    // 不能因为湿度改细把主信号也一起改细。
    {
        HistoryChart chart;
        chart.resize(900, 320);
        HistoryQuery::Record r = rec({ qMakePair(QString("th1_temp"), 250) });
        r.timestamp = QDateTime::currentDateTime().addSecs(-40);
        QVector<HistoryQuery::Record> recs;
        for (int i = 0; i < 40; ++i) {
            HistoryQuery::Record c = r;
            c.timestamp = r.timestamp.addSecs(i);
            recs << c;
        }
        chart.setRecords(recs);
        chart.show();
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        const int sx0 = 60, sx1 = 760, sy0 = 22, sy1 = 240;
        auto isA = [&](int x, int y) {
            const QColor p = img.pixelColor(x, y);
            return std::abs(p.red() - CA.red()) + std::abs(p.green() - CA.green())
                       + std::abs(p.blue() - CA.blue()) < 40;
        };
        int rows = 0, longest = 0, total = 0;
        for (int y = sy0; y <= sy1; ++y) {
            bool rowHas = false;
            int run = 0;
            for (int x = sx0; x <= sx1; ++x) {
                if (isA(x, y)) {
                    rowHas = true; ++run; ++total;
                    if (run > longest) longest = run;
                } else {
                    run = 0;
                }
            }
            if (rowHas) ++rows;
        }
        printf("\n=== 场景14 温度曲线保持实线 2px ===\n");
        printf("  占用的行数=%d (期望 2), 最长连续段=%d px, 总像素=%d\n",
               rows, longest, total);
        const bool wide = rows >= 1 && rows <= 2;
        const bool solid = longest > 600;
        // 行数只要求 1~2: 2px 笔画在整数 y 上会占满两行, 落在半像素上则第二行被
        // 抗锯齿稀释到实色阈值以下(实测 CI/Linux 上只剩 1 行, macOS 上是 2 行),
        // "是不是 2px"由此判不准。这条场景要守的回归是"温度被误改成 1px 点线",
        // 那个由场景13(点线断续 + 只占一行)与下面的"实线通长"共同抓住。
        printf("  笔宽 2px(占一到两行): %s  实线通长(最长段>600): %s\n",
               wide ? "✅" : "❌", solid ? "✅" : "❌");
        if (!wide || !solid) ++fail;
    }

    // 场景11: trimRecords —— 实时模式把窗口外的旧点裁掉, 裁掉后图表仍能画,
    // 且记录数只剩窗口内的那部分
    {
        HistoryChart chart;
        chart.resize(900, 320);
        // 60 条, 每秒一条, 时间戳从 60 秒前到现在
        QVector<HistoryQuery::Record> recs;
        const QDateTime now = QDateTime::currentDateTime();
        for (int i = 0; i < 60; ++i) {
            HistoryQuery::Record r = rec({ qMakePair(QString("th1_temp"), 250 + i),
                                           qMakePair(QString("th1_humi"), 450 + i) });
            r.timestamp = now.addSecs(-60 + i);
            recs << r;
        }
        chart.setRecords(recs);
        chart.show();
        qApp->processEvents();
        const int before = chart.recordCount();
        // 只保留最近 20 秒
        chart.trimRecords(now.addSecs(-20));
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        const int drawn = countNear(img, CA, 15);
        printf("\n=== 场景11 trimRecords 裁掉窗口外的点 ===\n");
        printf("  裁剪前 %d 条, 裁剪后 %d 条(期望 20)\n", before, chart.recordCount());
        printf("  裁剪后曲线仍画出: %d px\n", drawn);
        const bool countOk = chart.recordCount() == 20;
        const bool drawnOk = drawn >= 200;
        printf("  记录数: %s  曲线: %s\n",
               countOk ? "✅" : "❌", drawnOk ? "✅" : "❌");
        if (!countOk || !drawnOk) ++fail;
    }

    // 场景12: 裁剪后正在查看的十字线必须还指着同一条读数(时间戳不变),
    // 只是索引左移; 只有被裁掉的那条才放弃
    {
        HistoryChart chart;
        chart.resize(900, 320);
        QVector<HistoryQuery::Record> recs;
        const QDateTime now = QDateTime::currentDateTime();
        for (int i = 0; i < 60; ++i) {
            HistoryQuery::Record r = rec({ qMakePair(QString("th1_temp"), 250 + i),
                                           qMakePair(QString("th1_humi"), 450 + i) });
            r.timestamp = now.addSecs(-60 + i);
            recs << r;
        }
        chart.setRecords(recs);
        chart.show();
        qApp->processEvents();
        QString tooltip;
        QObject::connect(&chart, &HistoryChart::inspectionChanged,
                         [&tooltip](const QString &s) { tooltip = s; });
        QMouseEvent press(QEvent::MouseButtonPress, QPointF(450, 150),
                          Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &press);
        QMouseEvent release(QEvent::MouseButtonRelease, QPointF(450, 150),
                            Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &release);
        const QString before = tooltip;
        // 裁剪到最近 40 秒: 被点中的记录仍在窗口内
        chart.trimRecords(now.addSecs(-40));
        const QString afterInWindow = tooltip;
        // 再裁到最近 5 秒: 被点中的记录被裁掉, 提示应重置
        chart.trimRecords(now.addSecs(-5));
        const QString afterOut = tooltip;

        printf("\n=== 场景12 裁剪后十字线仍指着同一条读数 ===\n");
        const bool keepOk = afterInWindow == before && !before.isEmpty();
        const bool dropOk = afterOut.contains("点击曲线");
        printf("  窗口内裁剪后提示原样保留: %s\n", keepOk ? "✅" : "❌");
        printf("  记录被裁掉后重置为默认提示: %s\n", dropOk ? "✅" : "❌");
        if (!keepOk) printf("    裁剪前: %s\n    裁剪后: %s\n",
                            qPrintable(before), qPrintable(afterInWindow));
        if (!keepOk || !dropOk) ++fail;
    }

    // ══════════════════════════════════════════════════════════════════
    // 图例栏就是序列开关: 点一下藏起该条曲线, 再点一下恢复。
    // 序列下标: 0/1/2 = A/B/C 温度, 3/4/5 = A/B/C 湿度, 6/7 = PT100 1/2
    // ══════════════════════════════════════════════════════════════════

    // 场景15: 图例栏数 = 数据有效的序列数(含被藏起来的), 栏不重叠且在绘图区下方
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        const QVector<QRectF> boxes = chart.legendBoxes();
        const QVector<int> ser = chart.legendSeries();
        printf("\n=== 场景15 图例栏数 = 数据有效序列数 ===\n");
        const bool countOk = boxes.size() == 6 && ser.size() == 6;
        printf("  图例栏数=%d  期望=6(3 温度 + 3 湿度, PT100 读 0 不进图例)  %s\n",
               boxes.size(), countOk ? "✅" : "❌");
        int overlaps = 0;
        bool belowPlot = true;
        for (int i = 0; i < boxes.size(); ++i) {
            if (boxes[i].top() < 250) belowPlot = false;
            for (int j = i + 1; j < boxes.size(); ++j)
                if (boxes[i].intersects(boxes[j])) ++overlaps;
        }
        printf("  栏互相重叠=%d  期望=0  %s\n", overlaps,
               overlaps == 0 ? "✅" : "❌");
        printf("  栏都在绘图区下方: %s\n", belowPlot ? "✅" : "❌");
        for (int i = 0; i < boxes.size(); ++i)
            printf("    栏%d: 序列%d x[%.0f,%.0f] y[%.0f,%.0f]\n", i, ser[i],
                   boxes[i].left(), boxes[i].right(),
                   boxes[i].top(), boxes[i].bottom());
        if (!countOk || overlaps != 0 || !belowPlot) ++fail;
    }

    // 场景16: 藏起 A 的温度+湿度 → A 色曲线消失, B/C 仍在;
    //          图例栏数不变(藏掉的必须留着, 否则点不回来), 标签少两个
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        const QImage before = chart.grab().toImage();
        const int aBefore = countNear(before, CA, 15);
        const int labelBefore = chart.labelBoxes().size();
        chart.toggleSeriesVisible(0);
        chart.toggleSeriesVisible(3);
        qApp->processEvents();
        const QImage after = chart.grab().toImage();
        const int aAfter = countNear(after, CA, 15);
        const int bAfter = countNear(after, CB, 15);
        const int cAfter = countNear(after, CC, 15);
        printf("\n=== 场景16 藏起 A 温度+A湿度 ===\n");
        printf("  A色像素 %d -> %d\n", aBefore, aAfter);
        const bool aGone = aAfter < 60;
        const bool others = bAfter >= 200 && cAfter >= 200;
        printf("  A 曲线消失: %s   B/C 仍在: %s\n",
               aGone ? "✅" : "❌", others ? "✅" : "❌");
        const int labelAfter = chart.labelBoxes().size();
        printf("  标签数 %d -> %d(期望 6 -> 4)  %s\n", labelBefore, labelAfter,
               labelBefore == 6 && labelAfter == 4 ? "✅" : "❌");
        const int legendAfter = chart.legendBoxes().size();
        printf("  图例栏数 %d(期望仍为 6, 藏掉的要留着)  %s\n", legendAfter,
               legendAfter == 6 ? "✅" : "❌");
        if (!aGone || !others || labelAfter != 4 || legendAfter != 6) ++fail;
    }

    // 场景17: 再点两次恢复 → A 曲线回来, 标签回到 6 个
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        const int aBefore = countNear(chart.grab().toImage(), CA, 15);
        chart.toggleSeriesVisible(0);
        chart.toggleSeriesVisible(3);
        chart.toggleSeriesVisible(0);
        chart.toggleSeriesVisible(3);
        qApp->processEvents();
        const int aAfter = countNear(chart.grab().toImage(), CA, 15);
        const int labelAfter = chart.labelBoxes().size();
        printf("\n=== 场景17 再点两次恢复 ===\n");
        printf("  A色像素 %d -> %d\n", aBefore, aAfter);
        const bool back = aAfter >= 200 && labelAfter == 6;
        printf("  曲线恢复: %s   标签数=%d(期望 6)  %s\n",
               aAfter >= 200 ? "✅" : "❌", labelAfter,
               labelAfter == 6 ? "✅" : "❌");
        if (!back) ++fail;
    }

    // 场景18: 纵轴自适应 —— 藏掉 B/C 温度后, A 温度应铺满绘图区而不是
    //          仍挤在中间一小条。这才是真解决"曲线重叠"的地方。
    //          用无湿度数据, 免得 A 湿度(右轴, 本来就铺满)干扰跨度统计
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true, false, false, false));
        chart.show();
        qApp->processEvents();
        const int spanAll = verticalSpan(chart.grab().toImage(), CA, 15);
        chart.toggleSeriesVisible(1);
        chart.toggleSeriesVisible(2);
        qApp->processEvents();
        const int spanAOnly = verticalSpan(chart.grab().toImage(), CA, 15);
        printf("\n=== 场景18 纵轴跟着剩余曲线重算 ===\n");
        printf("  A温度 垂直跨度 %d px(三路都在) -> %d px(只剩 A)\n",
               spanAll, spanAOnly);
        const bool zoomed = spanAOnly > spanAll * 1.8;
        printf("  剩下的曲线放大铺满: %s\n", zoomed ? "✅" : "❌");
        if (!zoomed) ++fail;
    }

    // 场景19: 全藏完 → 所有序列色像素为 0, 图例栏仍在(点得回来)
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        for (int s = 0; s < 6; ++s)
            chart.toggleSeriesVisible(s);
        qApp->processEvents();
        const QImage img = chart.grab().toImage();
        const int a = countNear(img, CA, 15), b = countNear(img, CB, 15);
        const int c = countNear(img, CC, 15);
        printf("\n=== 场景19 全部藏起 ===\n");
        printf("  A/B/C 像素=%d/%d/%d  期望都 < 60\n", a, b, c);
        const bool allGone = a < 60 && b < 60 && c < 60;
        printf("  曲线全消失: %s\n", allGone ? "✅" : "❌");
        const int legend = chart.legendBoxes().size();
        const int labels = chart.labelBoxes().size();
        printf("  图例栏=%d(期望 6, 恢复入口还在)  标签=%d(期望 0)\n",
               legend, labels);
        const bool recoverable = legend == 6 && labels == 0;
        printf("  恢复入口保留: %s\n", recoverable ? "✅" : "❌");
        if (!allGone || !recoverable) ++fail;
    }

    // 场景20: 真实鼠标事件点图例栏 → 该序列被藏起, 且不触发拖动/查看数值
    {
        HistoryChart chart;
        chart.resize(900, 320);
        chart.setRecords(series(40, 200, 250, 300, 400, 420, 440, 0, 0,
                                true, true, true));
        chart.show();
        qApp->processEvents();
        QString tooltip;
        QObject::connect(&chart, &HistoryChart::inspectionChanged,
                         [&tooltip](const QString &s) { tooltip = s; });
        const QRectF first = chart.legendBoxes().at(0);
        const QPointF center = first.center();
        QMouseEvent press(QEvent::MouseButtonPress, center,
                          Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &press);
        QMouseEvent release(QEvent::MouseButtonRelease, center,
                            Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
        QApplication::sendEvent(&chart, &release);
        printf("\n=== 场景20 鼠标点图例栏切换序列 ===\n");
        const bool hidden = !chart.isSeriesVisible(chart.legendSeries().at(0));
        printf("  序列%d(A温度) 被藏起: %s\n", chart.legendSeries().at(0),
               hidden ? "✅" : "❌");
        const bool noTooltip = tooltip.isEmpty() || tooltip.contains("点击曲线");
        printf("  没有误触发数值提示: %s  (提示=%s)\n",
               noTooltip ? "✅" : "❌", qPrintable(tooltip));
        if (!hidden || !noTooltip) ++fail;
    }

    printf("\n════════════════════════\n");
    printf("%s\n", fail == 0 ? "✅ 全部场景通过" : "❌ 有场景不符合预期");
    return fail == 0 ? 0 : 1;
}
