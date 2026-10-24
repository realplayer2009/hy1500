#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《左岸励磁变外围接线图（YTT-1500 / BDXN3 改造）》SVG。

版式复刻现场既有 EPLAN 端子接线图（溪洛渡 成都院 DK 10036 系列）:
  * 双层图框 + 四角 A/B/C/D 分区与左右 1~6 行号
  * 左下标题栏(图号/比例/日期/专业/制图设计校核审查核定/设计证号/发证单位/院名)
  * 左侧「电缆表」+ 右侧「端子排表」; 每个端子一个圆符号, 同一根电缆的端子
    用竖向桥接线连起来, 回路号单独一列
  * 加热器与控制箱(温控箱)分为两个独立端子排 T2 / T1, 不合并成一个设备框

改图改本脚本后重新生成:
    python3 docs/hardware/make_zuoan_wiring.py
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "左岸励磁变外围接线图.svg")

# ---------------------------------------------------------------- 版面常量
W, H = 2000, 2060          # 图幅
FR = (40, 40, W - 40, H - 40)          # 外框
IR = (62, 62, W - 62, H - 62)          # 内框
ZONE_TOP = 26                          # A~D 行号带
COLS, ROWS = 4, 6                      # 分区

BLACK = "#000"
GREY = "#999"
FILL = "#fff"

# ---------------------------------------------------------------- 数据
# 电缆表: (序号, 电缆编号, 芯数截面, 电缆型号, 芯数, 备用, 项目代号,
#          电缆远端, 回路功能说明, 回路号)
CABLES = [
    (1, "Un-E/44-101", "4×4", "WDZA-KYJYRP-4X4", 4, "—", "1ZKK1", "温控箱 +XS1",
     "温控箱工作电源 L/N/PE", "101/102/103"),
    (2, "Un-E/44-102", "12×1.5", "WDZA-KYJYRP-12X1.5", 12, "—", "+B2~+B4",
     "温湿度传感器 A/B/C", "A/B/C 相温湿度传感器 −/GND/+/V0", "201~212"),
    (3, "Un-E/44-103", "8×1.0", "WDZA-KYJYRP-8X1.0", 8, "—", "+B3/+B4",
     "PT100 模块", "PT100-1/2 的 B/GND/A/V0", "301~308"),
    (4, "Un-E/44-104", "2×1.5", "WDZA-RVVP-2X1.5", 2, "—", "+W1",
     "域控主板 RS485", "RS485 A/B(触摸屏一组)", "601/602"),
    (5, "Un-E/44-105", "7×1.5", "WDZA-KYJYRP-7X1.5", 7, "—", "+OT1~+OT6",
     "加热器 +T2", "A/B/C 加热器 1/2 档驱动", "401~406"),
    (6, "Un-E/44-106", "3×1.5", "WDZA-KYJYRP-3X1.5", 3, "—", "2ZKK2",
     "带电显示器 +T3", "BDXN3 工作电源 L+/N/−", "501/502/503"),
    (7, "Un-E/44-107", "4×1.5", "WDZA-KYJYRP-4X1.5", 4, "—", "2ZKK3",
     "电磁锁 +T4", "电磁锁闭锁回路与三相 L/N", "701~708"),
    (8, "Un-E/44-108", "4×1.5", "WDZA-KYJYRP-4X1.5", 4, "—", "+K5/+K6",
     "微机五防", "带电允许信号(常开)", "801/802"),
]

# 端子排: (排号, 名称, [(端子号, 回路功能说明, 回路号, 桥接组)])
# 桥接组: 同一编号的相邻端子用竖向桥接线相连(同一根电缆)
TERMINALS = [
    ("T1", "温控箱端子（YTT-1500）", [
        (1, "温控箱工作电源 L", "101", 0),
        (2, "温控箱工作电源 N", "102", 0),
        (3, "温控箱工作电源 PE", "103", 0),
        (4, "A 相温湿度传感器 B2−", "201", 1),
        (5, "A 相温湿度传感器 GND", "202", 1),
        (6, "A 相温湿度传感器 A2+", "203", 1),
        (7, "A 相温湿度传感器 V0+", "204", 1),
        (8, "B 相温湿度传感器 B2−", "205", 2),
        (9, "B 相温湿度传感器 GND", "206", 2),
        (10, "B 相温湿度传感器 A2+", "207", 2),
        (11, "B 相温湿度传感器 V0+", "208", 2),
        (12, "C 相温湿度传感器 B2−", "209", 3),
        (13, "C 相温湿度传感器 GND", "210", 3),
        (14, "C 相温湿度传感器 A2+", "211", 3),
        (15, "C 相温湿度传感器 V0+", "212", 3),
        (16, "PT100-1 B3−", "301", 4),
        (17, "PT100-1 GND", "302", 4),
        (18, "PT100-1 A3+", "303", 4),
        (19, "PT100-1 V0+", "304", 4),
        (20, "PT100-2 B3−", "305", 5),
        (21, "PT100-2 GND", "306", 5),
        (22, "PT100-2 A3+", "307", 5),
        (23, "PT100-2 V0+", "308", 5),
        (24, "RS485 A", "601", 6),
        (25, "RS485 B", "602", 6),
    ]),
    ("T2", "加热器端子（独立设备）", [
        (1, "A 相加热器 1 档（OT1）", "401", 1),
        (2, "A 相加热器 2 档（OT2）", "402", 1),
        (3, "B 相加热器 1 档（OT3）", "403", 2),
        (4, "B 相加热器 2 档（OT4）", "404", 2),
        (5, "C 相加热器 1 档（OT5）", "405", 3),
        (6, "C 相加热器 2 档（OT6）", "406", 3),
        (7, "加热器公共零线 N", "407", 0),
    ]),
    ("T3", "带电显示器端子（BDXN3）", [
        (1, "工作电源 L+", "501", 0),
        (2, "工作电源 N", "502", 0),
        (3, "工作电源 −", "503", 0),
        (4, "电磁锁1 K2", "504", 1),
        (5, "电磁锁1 K1", "505", 1),
        (6, "电磁锁2 K4", "506", 2),
        (7, "电磁锁2 K3", "507", 2),
        (8, "微机五防 K6", "801", 3),
        (9, "微机五防 K5", "802", 3),
    ]),
    ("T4", "电磁锁端子", [
        (1, "A 相电磁锁 L", "701", 1),
        (2, "A 相电磁锁 N", "702", 1),
        (3, "B 相电磁锁 L", "703", 2),
        (4, "B 相电磁锁 N", "704", 2),
        (5, "C 相电磁锁 L", "705", 3),
        (6, "C 相电磁锁 N", "706", 3),
    ]),
]

NOTES = [
    "1. 本图为左岸励磁变外围接线技改图。原温湿度控制装置已由 YTT-1500（域控主板 + PA0715-N 触摸屏）替代；"
    "带电显示器采用福州博峰 BDXN3 系列，详见《BDXN3 系列使用说明书》。",
    "2. 加热器与控制箱（温控箱）为两个独立设备，分别设 T2、T1 两个端子排，现场不得合并布线。",
    "3. 电磁锁带电闭锁沿用原设计回路：ZKK3-2 → T3-4(K2) ═[BDXN3 电磁锁1 接点]═ T3-5(K1) → T4 三相 L，"
    "零线 ZKK3-4 → T4 三相 N。前提：电磁锁为失电闭锁型；若为得电闭锁型应改接 K5/K6。",
    "4. T3-8/9（K6/K5）送微机五防作带电允许信号。注意 BDXN3 的 K5/K6 带电与失电均闭合，"
    "与 K1/K2、K3/K4 极性相反，不能当作带电判据使用。",
    "5. 三路温湿度传感器分别接域控主板第二组 RS485；PT100 模块接第三组 RS485 与电源四线。"
    "A 用 OT1/OT2、B 用 OT3/OT4、C 用 OT5/OT6。",
    "6. BDXN3 的 RS485 通讯为定制项，协议需向厂家索取；本图全部采用无源接点硬接线，不依赖通信。",
    "7. 外扩输入 IN1~IN5 实际寄存器地址为 0x000C（bit0~bit4）；外扩输出 0x0033；OT 位掩码 0x0031。"
    "高压联锁参数见 YTT-1500 高级设置页。",
]


# ---------------------------------------------------------------- 绘图助手
def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


class Svg(object):
    def __init__(self):
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def line(self, x1, y1, x2, y2, w=1.0, color=BLACK):
        self.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                 'stroke-width="%.2f"/>' % (x1, y1, x2, y2, color, w))

    def rect(self, x, y, w, h, fill=FILL, sw=1.0, color=BLACK):
        self.add('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                 'stroke="%s" stroke-width="%.2f"/>' % (x, y, w, h, fill, color, sw))

    def circle(self, cx, cy, r, fill=FILL, sw=1.0):
        self.add('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" '
                 'stroke-width="%.2f"/>' % (cx, cy, r, fill, BLACK, sw))

    def text(self, x, y, s, size=11, anchor="start", weight="normal",
             color=BLACK):
        self.add('<text x="%.2f" y="%.2f" font-size="%.1f" text-anchor="%s" '
                 'font-weight="%s" fill="%s">%s</text>'
                 % (x, y, size, anchor, weight, color, esc(s)))

    def out(self):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
                'width="%d" height="%d" viewBox="0 0 %d %d">\n%s\n</svg>\n'
                % (W, H, W, H, "\n".join(self.parts)))


# ---------------------------------------------------------------- 图框
def draw_frame(s):
    x0, y0, x1, y1 = FR
    ix0, iy0, ix1, iy1 = IR
    s.rect(x0, y0, x1 - x0, y1 - y0, fill="none", sw=2.5)
    s.rect(ix0, iy0, ix1 - ix0, iy1 - iy0, fill="none", sw=1.0)

    cw = (ix1 - ix0) / float(COLS)
    rh = (iy1 - iy0) / float(ROWS)
    for i in range(COLS):
        c = chr(ord("A") + i)
        cx = ix0 + cw * (i + 0.5)
        s.text(cx, ZONE_TOP + 5, c, size=15, anchor="middle", weight="bold")
        s.text(cx, y1 - 7, c, size=15, anchor="middle", weight="bold")
    for j in range(ROWS):
        cy = iy0 + rh * (j + 0.5) + 5
        for xx in (x0 + 18, x1 - 18):
            s.text(xx, cy, str(j + 1), size=13, anchor="middle")


# ---------------------------------------------------------------- 标题栏
def draw_titleblock(s, x, y, w, h):
    s.rect(x, y, w, h, sw=1.5)
    r1, r2 = h * 0.28, h * 0.32
    s.line(x, y + r1, x + w, y + r1, 1.0)
    s.line(x, y + r1 + r2, x + w, y + r1 + r2, 1.0)
    s.line(x + w * 0.60, y, x + w * 0.60, y + r1, 1.0)
    s.line(x + w * 0.60, y + r1, x + w * 0.60, y + r1 + r2, 1.0)

    s.text(x + w * 0.30, y + r1 * 0.55, "中国水电顾问集团成都勘测设计研究院",
           size=14, anchor="middle", weight="bold")
    s.text(x + w * 0.30, y + r1 * 0.88, "溪洛渡  工程", size=11, anchor="middle")
    s.text(x + w * 0.80, y + r1 * 0.42, "电气二次", size=12, anchor="middle")
    s.text(x + w * 0.80, y + r1 * 0.82, "技    改", size=12, anchor="middle")

    s.text(x + w * 0.30, y + r1 + r2 * 0.40, "左岸励磁变外围接线图",
           size=14, anchor="middle", weight="bold")
    s.text(x + w * 0.30, y + r1 + r2 * 0.82, "（YTT-1500 / BDXN3 改造）",
           size=10, anchor="middle")
    for i, (k, v) in enumerate([("图  号", "DK 10036-TK-01"),
                                ("比  例", "1:1"), ("日  期", "2026.10")]):
        yy = y + r1 + r2 * (i + 0.5) / 3.0
        s.text(x + w * 0.615, yy, k, size=10, anchor="start")
        s.text(x + w * 0.74, yy, v, size=10, anchor="start")
        if i < 2:
            s.line(x + w * 0.60, y + r1 + r2 * (i + 1) / 3.0,
                   x + w, y + r1 + r2 * (i + 1) / 3.0, 0.6)

    signs = ["制 图", "设 计", "校 核", "审 查", "核 定"]
    cw = w / float(len(signs))
    for i, nm in enumerate(signs):
        xx = x + cw * i
        if i:
            s.line(xx, y + r1 + r2, xx, y + h, 0.6)
        s.text(xx + cw / 2, y + r1 + r2 + 16, nm, size=10, anchor="middle")
    s.text(x + w * 0.5, y + h - 9,
           "设计证号 A151001849    发证单位 中华人民共和国住房和城乡建设部",
           size=8.5, anchor="middle")


# ---------------------------------------------------------------- 表格
def draw_cable_table(s, x, y, w):
    """电缆表。"""
    cols = [("序号", 30), ("电缆编号", 86), ("芯数截面", 52), ("电缆型号", 100),
            ("芯数", 24), ("备用", 24), ("项目代号", 56), ("电缆远端", 100),
            ("回路功能说明", 140), ("回路号", 70)]
    total = sum(c[1] for c in cols)
    sc = w / float(total)
    xs, acc = [], 0.0
    for _, cw in cols:
        xs.append(acc)
        acc += cw * sc
    xs.append(acc)

    rh, hh, th = 30, 32, 28
    n = len(CABLES)
    h = th + hh + rh * n
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, th, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 18, "电  缆  表", size=13, weight="bold")
    for i, (nm, _) in enumerate(cols):
        cx = x + (xs[i] + xs[i + 1]) / 2
        if i:
            s.line(x + xs[i], y + th, x + xs[i], y + th + hh, 0.6)
        s.text(cx, y + th + 21, nm, size=9.5, anchor="middle")
    s.line(x, y + th + hh, x + w, y + th + hh, 0.8)
    for r, row in enumerate(CABLES):
        yy = y + th + hh + rh * r
        if r:
            s.line(x, yy, x + w, yy, 0.4, color=GREY)
        for i, v in enumerate(row):
            cx = x + (xs[i] + xs[i + 1]) / 2
            s.text(cx, yy + 20, str(v), size=9.5, anchor="middle")
    return h


def draw_terminal_table(s, x, y, w, strip):
    """端子排表。列序照原图: 端子排 | 回路功能说明 | 圆符号 | 端子号 | 回路号。
    同一根电缆的相邻端子用竖向桥接线相连。"""
    tag, name, rows = strip
    c_term, c_desc, c_dot, c_no, c_loop = 40, 290, 54, 44, 88
    total = c_term + c_desc + c_dot + c_no + c_loop
    sc = w / float(total)
    x_term = x
    x_desc = x_term + c_term * sc
    x_dot = x_desc + c_desc * sc
    x_no = x_dot + c_dot * sc
    x_loop = x_no + c_no * sc
    x_end = x_loop + c_loop * sc
    dot_cx = x_dot + c_dot * sc / 2
    no_x = dot_cx + 15

    rh, hh, th = 34, 32, 28
    n = len(rows)
    h = th + hh + rh * n
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, th, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 19, tag, size=13, weight="bold")
    s.text(x_desc + 6, y + 19, name, size=12, weight="bold")
    heads = [("端子排", x_term, x_desc), ("回路功能说明", x_desc, x_dot),
             ("", x_dot, x_no), ("端子号", x_no, x_loop),
             ("回路号", x_loop, x_end)]
    for nm, a, b in heads:
        if nm:
            s.text((a + b) / 2, y + th + 21, nm, size=10, anchor="middle")
        if a > x + 0.5:
            s.line(a, y + th, a, y + h, 0.6)
    s.line(x, y + th + hh, x + w, y + th + hh, 0.8)

    for r, (no, desc, loop, grp) in enumerate(rows):
        yy = y + th + hh + rh * r
        cy = yy + rh / 2
        if r:
            s.line(x, yy, x + w, yy, 0.4, color=GREY)
        s.circle(dot_cx, cy, 7)
        s.text(no_x, cy + 4, str(no), size=10.5, anchor="start")
        s.text(x_desc + 8, cy + 4, desc, size=10.5, anchor="start")
        s.text((x_loop + x_end) / 2, cy + 4, loop, size=10.5, anchor="middle")

    for i in range(len(rows) - 1):
        if rows[i][3] and rows[i][3] == rows[i + 1][3]:
            y1 = y + th + hh + rh * i + rh / 2
            y2 = y + th + hh + rh * (i + 1) + rh / 2
            s.line(dot_cx, y1, dot_cx, y2, 1.0)
    return h


def draw_device_table(s, x, y, w):
    """主要设备及端子排一览。"""
    devs = [("温控箱（YTT-1500）", "域控主板 + PA0715-N 触摸屏", "T1"),
            ("加热器", "A/B/C 三相，独立设备", "T2"),
            ("带电显示器", "福州博峰 BDXN3 系列", "T3"),
            ("电磁锁", "A/B/C 相，失电闭锁型", "T4")]
    rh, th = 56, 26
    h = th + rh * len(devs)
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, th, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 18, "主 要 设 备 及 端 子 排", size=12, weight="bold")
    for i, (a, b, c) in enumerate(devs):
        yy = y + th + rh * i
        if i:
            s.line(x, yy, x + w, yy, 0.4, color=GREY)
        s.text(x + 12, yy + 22, a, size=11, weight="bold")
        s.text(x + 12, yy + 40, b, size=10)
        s.text(x + w - 12, yy + 22, c, size=11, anchor="end", weight="bold")
    return h


def draw_legend(s, x, y, w, h):
    """符号图例。"""
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, 26, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 18, "符  号  图  例", size=12, weight="bold")
    items = [
        ("circle", "端子（圆符号）", "每个端子一个圆，圆旁数字为端子号"),
        ("bridge", "桥接线", "同一根电缆的相邻端子用竖线连通"),
        ("dash", "分区标记", "四周 A~D 为分区，1~6 为行号"),
        ("tag", "端子排号", "T1 温控箱 / T2 加热器 / T3 带电显示器 / T4 电磁锁"),
    ]
    for i, (kind, name, desc) in enumerate(items):
        yy = y + 26 + 30 + i * 52
        if kind == "circle":
            s.circle(x + 34, yy - 4, 7)
        elif kind == "bridge":
            s.line(x + 34, yy - 16, x + 34, yy + 8, 1.0)
            s.circle(x + 34, yy - 16, 6.5)
            s.circle(x + 34, yy + 8, 6.5)
        elif kind == "dash":
            s.rect(x + 20, yy - 14, 30, 20, fill="none", sw=0.6)
            s.text(x + 35, yy + 1, "A", size=9, anchor="middle")
        else:
            s.rect(x + 20, yy - 14, 30, 20, fill="#e8e8e8", sw=0.6)
            s.text(x + 35, yy + 1, "T1", size=9, anchor="middle")
        s.text(x + 62, yy + 1, name, size=10.5, weight="bold")
        s.text(x + 190, yy + 1, desc, size=10)
    return h


def draw_notes(s, x, y, w):
    """注释块, 返回底部 y。"""
    s.rect(x, y, w, 20, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 14, "注", size=11, weight="bold")
    yy = y + 20
    for nt in NOTES:
        maxc = int(w / 8.2)
        first = True
        while len(nt) > maxc:
            cut = nt.rfind("；", 0, maxc)
            if cut < 30:
                cut = maxc
            s.text(x + (10 if first else 26), yy + 16,
                   nt[:cut + 1] if cut < len(nt) else nt, size=9.5)
            nt = "    " + nt[cut + 1:]
            yy += 16
            first = False
            maxc = int(w / 8.2) - 2
        s.text(x + (10 if first else 26), yy + 16, nt, size=9.5)
        yy += 20
    return yy


# ---------------------------------------------------------------- 主流程
def main():
    s = Svg()
    draw_frame(s)

    s.text(W / 2, 92, "左岸励磁变外围接线图（YTT-1500 / BDXN3 改造）",
           size=22, anchor="middle", weight="bold")
    s.line(IR[0], 106, IR[2], 106, 1.0)

    top = 118
    lw = 700                     # 左列宽
    gap = 20
    rx = IR[0] + lw + gap        # 右列起点
    rw = IR[2] - rx              # 右列宽

    # 左列: 电缆表 + 主要设备及端子排
    h_cable = draw_cable_table(s, IR[0], top, lw)
    h_dev = draw_device_table(s, IR[0], top + h_cable + 18, lw)
    yl = top + h_cable + 18 + h_dev + 18

    # 右列: T1 温控箱
    h_t1 = draw_terminal_table(s, rx, top, rw, TERMINALS[0])
    yr = top + h_t1 + 18

    # 第 2 行: 左 T2 加热器 / 右 T3 带电显示器
    h_t2 = draw_terminal_table(s, IR[0], yl, lw, TERMINALS[1])
    h_t3 = draw_terminal_table(s, rx, yr, rw, TERMINALS[2])
    y2 = max(yl + h_t2, yr + h_t3) + 18

    # 第 3 行: 左 T4 电磁锁 / 右注释
    h_t4 = draw_terminal_table(s, IR[0], y2, lw, TERMINALS[3])
    y_notes = draw_notes(s, rx, y2, rw)
    y3 = max(y2 + h_t4, y_notes)

    # 左下补空: 符号图例(与 T4 同行)
    draw_legend(s, IR[0], y2 + h_t4 + 16, lw, y3 - (y2 + h_t4 + 16))

    # 底部: 标题栏通栏
    tb_h = 250
    tb_y = IR[3] - tb_h
    draw_titleblock(s, IR[0], tb_y, lw, tb_h)

    open(OUT, "w", encoding="utf-8").write(s.out())
    print("已生成 %s" % OUT)
    print("内容底部 y=%.0f  标题栏顶 y=%.0f  %s"
          % (y3, tb_y, "OK" if y3 < tb_y - 8 else "!! 重叠"))


if __name__ == "__main__":
    main()
