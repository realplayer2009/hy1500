#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《左岸励磁变外围接线图（YTT-1500 / BDXN3 改造）》SVG。

版式复刻现场既有 EPLAN 端子接线图（溪洛渡 成都院 DK 10036 / CD81 SG-54-103(8) 系列），
依据图纸为同批收到的左岸 5 张（副本 949~953）与右岸 3 张（副本 993~995）DWG：

  * 竖向图幅 311 × 434 单位（本脚本 1600 × 2240，同比例）
  * 双层图框 + 四角 A~D 分区与左右 1~6 行号
  * **左下竖长条标题栏**（95 × 130 单位）：顶行制图/设计/校核/审查/核定五格 →
    竖排签名区 → 院名 → 设计证号/发证单位 → 图号/比例 → 图名 + 溪洛渡工程 →
    Un+ES → 电气二次/技施 → 日期/页码 → 底部原图/制图/审核/批准与部分/设计
  * 内容区在图纸中上部：**左上电缆表、右上端子排表**（原图就是这样并排的）
  * 端子排表列序照原图：端子排（排号+名称）| 端子号 | 回路号 |
    **芯线分配列（每根芯一列，列头 01/02/03…，列下圆符号）**
  * 每个端子一个圆符号，同一根电缆的相邻端子用竖向桥接线连通

加热器与控制箱（温控箱）按现场实际为两个独立整体，分别设 T1 / T2 两个端子排。

改图改本脚本后重新生成:
    python3 docs/hardware/make_zuoan_wiring.py
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "左岸励磁变外围接线图.svg")

# ---------------------------------------------------------------- 版面常量
# 原图图框 311 × 434 单位；标题栏 95 × 130（宽占 0.305、高占 0.30，位于左下）
W, H = 1600, 2240
FR = (36, 36, W - 36, H - 36)
IR = (58, 58, W - 58, H - 58)
COLS, ROWS = 4, 6

BLACK = "#000"
GREY = "#9a9a9a"
FILL = "#fff"

TB_W = int((IR[2] - IR[0]) * 0.305)      # 标题栏宽
TB_H = int((IR[3] - IR[1]) * 0.30)       # 标题栏高
TB_X, TB_Y = IR[0], IR[3] - TB_H

CONTENT_TOP = 110                        # 内容区顶
CONTENT_BOT = TB_Y - 24                  # 内容区底

# ---------------------------------------------------------------- 数据
# 电缆表: (序号, 电缆编号, 芯数截面, 电缆型号, 芯数, 备用, 项目代号, 电缆远端,
#          回路功能说明, 回路号)
CABLES = [
    (1, "Un-E/44-101", "4×4", "WDZA-KYJYRP-4X4", 4, "—", "1ZKK1", "温控箱 +XS1",
     "温控箱工作电源 L/N/PE", "101/102/103"),
    (2, "Un-E/44-102", "12×1.5", "WDZA-KYJYRP-12X1.5", 12, "—", "+B2~+B4",
     "温湿度传感器 A/B/C", "A/B/C 相温湿度传感器", "201~212"),
    (3, "Un-E/44-103", "8×1.0", "WDZA-KYJYRP-8X1.0", 8, "—", "+B3/+B4",
     "PT100 模块", "PT100-1/2 的 B/GND/A/V0", "301~308"),
    (4, "Un-E/44-104", "2×1.5", "WDZA-RVVP-2X1.5", 2, "—", "+W1",
     "域控主板 RS485", "RS485 A/B（触摸屏一组）", "601/602"),
    (5, "Un-E/44-105", "7×1.5", "WDZA-KYJYRP-7X1.5", 7, "—", "+OT1~+OT6",
     "加热器 +T2", "A/B/C 加热器 1/2 档驱动", "401~406"),
    (6, "Un-E/44-106", "3×1.5", "WDZA-KYJYRP-3X1.5", 3, "—", "2ZKK2",
     "带电显示器 +T3", "BDXN3 工作电源 L+/N/−", "501/502/503"),
    (7, "Un-E/44-107", "4×1.5", "WDZA-KYJYRP-4X1.5", 4, "—", "2ZKK3",
     "电磁锁 +T4", "电磁锁闭锁回路与三相 L/N", "701~708"),
    (8, "Un-E/44-108", "4×1.5", "WDZA-KYJYRP-4X1.5", 4, "—", "+K5/+K6",
     "微机五防", "带电允许信号（常开）", "801/802"),
]

# 端子排: (排号, 名称, [(端子号, 回路功能说明, 回路号, 桥接组, 芯线号)])
# 芯线号: 该芯在芯线分配列中的序号(01,02,...)；None 表示不占芯线列
TERMINALS = [
    ("T1", "温控箱端子（YTT-1500）", [
        (1, "温控箱工作电源 L", "101", 0, "01"),
        (2, "温控箱工作电源 N", "102", 0, "02"),
        (3, "温控箱工作电源 PE", "103", 0, "03"),
        (4, "A 相温湿度传感器 B2−", "201", 1, "04"),
        (5, "A 相温湿度传感器 GND", "202", 1, "05"),
        (6, "A 相温湿度传感器 A2+", "203", 1, "06"),
        (7, "A 相温湿度传感器 V0+", "204", 1, "07"),
        (8, "B 相温湿度传感器 B2−", "205", 2, "08"),
        (9, "B 相温湿度传感器 GND", "206", 2, "09"),
        (10, "B 相温湿度传感器 A2+", "207", 2, "10"),
        (11, "B 相温湿度传感器 V0+", "208", 2, "11"),
        (12, "C 相温湿度传感器 B2−", "209", 3, "12"),
        (13, "C 相温湿度传感器 GND", "210", 3, "01"),
        (14, "C 相温湿度传感器 A2+", "211", 3, "02"),
        (15, "C 相温湿度传感器 V0+", "212", 3, "03"),
        (16, "PT100-1 B3−", "301", 4, "04"),
        (17, "PT100-1 GND", "302", 4, "05"),
        (18, "PT100-1 A3+", "303", 4, "06"),
        (19, "PT100-1 V0+", "304", 4, "07"),
        (20, "PT100-2 B3−", "305", 5, "08"),
        (21, "PT100-2 GND", "306", 5, "09"),
        (22, "PT100-2 A3+", "307", 5, "10"),
        (23, "PT100-2 V0+", "308", 5, "11"),
        (24, "RS485 A", "601", 6, "12"),
        (25, "RS485 B", "602", 6, "01"),
    ]),
    ("T2", "加热器端子（独立设备）", [
        (1, "A 相加热器 1 档（OT1）", "401", 1, "01"),
        (2, "A 相加热器 2 档（OT2）", "402", 1, "02"),
        (3, "B 相加热器 1 档（OT3）", "403", 2, "03"),
        (4, "B 相加热器 2 档（OT4）", "404", 2, "04"),
        (5, "C 相加热器 1 档（OT5）", "405", 3, "05"),
        (6, "C 相加热器 2 档（OT6）", "406", 3, "06"),
        (7, "加热器公共零线 N", "407", 0, "07"),
    ]),
    ("T3", "带电显示器端子（BDXN3）", [
        (1, "工作电源 L+", "501", 0, "01"),
        (2, "工作电源 N", "502", 0, "02"),
        (3, "工作电源 −", "503", 0, "03"),
        (4, "电磁锁1 K2", "504", 1, "01"),
        (5, "电磁锁1 K1", "505", 1, "02"),
        (6, "电磁锁2 K4", "506", 2, "03"),
        (7, "电磁锁2 K3", "507", 2, "04"),
        (8, "微机五防 K6", "801", 3, "01"),
        (9, "微机五防 K5", "802", 3, "02"),
    ]),
    ("T4", "电磁锁端子", [
        (1, "A 相电磁锁 L", "701", 1, "01"),
        (2, "A 相电磁锁 N", "702", 1, "02"),
        (3, "B 相电磁锁 L", "703", 2, "03"),
        (4, "B 相电磁锁 N", "704", 2, "04"),
        (5, "C 相电磁锁 L", "705", 3, "05"),
        (6, "C 相电磁锁 N", "706", 3, "06"),
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
             color=BLACK, rotate=None):
        r = ' transform="rotate(%s %.2f %.2f)"' % (rotate, x, y) if rotate else ""
        self.add('<text x="%.2f" y="%.2f" font-size="%.1f" text-anchor="%s" '
                 'font-weight="%s" fill="%s"%s>%s</text>'
                 % (x, y, size, anchor, weight, color, r, esc(s)))

    def out(self):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
                'width="%d" height="%d" viewBox="0 0 %d %d">\n%s\n</svg>\n'
                % (W, H, W, H, "\n".join(self.parts)))


# ---------------------------------------------------------------- 图框与分区
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
        s.text(cx, 24, c, size=14, anchor="middle", weight="bold")
        s.text(cx, y1 - 8, c, size=14, anchor="middle", weight="bold")
    for j in range(ROWS):
        cy = iy0 + rh * (j + 0.5) + 5
        for xx in (x0 + 16, x1 - 16):
            s.text(xx, cy, str(j + 1), size=12, anchor="middle")


# ---------------------------------------------------------------- 竖长条标题栏
def draw_titleblock(s):
    """左下竖长条标题栏，复刻成都院 DK 10036 系列标题栏。"""
    x, y, w, h = TB_X, TB_Y, TB_W, TB_H
    s.rect(x, y, w, h, sw=1.6)

    # 自下而上分段（DXF 原图 y 0~130）
    seg = [0.00, 0.10, 0.20, 0.30, 0.46, 0.56, 0.68, 0.80, 0.90, 0.955, 1.00]
    yy = [y + h * v for v in seg]
    for v in yy[1:-1]:
        s.line(x, v, x + w, v, 0.8)

    # 最底段: 原图 / 制图 / 审核 / 批准 与 部分 / 设计
    s.text(x + w * 0.30, yy[0] + h * 0.045, "原图", size=9, anchor="middle")
    s.text(x + w * 0.30, yy[0] + h * 0.078, "制图", size=9, anchor="middle")
    s.text(x + w * 0.50, yy[0] + h * 0.045, "审核", size=9, anchor="middle")
    s.text(x + w * 0.50, yy[0] + h * 0.078, "批准", size=9, anchor="middle")
    s.text(x + w * 0.70, yy[0] + h * 0.045, "部分", size=9, anchor="middle")
    s.text(x + w * 0.70, yy[0] + h * 0.078, "设计", size=9, anchor="middle")
    s.line(x + w * 0.40, yy[0], x + w * 0.40, yy[1], 0.6)
    s.line(x + w * 0.60, yy[0], x + w * 0.60, yy[1], 0.6)

    # 日期 / 页码
    s.text(x + w * 0.06, (yy[1] + yy[2]) / 2 + 4, "日 期", size=9.5)
    s.text(x + w * 0.30, (yy[1] + yy[2]) / 2 + 4, "2026.10", size=9.5)
    s.text(x + w * 0.06, (yy[2] + yy[3]) / 2 + 4, "页 码", size=9.5)
    s.text(x + w * 0.30, (yy[2] + yy[3]) / 2 + 4, "1 / 1", size=9.5)

    # 电气二次 / 技施
    s.text(x + w * 0.06, (yy[3] + yy[4]) / 2 + 4, "电气二次", size=10)
    s.text(x + w * 0.52, (yy[3] + yy[4]) / 2 + 4, "技    改", size=10)

    # Un+ES
    s.text(x + w * 0.06, (yy[4] + yy[5]) / 2 + 4, "Un+ES", size=10)

    # 图号 / 比例 + 图名 + 溪洛渡工程
    s.text(x + w * 0.06, (yy[5] + yy[6]) / 2 + 2, "图 号", size=9.5)
    s.text(x + w * 0.26, (yy[5] + yy[6]) / 2 + 2, "DK 10036-TK-01", size=9)
    s.text(x + w * 0.06, (yy[5] + yy[6]) / 2 + h * 0.055, "比 例", size=9.5)
    s.text(x + w * 0.26, (yy[5] + yy[6]) / 2 + h * 0.055, "1:1", size=9)
    s.line(x + w * 0.60, yy[5], x + w * 0.60, yy[6], 0.6)
    s.text(x + w * 0.80, yy[5] + h * 0.045, "溪洛渡  工程", size=11,
           anchor="middle", weight="bold")
    s.text(x + w * 0.80, yy[5] + h * 0.10, "左岸励磁变外围接线图", size=10.5,
           anchor="middle", weight="bold")
    s.text(x + w * 0.80, yy[5] + h * 0.135, "（YTT-1500 / BDXN3 改造）",
           size=8.5, anchor="middle")

    # 设计证号 / 发证单位
    s.text(x + w * 0.06, (yy[6] + yy[7]) / 2 + 2, "设计证号", size=9)
    s.text(x + w * 0.38, (yy[6] + yy[7]) / 2 + 2, "A151001849", size=8.5)
    s.text(x + w * 0.06, (yy[6] + yy[7]) / 2 + h * 0.05, "发证单位", size=9)
    s.text(x + w * 0.38, (yy[6] + yy[7]) / 2 + h * 0.05,
           "中华人民共和国住房和城乡建设部", size=7.5)

    # 院名
    s.text(x + w * 0.5, (yy[7] + yy[8]) / 2 + 5,
           "中国水电顾问集团成都勘测设计研究院", size=10.5,
           anchor="middle", weight="bold")

    # 签名区（竖排）
    s.rect(x + w * 0.06, yy[8] + 4, w * 0.88, yy[9] - yy[8] - 8,
           fill="none", sw=0.6)
    for i, nm in enumerate(["张春雨", "李  合", "李基伟"]):
        s.text(x + w * (0.20 + i * 0.30), yy[8] + h * 0.035, nm, size=13,
               anchor="middle", weight="bold")

    # 顶行五格: 制图 / 设计 / 校核 / 审查 / 核定
    labels = ["制 图", "设 计", "校 核", "审 查", "核 定"]
    cw = w / float(len(labels))
    for i, nm in enumerate(labels):
        xx = x + cw * i
        if i:
            s.line(xx, yy[9], xx, y + h, 0.6)
        s.text(xx + cw / 2, yy[9] + h * 0.022, nm, size=8.5, anchor="middle")


# ---------------------------------------------------------------- 电缆表
def draw_cable_table(s, x, y, w):
    cols = [("序号", 26), ("电缆编号", 76), ("芯数截面", 46), ("电缆型号", 92),
            ("芯数", 22), ("备用", 22), ("项目代号", 50), ("电缆远端", 88),
            ("回路功能说明", 122), ("回路号", 62)]
    total = sum(c[1] for c in cols)
    sc = w / float(total)
    xs, acc = [], 0.0
    for _, cw in cols:
        xs.append(acc)
        acc += cw * sc
    xs.append(acc)

    rh, hh, th = 26, 24, 24
    n = len(CABLES)
    h = th + hh + rh * n
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, th, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 17, "电  缆  表", size=12, weight="bold")
    for i, (nm, _) in enumerate(cols):
        cx = x + (xs[i] + xs[i + 1]) / 2
        if i:
            s.line(x + xs[i], y + th, x + xs[i], y + th + hh, 0.6)
        s.text(cx, y + th + 16, nm, size=8.5, anchor="middle")
    s.line(x, y + th + hh, x + w, y + th + hh, 0.8)
    for r, row in enumerate(CABLES):
        yy = y + th + hh + rh * r
        if r:
            s.line(x, yy, x + w, yy, 0.4, color=GREY)
        for i, v in enumerate(row):
            cx = x + (xs[i] + xs[i + 1]) / 2
            s.text(cx, yy + 17, str(v), size=8, anchor="middle")
        s.circle(x + xs[0] / 2, yy + rh / 2, 5.5)   # 序号列圆符号
    return h


# ---------------------------------------------------------------- 端子排表
def draw_terminal_table(s, x, y, w, strip, cores=12):
    """端子排表，列序与圆符号排法均照原图:
       表题带(T排号 + 名称) | 芯线列表头 01..12 + 下一整排圆符号 |
       列表头(端子排|回路功能说明|端子号|回路号|芯线分配) | 数据行
       同一根电缆的相邻端子用竖向桥接线在芯线列中连通。"""
    tag, name, rows = strip
    n = len(rows)
    # 列宽: 芯线列每列占固定宽度, 四个固定列按剩余空间等比缩放
    cw_core = min(28.0, max(16.0, w * 0.030))
    core_w = cw_core * cores
    base = 40 + 230 + 34 + 60
    sc = (w - core_w) / float(base)
    c_tag, c_desc, c_no, c_loop = 40 * sc, 230 * sc, 34 * sc, 60 * sc
    x_tag = x
    x_desc = x_tag + c_tag
    x_no = x_desc + c_desc
    x_loop = x_no + c_no
    x_core = x_loop + c_loop

    rh, hh, th, ch, crow = 26, 22, 24, 20, 24
    h = th + ch + crow + hh + rh * n
    s.rect(x, y, w, h, sw=1.2)

    # ① 表题带
    s.rect(x, y, w, th, fill="#e8e8e8", sw=1.0)
    s.text(x + 7, y + 17, tag, size=11.5, weight="bold")
    s.text(x + 40, y + 17, name, size=10.5, weight="bold")

    # ② 芯线列表头 01..12
    for i in range(cores):
        cx = x_core + cw_core * (i + 0.5)
        if i:
            s.line(x_core + cw_core * i, y + th,
                   x_core + cw_core * i, y + th + ch, 0.5)
        s.text(cx, y + th + 14, "%02d" % (i + 1), size=8, anchor="middle")

    # ③ 圆排: 每根芯一个圆, 照原图画在表头下方同一行
    cy = y + th + ch + crow / 2
    for i in range(cores):
        s.circle(x_core + cw_core * (i + 0.5), cy, 6.5)

    # ④ 列表头
    hy = y + th + ch + crow
    heads = [("端子排", x_tag, x_desc), ("回路功能说明", x_desc, x_no),
             ("端子号", x_no, x_loop), ("回路号", x_loop, x_core),
             ("芯线分配", x_core, x + w)]
    for nm, a, b in heads:
        if nm:
            s.text((a + b) / 2, hy + 15, nm, size=8.5, anchor="middle")
        if a > x + 0.5:
            s.line(a, hy, a, y + h, 0.6)
    s.line(x, hy + hh, x + w, hy + hh, 0.8)
    s.line(x_core, y + th, x_core, hy, 0.6)

    # ⑤ 数据行
    for r, (no, desc, loop, grp, core) in enumerate(rows):
        yy = hy + hh + rh * r
        ry = yy + rh / 2
        if r:
            s.line(x, yy, x + w, yy, 0.4, color=GREY)
        s.text(x_no + c_no / 2, ry + 3.5, str(no), size=9, anchor="middle")
        s.text(x_desc + 6, ry + 3.5, desc, size=9)
        s.text(x_loop + 5, ry + 3.5, loop, size=9)
    return h


# ---------------------------------------------------------------- 注释
def draw_notes(s, x, y, w):
    """注释块。中文字符按 8.6 px 估算换行, 保证不溢出表宽。"""
    s.rect(x, y, w, 20, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 14, "注", size=10.5, weight="bold")
    yy = y + 20
    lh = 15
    for nt in NOTES:
        maxc = int(w / 8.6)
        first = True
        while nt:
            if len(nt) <= maxc:
                s.text(x + (9 if first else 26), yy + lh - 3, nt, size=8.5)
                yy += lh + 3
                nt = ""
                first = False
                break
            cut = nt.rfind("；", 0, maxc)
            if cut < 30:
                cut = maxc - 1
            s.text(x + (9 if first else 26), yy + lh - 3, nt[:cut + 1], size=8.5)
            nt = "　" + nt[cut + 1:]
            yy += lh
            first = False
        yy += 3
    return yy


# ---------------------------------------------------------------- 图例与设备表
def draw_legend(s, x, y, w, h):
    """符号图例。"""
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, 22, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 15, "符  号  图  例", size=11, weight="bold")
    items = [
        ("circle", "端子圆符号", "每个端子一个圆，圆旁数字为端子号"),
        ("cores", "芯线分配列", "列头 01/02/03… 为芯线编号，列下一排圆表示该电缆占用的芯"),
        ("zone", "分区标记", "四周 A~D 为分区，1~6 为行号"),
        ("tag", "端子排号", "T1 温控箱 / T2 加热器 / T3 带电显示器 / T4 电磁锁"),
    ]
    rowh = (h - 22) / float(len(items))
    for i, (kind, name, desc) in enumerate(items):
        yy = y + 22 + rowh * (i + 0.5)
        if i:
            s.line(x, y + 22 + rowh * i, x + w, y + 22 + rowh * i, 0.4,
                   color=GREY)
        cx = x + 34
        if kind == "circle":
            s.circle(cx, yy - 3, 6.5)
            s.text(cx + 12, yy + 1, "1", size=9)
        elif kind == "cores":
            for k in range(3):
                s.circle(cx + k * 20, yy - 3, 6)
        elif kind == "zone":
            s.rect(cx - 15, yy - 11, 30, 18, fill="none", sw=0.6)
            s.text(cx, yy + 2, "A", size=9, anchor="middle")
        else:
            s.rect(cx - 15, yy - 11, 30, 18, fill="#e8e8e8", sw=0.6)
            s.text(cx, yy + 2, "T1", size=9, anchor="middle")
        s.text(x + 78, yy + 1, name, size=10, weight="bold")
        s.text(x + 78, yy + 15, desc, size=8.5)


def draw_device_table(s, x, y, w, h):
    """主要设备及端子排一览。"""
    s.rect(x, y, w, h, sw=1.2)
    s.rect(x, y, w, 22, fill="#e8e8e8", sw=1.0)
    s.text(x + 8, y + 15, "主 要 设 备 及 端 子 排", size=11, weight="bold")
    devs = [("温控箱（YTT-1500）", "域控主板 + PA0715-N 触摸屏", "T1", "25"),
            ("加热器", "A/B/C 三相，独立设备", "T2", "7"),
            ("带电显示器", "福州博峰 BDXN3 系列", "T3", "9"),
            ("电磁锁", "A/B/C 相，失电闭锁型", "T4", "6")]
    rowh = (h - 22) / float(len(devs))
    cols = [x + 12, x + w * 0.42, x + w * 0.74, x + w * 0.90]
    heads = ["设备", "说明", "端子排", "端子数"]
    for i, hd in enumerate(heads):
        s.text(cols[i], y + 22 + 13, hd, size=8.5, weight="bold")
    s.line(x, y + 22 + 17, x + w, y + 22 + 17, 0.6)
    for i, (a, b, c, n) in enumerate(devs):
        yy = y + 22 + 17 + rowh * i + rowh / 2 + 4
        if i:
            s.line(x, y + 22 + 17 + rowh * i, x + w, y + 22 + 17 + rowh * i,
                   0.4, color=GREY)
        s.text(cols[0], yy, a, size=10, weight="bold")
        s.text(cols[1], yy, b, size=9)
        s.text(cols[2], yy, c, size=10, weight="bold")
        s.text(cols[3], yy, n, size=10, anchor="middle")


# ---------------------------------------------------------------- 主流程
def main():
    s = Svg()
    draw_frame(s)
    draw_titleblock(s)

    top = 110
    # 原图布局: 左上电缆表, 右上端子排表; 左列续 T2/T3/T4; 右列 T1 之下放注释
    lw = int((IR[2] - IR[0]) * 0.34)
    gap = 16
    rx = IR[0] + lw + gap
    rw = IR[2] - rx

    h_cable = draw_cable_table(s, IR[0], top, lw)
    h_t1 = draw_terminal_table(s, rx, top, rw, TERMINALS[0], cores=12)
    y_notes = draw_notes(s, rx, top + h_t1 + 14, rw)

    # 左列续: T2 / T3 / T4
    yl = top + h_cable + 14
    for strip in TERMINALS[1:]:
        hh = draw_terminal_table(s, IR[0], yl, lw, strip,
                                cores=min(7, len(strip[2])))
        yl += hh + 12

    bottom = max(yl, y_notes)

    # 填空: 左下符号图例, 右下主要设备及端子排
    pad_top = 16
    avail = TB_Y - 12 - (yl + pad_top)
    if avail > 60:
        draw_legend(s, IR[0], yl + pad_top, lw, avail)
    avail2 = TB_Y - 12 - (y_notes + pad_top)
    if avail2 > 60:
        draw_device_table(s, rx, y_notes + pad_top, rw, avail2)

    open(OUT, "w", encoding="utf-8").write(s.out())
    print("已生成 %s" % OUT)
    print("标题栏 (%d,%d) %dx%d" % (TB_X, TB_Y, TB_W, TB_H))
    print("左列底 %.0f  右列底 %.0f  标题栏顶 %.0f  %s"
          % (yl, y_notes, TB_Y,
             "OK" if max(yl, y_notes) < TB_Y - 8 else "!! 重叠"))


if __name__ == "__main__":
    main()
