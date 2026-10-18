// 密码框测试: 位数跟随密码长度, 输满自动校验, 错误可重试
// 用非模态 show() + processEvents() 驱动 —— offscreen 平台下模态 exec()
// 的事件循环不转 QTimer, 会一直卡住
#include "appui.h"
#include <QApplication>
#include <QPushButton>
#include <cstdio>

static void click(PasswordDialog *dlg, const QString &text)
{
    const QList<QPushButton *> btns = dlg->findChildren<QPushButton *>();
    for (QPushButton *b : btns) {
        if (b->text() == text) {
            b->click();
            qApp->processEvents();
            return;
        }
    }
    printf("    [找不到按钮 %s]\n", qPrintable(text));
}

// 新建对话框并按一串键, 返回最终 result
static int run(const QStringList &keys, const QString &pwd = QString::fromUtf8("0000"))
{
    PasswordDialog dlg(nullptr, pwd);
    dlg.show();
    qApp->processEvents();
    for (const QString &k : keys)
        click(&dlg, k);
    return dlg.result();
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    int fail = 0;
    const int ACC = QDialog::Accepted, REJ = QDialog::Rejected;

    printf("\n=== 密码框 4 位(0000) ===\n");

    // 1) 正确密码: 点 4 个 0 应输满即通过
    {
        const int r = run({ "0", "0", "0", "0" });
        printf("  输满 4 位自动通过: %s\n", r == ACC ? "✅" : "❌");
        if (r != ACC) ++fail;
    }

    // 2) 只输 3 位 + 点"确定": 位数不足应被拦下
    {
        const int r = run({ "0", "0", "0", "确定" });
        printf("  只输 3 位点确定被拦下: %s\n", r == REJ ? "✅" : "❌");
        if (r != REJ) ++fail;
    }

    // 3) 错误密码: 输满 4 位错误数字应清空且不进入
    {
        const int r = run({ "1", "2", "3", "4" });
        printf("  输错 4 位不进入: %s\n", r == REJ ? "✅" : "❌");
        if (r != REJ) ++fail;
    }

    // 4) 取消应关闭且不通过
    {
        const int r = run({ "取消" });
        printf("  点取消不进入: %s\n", r == REJ ? "✅" : "❌");
        if (r != REJ) ++fail;
    }

    // 5) 退格改错后补对应密码能进入
    {
        const int r = run({ "9", "删除", "0", "0", "0", "0" });
        printf("  退格后补对应密码能进入: %s\n", r == ACC ? "✅" : "❌");
        if (r != ACC) ++fail;
    }

    // 6) 清空后重新输能进入
    {
        const int r = run({ "1", "1", "清空", "0", "0", "0", "0" });
        printf("  清空后重输能进入: %s\n", r == ACC ? "✅" : "❌");
        if (r != ACC) ++fail;
    }

    // 7) 5 位数字: 第 5 位应被忽略(位数封顶), 输对应 4 位仍能过
    {
        const int r = run({ "0", "0", "0", "0", "5" });
        printf("  多输一位被忽略、对应密码仍通过: %s\n", r == ACC ? "✅" : "❌");
        if (r != ACC) ++fail;
    }

    // 8) 位数真的跟随密码: 换成 6 位密码时要输满 6 位
    {
        const int r5 = run({ "1", "2", "3", "4", "5" },
                           QString::fromUtf8("123456"));
        const int r6 = run({ "1", "2", "3", "4", "5", "6" },
                           QString::fromUtf8("123456"));
        printf("  6 位密码: 输 5 位进不去(%s), 输满 6 位能进(%s)\n",
               r5 == REJ ? "✅" : "❌", r6 == ACC ? "✅" : "❌");
        if (r5 != REJ || r6 != ACC) ++fail;
    }

    // 9) 空密码: 任何输入都不放行
    {
        const int r = run({ "确定" }, QString());
        printf("  空密码时点确定也进不去: %s\n", r == REJ ? "✅" : "❌");
        if (r != REJ) ++fail;
    }

    printf("\n════════════════════════\n");
    printf("%s\n", fail == 0 ? "✅ 密码框全部通过" : "❌ 有场景不符合预期");
    return fail == 0 ? 0 : 1;
}
