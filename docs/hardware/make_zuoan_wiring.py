#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《左岸励磁变 YTT-1500 外围接线图》SVG。

用法:  python3 docs/hardware/make_zuoan_wiring.py
输出:  docs/hardware/左岸励磁变YTT1500外围接线图.svg

改图就改这个脚本重跑, 不要在 SVG 上手改——所有坐标都从这里出。
版面: 左列电源母排+三个 ZKK 开关, 中列 BDXN3/触摸屏/域控主板,
      右列现场负载(电磁锁/传感器/加热器/指示报警), 底部两张端子排表, 最底部注释。
走廊: 中列与右列之间 x=1240~1300, 右列外侧 x=1880, 底部 y=620。
"""
import os

FONT = "'PingFang SC','Heiti SC','Noto Sans CJK SC','Source Han Sans SC',sans-serif"

W_POWER, W_CTRL, W_SIG, W_TBL = 3.0, 1.8, 1.2, 1.0
C_POWER, C_N, C_CTRL, C_SIG = "#c62828", "#1565c0", "#37474f", "#6a1b9a"
C_BOX, C_TXT, C_MUT = "#263238", "#212121", "#616161"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def raw(self, s):
        self.parts.append(s)

    def line(self, x1, y1, x2, y2, w=W_CTRL, color=C_CTRL, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.raw('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                  'stroke-width="%.1f"%s/>' % (x1, y1, x2, y2, color, w, d))

    def poly(self, pts, w=W_CTRL, color=C_CTRL, dash=None):
        p = " ".join("%.1f,%.1f" % (x, y) for x, y in pts)
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.raw('<polyline points="%s" fill="none" stroke="%s" '
                  'stroke-width="%.1f" stroke-linejoin="round"%s/>' % (p, color, w, d))

    def rect(self, x, y, w, h, fill="none", stroke=C_BOX, sw=W_TBL, rx=0):
        self.raw('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" '
                  'fill="%s" stroke="%s" stroke-width="%.1f"/>'
                  % (x, y, w, h, rx, fill, stroke, sw))

    def text(self, x, y, s, size=14, anchor="start", weight="normal", color=C_TXT):
        self.raw('<text x="%.1f" y="%.1f" font-family="%s" font-size="%.1f" '
                  'text-anchor="%s" font-weight="%s" fill="%s">%s</text>'
                  % (x, y, FONT, size, anchor, weight, color, esc(s)))

    def term(self, x, y, label, side="top", size=11, color=C_TXT, r=3.4):
        self.raw('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#fff" '
                  'stroke="%s" stroke-width="1.5"/>' % (x, y, r, C_BOX))
        if side == "top":
            self.text(x, y - 8, label, size, "middle", color=color)
        elif side == "bottom":
            self.text(x, y + 15, label, size, "middle", color=color)
        elif side == "left":
            self.text(x - 8, y + 4, label, size, "end", color=color)
        else:
            self.text(x + 8, y + 4, label, size, "start", color=color)

    def dot(self, x, y, r=3.2, color=C_CTRL):
        self.raw('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (x, y, r, color))

    def render(self):
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
                'viewBox="0 0 %d %d">\n'
                '<rect width="%d" height="%d" fill="#ffffff"/>\n'
                % (self.w, self.h, self.w, self.h, self.w, self.h)
                + "\n".join(self.parts) + "\n</svg>\n")


# ================================================================ 版面常量
PW, PH = 2400, 1740
s = Svg(PW, PH)

L1X, NX = 108, 168
BUS_TOP, BUS_BOT = 180, 960
SW_X, SW_LEN = 200, 46

BD = (340, 180, 680, 250)          # BDXN3      340..1020 x 180..430
TS = (340, 460, 680, 110)          # 触摸屏      340..1020 x 460..570
MB = (340, 700, 900, 200)          # 域控主板    340..1240 x 700..900
RX, RW = 1300, 560                 # 右列        1300..1860
LK = (RX, 180, RW, 280)            # 电磁锁
SN = (RX, 480, RW, 120)            # 传感器
HT = (RX, 690, RW, 120)            # 加热器
AL = (RX, 830, RW, 100)            # 指示报警
T1 = (40, 990)                     # 端子排 XT
T2 = (1300, 990)                   # 端子排 XT2
NOTE_Y = 1552

FIRE_Y, NEUT_Y = 262, 276          # 电磁锁框内火线/零线分配母线
CORR = 1270                        # 中列与右列之间的走廊
RCORR = 1880                       # 右列外侧走廊
ZERO_Y = 675                       # 零线水平走廊(触摸屏底 570 与域控主板顶 700 之间)


def box_meta(b, title, sub, fill):
    x, y, w, h = b
    s.rect(x, y, w, h, fill=fill, stroke=C_BOX, sw=1.6, rx=4)
    s.text(x + 16, y + 26, title, 17, "start", "bold")
    if sub:
        s.text(x + 16, y + 46, sub, 12, "start", "normal", C_MUT)
        s.line(x + 10, y + 58, x + w - 10, y + 58, 0.8, "#cfd8dc")
    return x + w


# ================================================================ 标题栏
TX, TY, TW, TH = 40, 30, 2320, 92
s.rect(TX, TY, TW, TH, fill="#fafafa", stroke=C_BOX, sw=1.6)
s.text(TX + 24, TY + 40, "左岸励磁变外围接线图（改造后）", 30, "start", "bold")
s.text(TX + 24, TY + 70,
       "厂高变压器带电显示器、电磁锁、温湿度控制装置技改 —— 博峰 BDXN3 带电显示 + YTT-1500 温湿度控制",
       16, "start", "normal", C_MUT)
for i, (k, v) in enumerate([("图号", "ZA-LC-2026-01"),
                            ("部门", "电气维修部发电分分部"),
                            ("制图", "YTT-1500 / RS485Control"),
                            ("日期", "2026-10-23")]):
    x = TX + 1330 + i * 245
    s.line(x, TY + 8, x, TY + TH - 8, 0.8, "#bdbdbd")
    s.text(x + 14, TY + 36, k, 12, "start", "normal", C_MUT)
    s.text(x + 14, TY + 64, v, 13, "start", "bold")

# ================================================================ 电源母排
s.text(L1X, BUS_TOP - 12, "L1", 17, "middle", "bold", C_POWER)
s.text(NX, BUS_TOP - 12, "N", 17, "middle", "bold", C_N)
s.line(L1X, BUS_TOP, L1X, BUS_BOT, W_POWER, C_POWER)
s.line(NX, BUS_TOP, NX, BUS_BOT, W_POWER, C_N)
s.text(L1X - 16, (BUS_TOP + BUS_BOT) // 2, "AC 220V", 12, "middle", "normal", C_MUT)


def sw2(y, name, aux):
    """两极开关: L 极在 y, N 极在 y+36, 均水平布置。返回 (L出点, N出点)。"""
    for bx, tag, yy in ((L1X, "1", y), (NX, "3", y + 36)):
        col = C_POWER if bx == L1X else C_N
        s.line(bx, yy, SW_X, yy, W_POWER, col)
        s.term(SW_X, yy, tag, "top", 10, C_MUT)
        s.term(SW_X + SW_LEN, yy, "2" if bx == L1X else "4", "top", 10, C_MUT)
        s.line(SW_X, yy, SW_X + 8, yy, W_CTRL, C_BOX)
        s.line(SW_X + 38, yy, SW_X + SW_LEN, yy, W_CTRL, C_BOX)
        # L 极闸刀朝上, N 极闸刀朝下
        s.line(SW_X + 8, yy, SW_X + 40, yy - 17 if bx == L1X else yy + 17, W_CTRL, C_BOX)
    s.line(SW_X + 24, y - 20, SW_X + 24, y + 56, 1.0, C_MUT, dash="4,3")
    # 名称放在开关上方偏右, 避开右侧装置框(中列左缘 x=340)
    s.text(182, y - 34, name, 12, "start", "bold")
    s.text(182, y - 20, aux, 10, "start", "normal", C_MUT)
    return (SW_X + SW_LEN, y), (SW_X + SW_LEN, y + 36)


z2 = sw2(250, "ZKK2 带电显示电源开关", "辅触 ZKK2-2 / ZKK2-4")
z3 = sw2(470, "ZKK3 电磁锁开关", "辅触 ZKK3-2 / ZKK3-4")
z1 = sw2(630, "ZKK1 温湿度/装置电源开关", "辅触 ZKK1-2 / ZKK1-4")

# ================================================================ BDXN3
bx, by, bw, bh = BD
kx = box_meta(BD, "博峰 BDXN3 感应式高压带电显示装置",
              "工作电源 85~265VAC / 100~360VDC  ·  闭锁接点 5A/250VAC/30VDC", "#f5f7fa")
s.term(420, by, "L+", "top", 12)
s.term(480, by, "N", "top", 12)
s.term(540, by, "-", "top", 12)
s.poly([(z2[0][0], z2[0][1]), (420, z2[0][1]), (420, by)], W_POWER, C_POWER)
s.poly([(z2[1][0], z2[1][1]), (540, z2[1][1]), (540, by)], W_POWER, C_N)
s.line(480, z2[1][1], 540, z2[1][1], W_POWER, C_N)
s.poly([(480, z2[1][1]), (480, by)], W_POWER, C_N)
s.dot(480, z2[1][1], 3.2, C_N)
for lb, dy in [("K1", 118), ("K2", 148), ("K3", 178), ("K4", 208), ("K5", 238), ("K6", 268)]:
    s.term(kx, by + dy, lb, "right", 12)
s.text(kx + 10, by + 96, "电磁锁1 (K1·K2)", 11, "start", "normal", C_MUT)
s.text(kx + 10, by + 158, "电磁锁2 (K3·K4) 备用", 11, "start", "normal", C_MUT)
s.text(kx + 10, by + 220, "微机五防 (K5·K6)", 11, "start", "normal", C_MUT)
for lb, dx in [("A", 490), ("B", 570), ("C", 650), ("接地", 400)]:
    s.term(bx + dx, by + bh, lb, "bottom", 12)
# BDXN3 自身传感器: 屏蔽线直接上母排, 不进端子排, 只画引下线与说明
for dx in (490, 570, 650):
    s.line(bx + dx, by + bh, bx + dx, by + bh + 26, W_SIG, C_SIG, dash="7,4")
s.text(bx + 660, by + bh + 20, "A/B/C 传感器屏蔽线（黄/绿/红 5m）→ 装于母排，见注 3/4",
       11, "start", "normal", C_SIG)
s.text(bx + 400, by + bh + 34, "引至最近接地点", 11, "middle", "normal", C_MUT)

# ================================================================ 电磁锁
lx, ly, lw, lh = LK
box_meta(LK, "电磁锁 A/B/C 相（每相 2 把，失电闭锁型）",
         "BDXN3 带电时 K1·K2 断开 → 电磁锁失电闭锁；停电时闭合 → 得电可操作", "#fdf6f6")
s.line(1330, FIRE_Y, 1480, FIRE_Y, W_CTRL, C_CTRL)
s.line(1560, NEUT_Y, 1810, NEUT_Y, W_POWER, C_N)
s.text(1330, FIRE_Y - 8, "火线 XT-17", 11, "start", "normal", C_CTRL)
s.text(1560, NEUT_Y - 8, "零线 XT-20", 11, "start", "normal", C_N)
for i, ph in enumerate(["A 相", "B 相", "C 相"]):
    ry = 310 + i * 40
    s.text(1340, ry - 6, ph, 12, "start", "bold")
    for j in range(2):
        ox = 1390 + j * 180
        s.rect(ox, ry, 150, 26, fill="#fff", stroke=C_BOX, sw=1.0)
        s.text(ox + 75, ry + 17, "电磁锁 %d" % (j + 1), 12, "middle")
        s.term(ox, ry + 13, "L", "left", 10)
        s.term(ox + 150, ry + 13, "N", "right", 10)
    s.line(1390, ry + 13, 1390, FIRE_Y, W_CTRL, C_CTRL)      # 锁1 L 上火线
    s.line(1540, ry + 13, 1570, ry + 13, W_CTRL, C_CTRL)     # 锁1N-锁2L 跳线(并联)
    s.line(1740, ry + 13, 1740, NEUT_Y, W_POWER, C_N)        # 锁2 N 上零线

# BDXN3 K1(出) → 火线母线 ; K2(入) ← ZKK3-2 ; K5·K6 → 微机五防
s.poly([(kx, by + 118), (1085, by + 118), (1085, FIRE_Y), (1330, FIRE_Y)], W_CTRL, C_CTRL)
s.text(1090, by + 112, "K1 → XT-17", 11, "start", "normal", C_MUT)
s.poly([(z3[0][0], z3[0][1]), (1040, z3[0][1]), (1040, by + 148), (kx, by + 148)], W_CTRL, C_CTRL)
s.text(660, z3[0][1] - 8, "ZKK3-2 → XT-11 → K2", 11, "start", "normal", C_MUT)
s.poly([(kx, by + 238), (1120, by + 238), (1120, by + 262)], W_SIG, C_SIG, dash="7,4")
s.text(1050, by + 254, "→ 微机五防", 11, "start", "normal", C_SIG)
# ZKK3-4 → 零线母线(走底部走廊 + 右列外侧走廊)
s.poly([(z3[1][0], z3[1][1]), (1040, z3[1][1]), (1040, ZERO_Y), (RCORR, ZERO_Y),
        (RCORR, NEUT_Y), (1810, NEUT_Y)], W_POWER, C_N)
s.text(660, ZERO_Y - 8, "ZKK3-4 → XT-20 零线", 11, "start", "normal", C_N)

# ================================================================ 触摸屏
tx, ty, tw, th = TS
box_meta(TS, "YTT-1500 显示控制单元（PA0715-N / RK3562 / Android 13）",
         "运行 RS485Control 程序  ·  1024×600 触摸屏  ·  开放 root", "#eef4fb")
s.term(tx + 90, ty + th, "L", "bottom", 12)
s.term(tx + 170, ty + th, "N", "bottom", 12)
s.poly([(z1[0][0], z1[0][1]), (tx + 90, z1[0][1]), (tx + 90, ty + th)], W_POWER, C_POWER)
s.poly([(z1[1][0], z1[1][1]), (tx + 170, z1[1][1]), (tx + 170, ty + th)], W_POWER, C_N)
s.term(tx + 540, ty + th, "RS485-A", "bottom", 12, C_SIG)
s.term(tx + 650, ty + th, "RS485-B", "bottom", 12, C_SIG)
s.text(tx + 540, ty + th + 32, "ttyS4 → 域控主板", 11, "middle", "normal", C_SIG)
s.text(tx + 650, ty + th + 32, "ttyS2 → 备用/第二块主板", 11, "middle", "normal", C_SIG)

# ================================================================ 域控主板
mx, my, mw, mh = MB
box_meta(MB, "域控主板 V-1.1（Modbus 从站）",
         "Modbus ID 1~247  ·  OT1~OT10 位掩码 0x0031  ·  外扩 IN 0x000C / OUT 0x0033", "#eef4fb")
s.poly([(tx + 540, ty + th), (tx + 540, my)], W_SIG, C_SIG)
s.text(tx + 548, ty + th + 48, "RS485-A（A/B）", 11, "start", "normal", C_SIG)
s.term(mx + 540, my, "RS485-A", "top", 11, C_SIG)
s.term(mx + 150, my, "温湿度 B2-/GND/A2+/V0+", "top", 11, C_SIG)
s.term(mx + 470, my, "PT100 B3-/GND/A3+/V0+", "top", 11, C_SIG)
for lb, dx in [("IN1", 60), ("IN2", 100), ("IN3", 140), ("IN4", 180), ("IN5", 220),
               ("OUT1", 290), ("OUT2", 330), ("OUT3", 370), ("OUT4", 410),
               ("OUT5", 450), ("OUT6", 490), ("OUT7", 530),
               ("OT1", 600), ("OT2", 630), ("OT3", 660), ("OT4", 690), ("OT5", 720),
               ("OT6", 750), ("OT7", 780), ("OT8", 810), ("OT9", 840), ("OT10", 870)]:
    s.term(mx + dx, my + mh, lb, "bottom", 10)
s.text(mx + 60, my + mh - 12, "外扩输入 0x000C", 11, "start", "normal", C_MUT)
s.text(mx + 290, my + mh - 12, "外扩输出 0x0033", 11, "start", "normal", C_MUT)
s.text(mx + 600, my + mh - 12, "OT 继电器 0x0031", 11, "start", "normal", C_MUT)

# ================================================================ 传感器
sx, sy, sw_, sh = SN
box_meta(SN, "温湿度传感器 ×3 + PT100 ×2",
         "三只温湿度共用第二组 RS485；PT100 模块接第三组 RS485 与电源四线", "#f4f8f4")
s.term(sx + 30, sy + sh, "温湿度接口", "bottom", 11, C_SIG)
s.term(sx + 330, sy + sh, "PT100 接口", "bottom", 11, C_SIG)
# 两路回线分别走 y=630 / y=645, 在 x=880(RS485-A 竖线)处断开做跨接;
# PT100 那一路还要跨 x=1040(零线竖线), 同样做跨接, 避免被误读成接点
s.poly([(sx + 30, sy + sh), (sx + 30, 615), (1255, 615), (1255, 630), (892, 630)],
       W_SIG, C_SIG, dash="7,4")
s.poly([(868, 630), (mx + 150, 630), (mx + 150, my)], W_SIG, C_SIG, dash="7,4")
s.poly([(sx + 330, sy + sh), (sx + 330, 645), (1052, 645)], W_SIG, C_SIG, dash="7,4")
s.poly([(1028, 645), (892, 645)], W_SIG, C_SIG, dash="7,4")
s.poly([(868, 645), (mx + 470, 645), (mx + 470, my)], W_SIG, C_SIG, dash="7,4")
s.text(sx + 40, 610, "第二组 RS485", 10, "start", "normal", C_SIG)
s.text(sx + 340, 640, "第三组 RS485 + 电源四线", 10, "start", "normal", C_SIG)

# ================================================================ 加热器
hx, hy, hw, hh = HT
box_meta(HT, "加热器 A / B / C（各一对 OT 驱动，三档）",
         "低位=1 档、高位=2 档、同开=3 档；默认 A=OT1+OT2 / B=OT3+OT4 / C=OT5+OT6", "#fff8f0")
for i, (nm, pair) in enumerate([("加热器 A", "OT1+OT2"), ("加热器 B", "OT3+OT4"),
                                ("加热器 C", "OT5+OT6")]):
    y = hy + 82 + i * 20
    s.text(hx + 16, y, nm, 12, "start", "bold")
    s.text(hx + 120, y, pair, 12, "start", "normal", C_SIG)
    s.rect(hx + 250, y - 13, 140, 20, fill="#fff", stroke=C_BOX, sw=1.0)
    s.text(hx + 320, y + 2, "加热器", 11, "middle")
s.term(hx + 60, hy + hh, "加热回路", "bottom", 11, C_CTRL)
s.poly([(hx + 60, hy + hh), (hx + 60, hy + hh + 10), (CORR, hy + hh + 10),
        (CORR, 924), (mx + 660, 924), (mx + 660, my + mh)], W_CTRL, C_CTRL)
s.text(CORR + 8, 918, "OT 输出对（经保护）", 11, "start", "normal", C_MUT)

# ================================================================ 指示与报警
ax_, ay, aw, ah = AL
box_meta(AL, "指示与报警", "", "#faf7fb")
for i, (t, n) in enumerate([("OUT1", "加热器A工作灯"), ("OUT2", "加热器B工作灯"),
                            ("OUT3", "加热器C工作灯"), ("OUT5", "操作提示蜂鸣器"),
                            ("OT9", "红色报警灯"), ("OT10", "高压报警蜂鸣器")]):
    x = ax_ + 16 + (i % 3) * 178
    y = ay + 52 + (i // 3) * 26
    s.text(x, y, t, 12, "start", "bold", C_SIG)
    s.text(x + 46, y, n, 11, "start", "normal", C_MUT)
s.term(ax_ + 90, ay + ah, "OUT/OT", "bottom", 11, C_SIG)
s.poly([(ax_ + 90, ay + ah), (ax_ + 90, 944), (mx + 870, 944), (mx + 870, my + mh)],
       W_SIG, C_SIG)


# ================================================================ 端子排表
def table(x, y, title, cols, rows, note=None, row_h=21, hdr_h=26):
    tw = sum(c[1] for c in cols)
    bottom = y + 28 + hdr_h + row_h * len(rows)
    s.rect(x, y, tw, 28, fill="#eceff1", stroke=C_BOX, sw=1.2)
    s.text(x + 10, y + 19, title, 14, "start", "bold")
    y2 = y + 28
    s.rect(x, y2, tw, hdr_h, fill="#f7f9fa", stroke=C_BOX, sw=1.2)
    cx = x
    for name, cw in cols:
        s.line(cx, y, cx, bottom, W_TBL, C_BOX)
        cx += cw
    s.line(x + tw, y, x + tw, bottom, W_TBL, C_BOX)
    cx = x
    for name, cw in cols:
        s.text(cx + cw / 2, y2 + hdr_h - 8, name, 12, "middle", "bold")
        cx += cw
    s.line(x, y2, x + tw, y2, 1.2, C_BOX)
    s.line(x, y2 + hdr_h, x + tw, y2 + hdr_h, 1.2, C_BOX)
    for r, row in enumerate(rows):
        ry = y2 + hdr_h + r * row_h
        if r % 2 == 1:
            s.rect(x, ry, tw, row_h, fill="#fafafa", stroke="none", sw=0)
        cx = x
        for (name, cw), val in zip(cols, row):
            al = "middle" if cw < 90 else "start"
            ox = cx + cw / 2 if al == "middle" else cx + 8
            s.text(ox, ry + 15, val, 11, al)
            cx += cw
        s.line(x, ry + row_h, x + tw, ry + row_h, 0.6, "#cfd8dc")
    if note:
        s.text(x, bottom + 18, note, 11, "start", "normal", C_MUT)
        bottom += 26
    return bottom


xt_rows = [
    ("1", "加热器A 出线", "域控主板 OT1", "加热器A"),
    ("2", "加热器A 回线", "N", "加热器A"),
    ("3", "加热器B 出线", "域控主板 OT3", "加热器B"),
    ("4", "加热器B 回线", "N", "加热器B"),
    ("5", "传感器A +", "温湿度接口 A2+", "温湿度探头A"),
    ("6", "传感器A −", "温湿度接口 B2−", "温湿度探头A"),
    ("7", "传感器B +", "温湿度接口 A2+", "温湿度探头B"),
    ("8", "传感器B −", "温湿度接口 B2−", "温湿度探头B（引至B柜）"),
    ("9", "带电显示 N", "ZKK2-4", "BDXN3 N"),
    ("10", "带电显示 L+", "ZKK2-2", "BDXN3 L+"),
    ("11", "电磁锁控制", "ZKK3-2", "BDXN3 K2"),
    ("12", "电磁锁控制", "XT-17", "BDXN3 K1"),
    ("13", "装置电源 N", "ZKK1-4", "YTT-1500 N"),
    ("14", "装置电源 L", "ZKK1-2", "YTT-1500 L"),
    ("15", "五防/测控", "BDXN3 K6", "微机五防"),
    ("16", "五防/测控", "BDXN3 K5", "微机五防"),
    ("17", "电磁锁火线", "XT-12", "A相电磁锁1、2:L"),
    ("18", "电磁锁火线", "XT-12", "B相电磁锁1、2:L"),
    ("19", "电磁锁火线", "XT-12", "C相电磁锁1、2:L"),
    ("20", "电磁锁零线", "ZKK3-4", "A相电磁锁1、2:N"),
    ("21", "电磁锁零线", "ZKK3-4", "B相电磁锁1、2:N"),
    ("22", "电磁锁零线", "ZKK3-4", "C相电磁锁1、2:N"),
]
table(T1[0], T1[1], "端子排 XT（保留原 22 位，用途按改造后重标）",
      [("XT", 70), ("回路名称", 210), ("来源", 260), ("去向", 260), ("备注", 400)],
      [r + ("",) for r in xt_rows],
      note="XT-17~19 为火线分配，XT-20~22 为零线分配；XT-12 与 XT-17 为同一节点（跨接）。")

xt2_rows = [
    ("1", "RS485-A A/B", "YTT-1500 ttyS4", "域控主板"),
    ("2", "RS485-B A/B", "YTT-1500 ttyS2", "备用 / 第二块主板"),
    ("3", "IN1 手自动", "域控主板", "手自动选择开关"),
    ("4", "IN2 加热A", "域控主板", "加热器A实体按键"),
    ("5", "IN3 加热B", "域控主板", "加热器B实体按键"),
    ("6", "IN4 加热C", "域控主板", "加热器C实体按键"),
    ("7", "IN5 备用", "域控主板", "备用 / 高压闭锁（待开发）"),
    ("8", "OUT1 加热A灯", "域控主板", "加热器A工作灯"),
    ("9", "OUT2 加热B灯", "域控主板", "加热器B工作灯"),
    ("10", "OUT3 加热C灯", "域控主板", "加热器C工作灯"),
    ("11", "OUT4 备用", "域控主板", "备用手动扩展输出"),
    ("12", "OUT5 提示音", "域控主板", "操作提示蜂鸣器"),
    ("13", "OUT6/OUT7", "域控主板", "扩展指示（只读）"),
    ("14", "OT9 报警灯", "域控主板", "红色报警灯（只读）"),
    ("15", "OT10 高压蜂鸣", "域控主板", "高压报警蜂鸣器（只读）"),
]
table(T2[0], T2[1], "端子排 XT2（新增：YTT-1500 / 域控主板）",
      [("XT2", 70), ("功能", 200), ("来源", 240), ("去向", 240), ("备注", 300)],
      [r + ("",) for r in xt2_rows],
      note="IN1~IN5 实际地址 0x000C（bit0~bit4）；OUT1~OUT7 写 0x0033；OT1~OT10 位掩码 0x0031。")

# ================================================================ 注释
notes = [
    "注 1　BDXN3 接点极性（摘自说明书）：K1·K2 / K3·K4 带电时断开、不带电时闭合、装置无工作电源时断开；K5·K6 相反（带电与失电均闭合）。",
    "注 2　电磁锁必须选失电闭锁型：BDXN3 带电 → K1·K2 断开 → 锁失电闭锁；停电 → 闭合 → 得电可操作。若现场为得电闭锁型，改接 K5·K6。",
    "注 3　BDXN3 控制器与电磁锁等电磁元件距离 ≥200 mm；传感器与柜内互感器距离 >250 mm；传感器与母排空气距离 10 kV 取 125~145 mm。",
    "注 4　传感器屏蔽线不得从中间断开或经中间端子对接，应连续引至控制器；控制器接地端子引至最近接地点直接接地。",
    "注 5　BDXN3 的 RS485（ModBus-RTU，定制）协议未随说明书提供，需向福州博峰索取；YTT-1500 程序中亦无 BDXN3 驱动，故本图按硬接线（无源接点）设计，不依赖通信。",
    "注 6　原“测控带电监测”（XT-15/16，接旧装置 K1/K2）改接 BDXN3 K5·K6 送微机五防；旧装置 K3/K4 的电磁锁控制功能由 BDXN3 K1·K2（电磁锁1）承担，K3·K4（电磁锁2）留作备用。",
    "注 7　YTT-1500 的“高压闭锁”外扩输入映射（hv_lockout）当前仅在界面显示，未参与控制逻辑；如需以 BDXN3 接点参与高压联锁，须先开发，见改造方案文档。",
]
for i, n in enumerate(notes):
    s.text(40, NOTE_Y + i * 22, n, 13, "start", "normal", C_TXT if i < 2 else C_MUT)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "左岸励磁变YTT1500外围接线图.svg")
with open(out, "w", encoding="utf-8") as f:
    f.write(s.render())
print("已生成:", out, os.path.getsize(out), "字节")
