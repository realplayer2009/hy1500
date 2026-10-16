#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《变压器加热系统 使用手册》插图（面向鸿蒙/石墨灰主题的程序界面重绘）。

输出到 docs/manual/images/。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
os.makedirs(OUT, exist_ok=True)

# ---- 调色板（对齐程序 石墨灰 主题） ----
BG = (24, 24, 26)
CARD = (31, 31, 33)
CARD2 = (38, 38, 40)
GRID = (58, 58, 60)
TEXT = (242, 242, 247)
SUB = (161, 161, 166)
RUN = (0, 230, 118)
RUN_DK = (0, 184, 95)
BLUE = (100, 181, 246)
AMBER = (255, 145, 0)
RED = (200, 54, 50)
HARMONY_B = (0, 125, 255)
W, H = 1024, 600


def font(size, bold=False):
    cands = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def txt(d, xy, s, f, fill=TEXT, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def arrow(d, x1, y1, x2, y2, fill=SUB, w=2, head=8):
    d.line((x1, y1, x2, y2), fill=fill, width=w)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        d.line((x2, y2, x2 - head * math.cos(ang + da), y2 - head * math.sin(ang + da)),
               fill=fill, width=w)


def dashed(d, p, color, width=2, period=5):
    for k in range(len(p) - 1):
        if k % period < period - 1:
            d.line((p[k][0], p[k][1], p[k + 1][0], p[k + 1][1]), fill=color, width=width)


# ============================================================
def fig_main_layout():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_t = font(15, True)
    f_n = font(13)
    f_s = font(11)

    NAV_W = 182
    rrect(d, (0, 0, NAV_W, H), 0, fill=(20, 20, 22))
    d.line((NAV_W, 0, NAV_W, H), fill=GRID, width=1)
    rrect(d, (14, 22, NAV_W - 14, 52), 6, fill=None, outline=GRID)
    txt(d, (28, 37), "裕泰通加热器", f_t, fill=TEXT)
    navs = ["域控子板总览", "子板手自控制", "加热参数设置", "数据浏览", "高级设置", "关于本机"]
    y = 88
    for i, n in enumerate(navs):
        if i == 0:
            rrect(d, (8, y - 6, NAV_W - 8, y + 44), 6, fill=HARMONY_B)
        rrect(d, (8, y - 6, NAV_W - 8, y + 44), 6, outline=GRID)
        txt(d, (26, y + 16), n, f_n, fill=TEXT if i == 0 else SUB)
        y += 58

    rrect(d, (NAV_W, 0, W, 64), 0, fill=CARD)
    d.line((NAV_W, 64, W, 64), fill=GRID, width=1)
    txt(d, (NAV_W + 20, 32), "域控子板总览", f_t, fill=TEXT)
    rrect(d, (W - 330, 18, W - 186, 46), 14, fill=(18, 51, 36), outline=RUN_DK)
    txt(d, (W - 316, 32), "✓ 自检正常", f_s, fill=RUN)
    rrect(d, (W - 174, 18, W - 20, 46), 14, fill=CARD2, outline=GRID)
    txt(d, (W - 164, 32), "2026-10-09  14:30:00", f_s, fill=SUB)

    cx = NAV_W + 14
    rrect(d, (cx, 80, W - 14, 122), 8, fill=CARD, outline=GRID)
    txt(d, (cx + 16, 101), "点击任意子板卡片进入详细控制", f_s, fill=SUB)
    txt(d, (W - 270, 101), "共 4 块 · 在线 4 · 离线 0 · 告警 0", f_s, fill=TEXT)

    cards = [
        ("串口 1 · ID 1", "自动温控", True, "30.1", "52.3", "29.8"),
        ("串口 1 · ID 2", "自动温控", True, "31.2", "48.0", "30.4"),
        ("串口 2 · ID 3", "手动", False, "28.6", "55.1", "28.2"),
        ("串口 2 · ID 4", "自动温控", True, "32.0", "44.7", "31.1"),
    ]
    cw, ch = (W - NAV_W - 40) // 2, 186
    for i, (idn, mode, auto, t, hu, pt) in enumerate(cards):
        x = cx + (i % 2) * (cw + 12)
        yy = 134 + (i // 2) * (ch + 12)
        rrect(d, (x, yy, x + cw, yy + ch), 10, fill=CARD, outline=GRID)
        txt(d, (x + 16, yy + 20), idn, f_n, fill=TEXT)
        col = RUN if auto else BLUE
        txt(d, (x + cw - 116, yy + 20), "● " + mode, f_n, fill=col)
        cols = [("平均温度 · ℃", t), ("平均湿度 · %RH", hu), ("PT100均温 · ℃", pt)]
        for k, (lb, vl) in enumerate(cols):
            bx = x + 16 + k * ((cw - 32) // 3)
            txt(d, (bx, yy + 50), lb, f_s, fill=SUB)
            txt(d, (bx, yy + 68), vl, f_t, fill=TEXT)
        txt(d, (x + 16, yy + 100), "加热器A  2档", f_s, fill=AMBER)
        txt(d, (x + 16, yy + 118), "加热器B  关闭", f_s, fill=SUB)
        txt(d, (x + 16, yy + 136), "加热器C  1档", f_s, fill=AMBER)
        for k, st in enumerate(["● 开", "○ 关", "○ 关", "○ 关"]):
            txt(d, (x + cw // 2 + 8 + (k % 2) * 130, yy + 100 + (k // 2) * 20), st, f_s,
                fill=RUN if k == 0 else SUB)
        txt(d, (x + cw // 2 + 8, yy + 142), "● 在线 · 外压 0.0 V · 备用输入 低电平", f_s, fill=RUN)

    rrect(d, (NAV_W, H - 30, W, H), 0, fill=(26, 26, 28))
    d.line((NAV_W, H - 30, W, H - 30), fill=GRID, width=1)
    txt(d, (NAV_W + 20, H - 15), "通信已启动，正在自动搜索子板……已发现 4 块，自动温控 3/4 块运行中", f_s, fill=SUB)
    d.rectangle((0, 0, W - 1, H - 1), outline=HARMONY_B, width=2)
    return im


# ============================================================
def fig_wiring():
    im = Image.new("RGB", (1080, 560), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(14, True)
    f_s = font(12)

    txt(d, (24, 18), "系统接线示意图", f_h, fill=(20, 20, 24))

    def box(x, y, w, h, title, lines, fill=(255, 255, 255), edge=HARMONY_B, tcol=(20, 30, 50)):
        rrect(d, (x, y, x + w, y + h), 10, fill=fill, outline=edge, width=2)
        txt(d, (x + 12, y + 12), title, f_t, fill=tcol)
        for i, l in enumerate(lines):
            txt(d, (x + 12, y + 40 + i * 22), l, f_s, fill=(40, 40, 46))

    box(330, 54, 420, 96, "变压器箱内（干式变压器）",
        ["三路温湿度探头 A/B/C（菊花链）", "PT100 铂热电阻 1/2（内部温度）"], fill=(240, 246, 255))
    box(60, 190, 250, 82, "高压带电传感器",
        ["低电平/数字量信号有效", "接入主控板 0x0001 或 0x0003"], fill=(255, 244, 244), edge=RED)
    box(760, 68, 290, 330, "裕泰通 触屏一体机 PA0715-N",
        ["RK3562 / 1024×600 · 鸿蒙界面外观", "程序：变压器加热系统", "",
         "串口配置：",
         "  Port0 = /dev/ttyS4（主线）", "  Port1 = /dev/ttyS2（子板）", "",
         "CSV 数据落盘：", "  data/logs/YYYY-MM-DD.csv"])
    box(360, 200, 330, 150, "RS485 主控板（Modbus RTU 19200/N/8/1）",
        ["Modbus 从站地址范围 1~247", "输出：OT1~OT10 位掩码 / OUT1~OUT7",
         "读取：温湿度 · PT100 · 外压 · IN/OUT"], fill=(245, 250, 255), edge=(60, 100, 160))
    box(360, 400, 330, 120, "子板 ×N（每口最多 16 块）",
        ["从站地址范围 1~247（按现场设置）", "两路 PT100 + 三路温湿度采集",
         "加热器 A/B/C 各由一对 OT 驱动"], fill=(250, 250, 252), edge=(120, 120, 128))
    box(760, 428, 290, 92, "三色灯 + 蜂鸣器",
        ["OT7 绿灯 / OT8 黄灯 / OT9 红灯", "OT10 蜂鸣器（现场接线，高压报警）",
         "OUT5 操作确认音（选配，未接）"],
        fill=(255, 250, 240), edge=(200, 160, 60))

    arrow(d, 620, 150, 620, 196, fill=(90, 130, 190), w=3)
    txt(d, (628, 164), "RS485-A", f_s, fill=(90, 130, 190))
    arrow(d, 525, 350, 525, 396, fill=(90, 130, 190), w=3)
    txt(d, (533, 364), "RS485-B", f_s, fill=(90, 130, 190))
    arrow(d, 190, 272, 356, 272, fill=(200, 90, 90), w=3)
    txt(d, (196, 250), "带电信号", f_s, fill=(200, 90, 90))
    arrow(d, 690, 300, 756, 240, fill=(90, 130, 190), w=3)
    txt(d, (700, 252), "Modbus", f_s, fill=(90, 130, 190))
    arrow(d, 690, 460, 756, 460, fill=(200, 160, 60), w=3)
    txt(d, (700, 436), "OT7~OT10 / OUT5", f_s, fill=(200, 160, 60))
    return im


# ============================================================
def fig_boot_flow():
    im = Image.new("RGB", (1080, 430), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(12)
    txt(d, (24, 18), "上电启动到正常监控的流程", f_h, fill=(20, 20, 24))

    steps = [
        ("开机自启", "启动链路拉起\n变压器加热系统", (235, 240, 255), (80, 120, 190)),
        ("加载配置", "读 app.ini\n串口/参数/数据路径", (240, 248, 240), (90, 150, 100)),
        ("自动发现子板", "每口扫描至发现\n第一块即停（≤16 块/口）", (255, 250, 235), (200, 160, 60)),
        ("顶部自检倒计时", "最多 60 秒\n等待各子板温湿度数据", (245, 245, 250), (120, 120, 130)),
        ("✓ 自检正常", "进入正常监控\n自动 / 手动可操作", (235, 255, 240), RUN_DK),
    ]
    bw, bh, gap = 180, 120, 26
    x0, y0 = 40, 70
    for i, (title, body, fill, edge) in enumerate(steps):
        x = x0 + i * (bw + gap)
        rrect(d, (x, y0, x + bw, y0 + bh), 10, fill=fill, outline=edge, width=2)
        txt(d, (x + bw // 2, y0 + 20), title, f_t, fill=(20, 20, 26), anchor="ma")
        for k, ln in enumerate(body.split("\n")):
            txt(d, (x + bw // 2, y0 + 48 + k * 18), ln, f_s, fill=(50, 50, 56), anchor="ma")
        if i < len(steps) - 1:
            arrow(d, x + bw + 4, y0 + bh // 2, x + bw + gap - 4, y0 + bh // 2,
                  fill=(120, 120, 130), w=2)

    yb = y0 + bh + 46
    bx = x0 + 3 * (bw + gap)
    rrect(d, (bx, yb, bx + bw - 10, yb + 74), 10, fill=(255, 244, 244), outline=RED, width=2)
    txt(d, (bx + (bw - 10) // 2, yb + 16), "⚠ 异常分支", f_t, fill=RED, anchor="ma")
    txt(d, (bx + (bw - 10) // 2, yb + 38), "自检告警 / 通信异常 / 系统时间异常", f_s,
        fill=(120, 40, 40), anchor="ma")
    txt(d, (bx + (bw - 10) // 2, yb + 56), "按顶部提示处置，不阻塞手动操作", f_s,
        fill=(120, 40, 40), anchor="ma")
    arrow(d, bx + bw // 2, y0 + bh + 4, bx + bw // 2, yb - 4, fill=RED, w=2)

    rrect(d, (40, yb + 90, 1040, yb + 126), 8, fill=(240, 240, 245), outline=(180, 180, 190))
    txt(d, (56, yb + 104),
        "注：未接板的口持续等待，接板即被发现；“重新扫描子板”执行一轮完整扫描后自动停止。",
        f_s, fill=(70, 70, 76))
    d.rectangle((0, 0, 1079, 429), outline=(200, 200, 210), width=1)
    return im


# ============================================================
def fig_nav_map():
    im = Image.new("RGB", (1080, 470), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(14, True)
    f_s = font(12)
    txt(d, (24, 18), "左侧导航：六个页面与用途", f_h, fill=(20, 20, 24))

    rrect(d, (36, 60, 250, 410), 10, fill=(32, 34, 38))
    txt(d, (56, 78), "裕泰通加热器", f_t, fill=TEXT)
    items = ["域控子板总览", "子板手自控制", "加热参数设置", "数据浏览", "高级设置", "关于本机"]
    y = 118
    for i, n in enumerate(items):
        rrect(d, (48, y, 240, y + 42), 6,
              fill=HARMONY_B if i == 0 else (44, 46, 50), outline=(60, 62, 66))
        txt(d, (66, y + 21), n, f_s, fill=TEXT if i == 0 else (200, 200, 205))
        y += 50

    panels = [
        ("① 域控子板总览", "所有子板状态卡片\n模式 / 档位 / 灯 / 告警"),
        ("② 子板手自控制", "选中子板的测量、加热器\n与回路操作、启停自动"),
        ("③ 加热参数设置", "温控模式与目标温度\n展开计算说明"),
        ("④ 数据浏览", "历史曲线与明细表格\n日期 / 子板筛选"),
        ("⑤ 高级设置", "接口配置 / 安全保护\n数据存储 / 显示与声音"),
        ("⑥ 关于本机", "程序版本、运行时长\n系统时间与存储信息"),
    ]
    bw, bh = 250, 96
    for i, (t, body) in enumerate(panels):
        x = 290 + (i % 3) * (bw + 14)
        yy = 64 + (i // 3) * (bh + 26)
        rrect(d, (x, yy, x + bw, yy + bh), 10, fill=(255, 255, 255), outline=(80, 120, 190), width=2)
        txt(d, (x + 14, yy + 14), t, f_t, fill=(20, 30, 50))
        for k, ln in enumerate(body.split("\n")):
            txt(d, (x + 14, yy + 40 + k * 18), ln, f_s, fill=(60, 60, 66))
        txt(d, (x + bw - 32, yy + 12), str(i + 1), font(22, True), fill=(220, 228, 240))

    rrect(d, (290, 300, 1044, 350), 8, fill=(250, 250, 252), outline=(200, 200, 210))
    txt(d, (304, 316), "顶部：页面标题 ｜ 自检 pill ｜ 系统状态 pill ｜ 版本号 + 实时时钟（每秒刷新）",
        f_s, fill=(70, 70, 76))
    rrect(d, (290, 360, 1044, 400), 8, fill=(250, 250, 252), outline=(200, 200, 210))
    txt(d, (304, 376), "底部：初始化进度 / 通信状态 / 操作结果提示，随状态即时刷新",
        f_s, fill=(70, 70, 76))
    return im


# ============================================================
def fig_card_anatomy():
    im = Image.new("RGB", (1080, 470), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(14, True)
    f_s = font(12)
    txt(d, (24, 18), "总览卡片信息分区（四块子板两列排布，单板铺满宽度）", f_h, fill=(20, 20, 24))

    x, yy, cw, ch = 36, 60, 1010, 200
    rrect(d, (x, yy, x + cw, yy + ch), 10, fill=CARD, outline=GRID)
    txt(d, (x + 18, yy + 20), "串口 1 · ID 1", f_t, fill=TEXT)
    txt(d, (x + cw - 150, yy + 20), "● 自动温控", f_t, fill=RUN)
    for k, (lb, vl) in enumerate([("平均温度 · ℃", "30.1"), ("平均湿度 · %RH", "52.3"),
                                  ("PT100均温 · ℃", "29.8")]):
        bx = x + 18 + k * 330
        txt(d, (bx, yy + 52), lb, f_s, fill=SUB)
        txt(d, (bx, yy + 70), vl, f_t, fill=TEXT)
    txt(d, (x + 18, yy + 104), "加热器A  2档", f_s, fill=AMBER)
    txt(d, (x + 158, yy + 104), "加热器B  关闭", f_s, fill=SUB)
    txt(d, (x + 298, yy + 104), "加热器C  1档", f_s, fill=AMBER)
    for k, (lb, st, c) in enumerate([("自动运行绿灯", "● 开", RUN), ("手动模式黄灯", "○ 关", SUB),
                                     ("故障报警红灯", "○ 关", SUB), ("高压报警蜂鸣器", "○ 关", SUB)]):
        bx = x + 18 + (k % 2) * 240
        by = yy + 132 + (k // 2) * 22
        txt(d, (bx, by), lb, f_s, fill=SUB)
        txt(d, (bx + 130, by), st, f_s, fill=c)
    txt(d, (x + 520, yy + 132), "● 在线", f_s, fill=RUN)
    txt(d, (x + 520, yy + 154), "外部电压 0.0 V · 备用输入 低电平", f_s, fill=TEXT)

    j = yy + ch + 24
    for s in [
        "① 串口号 + Modbus ID + 在线状态（离线保留缓存读数，但不充当实时值）",
        "② 三栏测量：外部三路平均温度、平均湿度、两路 PT100 平均温度",
        "③ 三组加热器档位：关闭 / 1档 / 2档 / 3档（按 OT 输出对回读解码）",
        "④ 指示灯与蜂鸣器为只读展示：绿=自动运行、黄=手动模式、红=故障/高压",
        "⑤ 安全状态：高压告警、备用输入联锁、传感器异常时整卡以警示色呈现",
    ]:
        txt(d, (40, j), s, f_s, fill=(50, 50, 56))
        j += 22
    return im


# ============================================================
def fig_manual_layout():
    im = Image.new("RGB", (1080, 470), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "子板手自控制：左测量、右操作（约 7:3）", f_h, fill=(20, 20, 24))

    lx, ly, lw, lh = 36, 56, 700, 380
    rrect(d, (lx, ly, lx + lw, ly + lh), 10, fill=CARD, outline=GRID)
    rrect(d, (lx + 12, ly + 12, lx + lw - 12, ly + 54), 8, fill=CARD2, outline=GRID)
    txt(d, (lx + 24, ly + 22), "子板（4 块）", f_s, fill=SUB)
    txt(d, (lx + 130, ly + 22), "P1-ID1 · P1-ID2 · P2-ID3 · P2-ID4", f_s, fill=TEXT)
    rrect(d, (lx + lw - 140, ly + 18, lx + lw - 24, ly + 48), 14, fill=(18, 51, 36), outline=RUN_DK)
    txt(d, (lx + lw - 130, ly + 33), "● 在线", f_s, fill=RUN)

    for i, (t, a, b) in enumerate([("温湿度 A", "30.1 ℃", "52.3 %RH"), ("温湿度 B", "29.8 ℃", "50.0 %RH"),
                                   ("温湿度 C", "30.4 ℃", "54.1 %RH")]):
        cx = lx + 12 + i * 224
        rrect(d, (cx, ly + 64, cx + 214, ly + 156), 8, fill=CARD2, outline=GRID)
        txt(d, (cx + 12, ly + 74), t, f_t, fill=TEXT)
        txt(d, (cx + 12, ly + 100), a, f_s, fill=TEXT)
        txt(d, (cx + 12, ly + 122), b, f_s, fill=SUB)

    for i, (t, gear) in enumerate([("加热器状态A", 2), ("加热器状态B", 0), ("加热器状态C", 1)]):
        cx = lx + 12 + i * 224
        rrect(d, (cx, ly + 166, cx + 214, ly + 292), 8, fill=CARD2, outline=GRID)
        txt(d, (cx + 12, ly + 176), t, f_t, fill=TEXT)
        txt(d, (cx + 12, ly + 198), "目标 30.0 ℃", f_s, fill=SUB)
        for jdx in range(3):
            bx = cx + 12 + jdx * 44
            on = jdx < gear
            rrect(d, (bx, ly + 224, bx + 36, ly + 260), 4,
                  fill=AMBER if on else CARD, outline=AMBER if on else GRID, width=2)
            if on:
                txt(d, (bx + 18, ly + 242), "●", font(14, True), fill=(10, 20, 15), anchor="ma")
            else:
                txt(d, (bx + 18, ly + 242), "×", font(16, True), fill=SUB, anchor="ma")
        txt(d, (cx + 152, ly + 232), ["2档", "关闭", "1档"][i], f_s, fill=AMBER if gear else SUB)

    for i, (t, v) in enumerate([("PT100 温度 1", "29.8 ℃"), ("PT100 温度 2", "29.6 ℃"), ("外部电压", "0.0 V")]):
        cx = lx + 12 + i * 224
        rrect(d, (cx, ly + 302, cx + 214, ly + 370), 8, fill=CARD2, outline=GRID)
        txt(d, (cx + 12, ly + 312), t, f_s, fill=SUB)
        txt(d, (cx + 12, ly + 334), v, f_t, fill=TEXT)
    txt(d, (lx + 12, ly + 380), "最后更新：2026-10-09  14:30:00", f_s, fill=SUB)

    rx, ry, rw, rh = 748, 56, 296, 380
    rrect(d, (rx, ry, rx + rw, ry + rh), 10, fill=CARD, outline=GRID)
    txt(d, (rx + 14, ry + 14), "自动温控", f_t, fill=TEXT)
    rrect(d, (rx + 14, ry + 40, rx + 180, ry + 74), 14, fill=(10, 33, 24), outline=RUN)
    txt(d, (rx + 24, ry + 57), "● 自动温控运行中", f_s, fill=RUN)
    txt(d, (rx + 190, ry + 57), "30.1 ℃", f_s, fill=TEXT)
    rrect(d, (rx + 14, ry + 82, rx + 142, ry + 124), 8, fill=RUN)
    txt(d, (rx + 60, ry + 103), "启动自动", f_s, fill=(10, 20, 15), anchor="ma")
    rrect(d, (rx + 152, ry + 82, rx + 282, ry + 124), 8, fill=(60, 60, 64), outline=GRID)
    txt(d, (rx + 200, ry + 103), "停止自动", f_s, fill=SUB, anchor="ma")

    txt(d, (rx + 14, ry + 136), "设备控制", f_t, fill=TEXT)
    rrect(d, (rx + 14, ry + 162, rx + 282, ry + 200), 8, fill=(18, 51, 36), outline=RUN_DK)
    txt(d, (rx + 24, ry + 172), "● 外部电压未超阈值", f_s, fill=RUN)
    txt(d, (rx + 24, ry + 188), "可以操作", f_s, fill=RUN)

    for i, (n, g) in enumerate([("加热器A", "2档"), ("加热器B", "关闭"), ("加热器C", "1档")]):
        bx = rx + 14 + i * 92
        rrect(d, (bx, ry + 210, bx + 84, ry + 262), 8,
              fill=(30, 60, 45) if g != "关闭" else CARD2,
              outline=RUN if g != "关闭" else GRID)
        txt(d, (bx + 42, ry + 226), n, f_s, fill=TEXT, anchor="ma")
        txt(d, (bx + 42, ry + 246), g, f_s, fill=RUN if g != "关闭" else SUB, anchor="ma")

    txt(d, (rx + 14, ry + 272), "加热回路操作", f_s, fill=SUB)
    names = ["加热器A · 第一路", "加热器A · 第二路", "加热器B · 第一路", "加热器B · 第二路"]
    states = [("已打开", RUN), ("已关闭", SUB), ("--", SUB), ("--", SUB)]
    for r in range(2):
        for c in range(2):
            idx = r * 2 + c
            st, col = states[idx]
            bx = rx + 14 + c * 136
            by = ry + 292 + r * 60
            rrect(d, (bx, by, bx + 128, by + 52), 8, fill=CARD2,
                  outline=col if st != "--" else GRID)
            txt(d, (bx + 10, by + 8), names[idx], f_s, fill=TEXT)
            txt(d, (bx + 10, by + 28), st, f_s, fill=col)
    txt(d, (rx + 14, ry + 366), "OUT4 备用扩展输出：可手动切换", f_s, fill=SUB)
    return im


# ============================================================
def fig_gear_map():
    im = Image.new("RGB", (1080, 440), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(14, True)
    f_s = font(12)
    txt(d, (24, 18), "档位 → 继电器 → 功率（以“一级第一路”为例）", f_h, fill=(20, 20, 24))

    rows = [
        ("关闭", [], "0 W（两路均断开）", (140, 140, 146)),
        ("1 档", [0], "低功率：仅第一路闭合", RUN_DK),
        ("2 档", [1], "高功率：仅第二路闭合", (230, 126, 34)),
        ("3 档", [0, 1], "两路同开：最高档", RED),
    ]
    x, yy = 60, 80
    txt(d, (x, yy), "档位状态", f_t, fill=(20, 20, 24))
    txt(d, (x + 170, yy), "继电器对（低位 / 高位）", f_t, fill=(20, 20, 24))
    txt(d, (x + 470, yy), "实际加热效果", f_t, fill=(20, 20, 24))
    txt(d, (x + 790, yy), "对应工作灯", f_t, fill=(20, 20, 24))
    yy += 34
    for name, on, desc, col in rows:
        rrect(d, (x - 12, yy - 8, x + 980, yy + 54), 10, fill=(255, 255, 255), outline=(210, 210, 218))
        txt(d, (x, yy + 12), name, f_t, fill=(20, 20, 26))
        for k in range(2):
            bx = x + 190 + k * 120
            lit = k in on
            rrect(d, (bx, yy + 4, bx + 100, yy + 46), 8,
                  fill=col if lit else (240, 240, 244),
                  outline=col if lit else (200, 200, 208), width=2)
            txt(d, (bx + 50, yy + 14), "低位 = 1档" if k == 0 else "高位 = 2档", f_s,
                fill=(255, 255, 255) if lit else (120, 120, 128), anchor="ma")
            txt(d, (bx + 50, yy + 32), "闭合" if lit else "断开", f_s,
                fill=(255, 255, 255) if lit else (120, 120, 128), anchor="ma")
        txt(d, (x + 470, yy + 18), desc, f_t, fill=(40, 40, 46))
        txt(d, (x + 790, yy + 18), "OUT1~OUT3：" + ("点亮" if on else "熄灭"), f_t,
            fill=RUN_DK if on else (150, 150, 156))
        yy += 66
    rrect(d, (48, yy + 6, 1040, yy + 46), 8, fill=(240, 246, 255), outline=(120, 160, 220))
    txt(d, (64, yy + 18),
        "档位来源统一为 OT 输出对回读解码：手动点击与自动温控驱动的显示完全同源，不会出现“界面显示与实际输出不一致”。",
        f_s, fill=(40, 60, 100))
    return im


# ============================================================
def fig_control_modes():
    im = Image.new("RGB", (1080, 540), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "三种温控模式：同一个“档位输出”，三种切档依据", f_h, fill=(20, 20, 26))

    cols = [
        ("阈值三档", "按温差切档", (235, 245, 255), (80, 120, 190),
         ["目标 − 外部平均温度 < 0.3 ℃", "　→ 全关", "0.3～<1.5 ℃ → 第一路",
          "1.5～<3.0 ℃ → 第二路", "≥3.0 ℃ → 两路同开", "每个边界两侧 ±0.2 ℃ 回差"]),
        ("PID 三档", "按加热需求切档", (235, 250, 240), (80, 150, 110),
         ["Kp=12 · Ki=0.15 · Kd=0", "需求 <10% → 全关", "10%～<35% → 第一路",
          "35%～<60% → 第二路", "≥60% → 两路同开", "积分限幅 + 继电器最短间隔保护"]),
        ("防凝露三档", "按露点余量切档", (255, 248, 235), (200, 160, 60),
         ["露点余量 = PT100均温 − 最不利露点", ">3 ℃ → 全关", "2～3 ℃ → 第一路",
          "1～2 ℃ → 第二路", "≤1 ℃ → 两路同开", "外部温度超 PT100+5 ℃ 停止加热"]),
    ]
    bw = 330
    for i, (title, sub, fill, edge, lines) in enumerate(cols):
        x = 36 + i * (bw + 18)
        rrect(d, (x, 60, x + bw, 360), 12, fill=fill, outline=edge, width=2)
        txt(d, (x + 16, 74), title, font(16, True), fill=(20, 20, 26))
        txt(d, (x + 16, 100), sub, f_s, fill=(70, 70, 76))
        for k, ln in enumerate(lines):
            txt(d, (x + 16, 130 + k * 30), ln, f_t, fill=(40, 40, 46))

    rrect(d, (36, 380, 1044, 510), 10, fill=(245, 245, 250), outline=(200, 200, 210))
    txt(d, (56, 396), "共同点", f_t, fill=(20, 20, 26))
    for k, ln in enumerate([
        "被控量 = 外部三路温湿度探头的有效平均温度；三个加热器各自独立计算，各自驱动各自的 OT 输出对。",
        "目标温度来源可选“跟随内部 PT100 平均值”或“固定温度”；固定温度时 A/B/C 三档可分别设定。",
        "继电器两次状态改变默认最短间隔 10 秒（1~3600 秒可设），高压联锁切断不受此间隔限制。"]):
        txt(d, (56, 424 + k * 26), "· " + ln, f_s, fill=(50, 50, 56))
    return im


# ============================================================
def fig_interlock():
    im = Image.new("RGB", (1080, 470), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "高压安全联锁：触发 → 切断 → 解除后的行为", f_h, fill=(20, 20, 24))

    x, y = 60, 74
    rrect(d, (x, y, x + 260, y + 130), 10, fill=(240, 250, 242), outline=RUN_DK, width=2)
    txt(d, (x + 130, y + 20), "正常运行", f_t, fill=RUN_DK, anchor="ma")
    for k, ln in enumerate(["自动温控或手动操作", "可按目标切档加热"]):
        txt(d, (x + 130, y + 50 + k * 20), ln, f_s, fill=(40, 80, 60), anchor="ma")

    x2 = 420
    rrect(d, (x2, y, x2 + 260, y + 130), 10, fill=(255, 244, 244), outline=RED, width=2)
    txt(d, (x2 + 130, y + 20), "⚠ 高压告警中", f_t, fill=RED, anchor="ma")
    for k, ln in enumerate(["切断全部子板加热回路", "OT9 红灯 + OT10 蜂鸣器",
                            "停止所有自动温控", "拒绝手动开启与重新扫描"]):
        txt(d, (x2 + 130, y + 46 + k * 20), ln, f_s, fill=(120, 40, 40), anchor="ma")

    x3 = 780
    rrect(d, (x3, y, x3 + 250, y + 130), 10, fill=(245, 245, 250), outline=(150, 150, 160), width=2)
    txt(d, (x3 + 125, y + 20), "告警解除", f_t, fill=(60, 60, 66), anchor="ma")
    for k, ln in enumerate(["继电器状态随轮询回读刷新", "需人工确认现场安全",
                            "再由操作员重新启动自动"]):
        txt(d, (x3 + 125, y + 50 + k * 20), ln, f_s, fill=(70, 70, 76), anchor="ma")

    arrow(d, x + 264, y + 65, x2 - 6, y + 65, fill=RED, w=3)
    txt(d, (x + 268, y + 40), "带电信号", f_s, fill=RED)
    arrow(d, x2 + 264, y + 65, x3 - 6, y + 65, fill=(120, 160, 120), w=3)
    txt(d, (x2 + 268, y + 40), "失电", f_s, fill=(90, 140, 90))

    yy = y + 160
    rrect(d, (60, yy, 1030, yy + 120), 10, fill=(255, 255, 255), outline=(210, 210, 218))
    txt(d, (76, yy + 14), "顶部状态栏在告警期间列出每个告警子板的串口与 Modbus ID", f_t, fill=(20, 20, 26))
    rrect(d, (76, yy + 44, 520, yy + 80), 8, fill=(255, 235, 234), outline=RED)
    txt(d, (90, yy + 58), "⚠ 高压：1口-ID 2、2口-ID 3", f_s, fill=RED)
    txt(d, (76, yy + 90),
        "检测类型：模拟信号读 0x0003（原始值÷10 后严格高于阈值触发）；数字信号读 0x0001（等于触发值时触发）。",
        f_s, fill=(60, 60, 66))
    txt(d, (76, yy + 108), "正式投运前必须按现场高压传感器标定阈值——默认值仅供开发调试。", f_s,
        fill=(150, 60, 60))

    yy += 136
    rrect(d, (60, yy, 1030, yy + 96), 10, fill=(255, 252, 240), outline=(200, 170, 80))
    txt(d, (76, yy + 14), "备用输入联锁（0x0002）+ 传感器异常", f_t, fill=(20, 20, 26))
    for k, ln in enumerate([
        "备用输入可设为仅监视 / 高电平联锁 / 低电平联锁；联锁时同样停止该子板自动温控并关闭全部加热回路。",
        "温湿度自检只对固定极端量程（-40～85 ℃ / 0～100 %RH）报警，只提示不阻塞控制，也不拦截手动操作。"]):
        txt(d, (76, yy + 40 + k * 24), "· " + ln, f_s, fill=(60, 60, 66))
    return im


# ============================================================
def fig_data_browser():
    im = Image.new("RGB", (1080, 520), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "数据浏览：筛选 → 曲线 → 明细", f_h, fill=(20, 20, 24))

    rrect(d, (36, 56, 1044, 104), 8, fill=(255, 255, 255), outline=(210, 210, 218))
    txt(d, (52, 76), "日期", f_s, fill=(70, 70, 76))
    rrect(d, (96, 68, 210, 92), 6, fill=(245, 245, 250), outline=(200, 200, 208))
    txt(d, (106, 76), "2026-09-01", f_s, fill=(40, 40, 46))
    txt(d, (216, 76), "—", f_s, fill=(70, 70, 76))
    rrect(d, (236, 68, 350, 92), 6, fill=(245, 245, 250), outline=(200, 200, 208))
    txt(d, (246, 76), "2026-10-09", f_s, fill=(40, 40, 46))
    rrect(d, (366, 68, 560, 92), 6, fill=(245, 245, 250), outline=(200, 200, 208))
    txt(d, (376, 76), "全部子板（按秒聚合）", f_s, fill=(40, 40, 46))
    rrect(d, (576, 68, 660, 92), 8, fill=HARMONY_B)
    txt(d, (600, 76), "查  询", f_s, fill=(255, 255, 255))
    rrect(d, (672, 68, 770, 92), 8, fill=(255, 255, 255), outline=(180, 180, 190))
    txt(d, (692, 76), "仅看表格", f_s, fill=(60, 60, 66))
    txt(d, (790, 76), "共 61 204 条明细 / 61 200 个时间点（曲线已压缩）", f_s, fill=(90, 90, 96))

    rrect(d, (36, 116, 1044, 380), 8, fill=CARD, outline=GRID)
    rrect(d, (48, 124, 1032, 152), 6, fill=CARD2, outline=GRID)
    txt(d, (60, 132), "点击曲线查看数据，左右拖动切换时间段", f_s, fill=SUB)
    d.line((560, 156, 560, 360), fill=TEXT, width=1)
    d.line((56, 250, 1030, 250), fill=TEXT, width=1)
    pts_temp = [(70 + i * 24, 250 - 70 * math.sin(i / 5.5) - 20) for i in range(40)]
    pts_hum = [(70 + i * 24, 300 - 40 * math.cos(i / 6.0)) for i in range(40)]
    pts_pt = [(70 + i * 24, 240 - 60 * math.sin(i / 7.0) - 10) for i in range(40)]
    band = [(x, y - 14) for x, y in pts_temp] + [(x, y + 14) for x, y in reversed(pts_temp)]
    d.polygon(band, fill=(230, 126, 34, 45))
    d.line([(x, y) for x, y in pts_temp], fill=(230, 126, 34), width=2)
    dashed(d, pts_hum, (25, 118, 210))
    for k in range(0, len(pts_pt) - 1):
        if k % 2 == 0:
            d.line((pts_pt[k][0], pts_pt[k][1], pts_pt[k + 1][0], pts_pt[k + 1][1]),
                   fill=(142, 68, 173), width=2)
    txt(d, (50, 368), "— 温湿度计温度", f_s, fill=(197, 95, 10))
    txt(d, (340, 368), "··· 温湿度计湿度", f_s, fill=(25, 118, 210))
    txt(d, (640, 368), "- - PT100 温度", f_s, fill=(142, 68, 173))
    txt(d, (900, 368), "橙色半透明带 = 全部子板最高—最低范围", f_s, fill=SUB)

    rrect(d, (36, 396, 1044, 500), 8, fill=(255, 255, 255), outline=(210, 210, 218))
    heads = ["时间", "子板", "平均温度", "平均湿度", "高压状态"]
    xs = [56, 300, 500, 700, 880]
    for i, hd in enumerate(heads):
        txt(d, (xs[i], 406), hd, f_t, fill=(20, 20, 26))
    d.line((48, 428, 1032, 428), fill=(210, 210, 218))
    rows = [("14:30:00", "P1-ID1", "30.1 ℃", "52.3 %RH", "正常"),
            ("14:30:01", "P1-ID1", "30.2 ℃", "52.1 %RH", "正常"),
            ("14:30:01", "P2-ID3", "28.6 ℃", "55.1 %RH", "正常")]
    for r, row in enumerate(rows):
        for i, v in enumerate(row):
            txt(d, (xs[i], 440 + r * 20), v, f_s, fill=(40, 40, 46))
    return im


# ============================================================
def fig_advanced():
    im = Image.new("RGB", (1080, 520), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "高级设置：四个分组分别管一类配置", f_h, fill=(20, 20, 24))

    groups = [
        ("接口配置", ["外扩输入接入配置：IN1~IN5 各自分配功能",
                     "加热器输出配置：A/B/C 各选一组 OT 继电器对",
                     "备用接口逻辑：OT1/2/5/6 联动 + 备用输入联锁"],
         (235, 245, 255), (80, 120, 190)),
        ("安全保护", ["高压安全联锁：模拟量或数字量两种检测",
                     "继电器切换保护：两次状态改变最短间隔",
                     "默认 10 秒，可设 1~3600 秒"],
         (255, 244, 244), (200, 80, 80)),
        ("数据存储", ["轮询周期与记录周期各自独立可配",
                     "日志容量上限（默认 12 GB）与手动清理",
                     "按天/月/年设定截止日期，先预览再删除"],
         (240, 250, 242), (80, 140, 100)),
        ("显示与声音", ["显示主题：标准/低光/强光/石墨灰/鸿蒙",
                       "屏幕亮度滑条 + 无人值守自动降亮",
                       "操作提示音开关"],
         (255, 250, 240), (200, 160, 60)),
    ]
    bw, bh = 490, 200
    for i, (title, lines, fill, edge) in enumerate(groups):
        x = 36 + (i % 2) * (bw + 26)
        y = 60 + (i // 2) * (bh + 24)
        rrect(d, (x, y, x + bw, y + bh), 10, fill=fill, outline=edge, width=2)
        txt(d, (x + 16, y + 14), title, font(16, True), fill=(20, 20, 26))
        for k, ln in enumerate(lines):
            txt(d, (x + 16, y + 50 + k * 26), "· " + ln, f_s, fill=(50, 50, 56))

    rrect(d, (36, 500, 1044, 540), 8, fill=(245, 245, 250), outline=(200, 200, 210))
    txt(d, (52, 516),
        "加热参数设置页只负责温控参数并显示计算说明；两页都有未保存修改时切换页面会询问“保存 / 不保存 / 取消”。",
        f_s, fill=(60, 60, 66))
    return im


# ============================================================
def fig_dim():
    im = Image.new("RGB", (1080, 380), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "无人值守自动降亮：按时间轴降低背光，触摸即恢复", f_h, fill=(20, 20, 24))

    d.line((80, 250, 1000, 250), fill=(150, 150, 160), width=3)
    for i in range(7):
        x = 80 + i * 153
        d.line((x, 240, x, 260), fill=(150, 150, 160), width=2)
        txt(d, (x, 268), "%d 分" % (i * 5), f_s, fill=(90, 90, 96), anchor="ma")

    pts = [(80, 80), (233, 80), (233, 200), (540, 200), (540, 60), (1000, 60)]
    d.line(pts, fill=HARMONY_B, width=3)
    txt(d, (90, 56), "亮度 100%", f_s, fill=HARMONY_B)
    rrect(d, (250, 186, 520, 216), 8, fill=(20, 40, 70))
    txt(d, (262, 192), "无人值守：降到目标亮度（0% = 关闭背光）", f_s, fill=(180, 210, 255))
    txt(d, (556, 40), "任意触摸立即恢复", f_s, fill=HARMONY_B)

    rrect(d, (80, 292, 1000, 348), 8, fill=(240, 246, 255), outline=(120, 160, 220))
    txt(d, (96, 306), "99.9% 无人值守的现场，背光衰减与图像残留是屏幕主要磨损源（质保通常不覆盖）。",
        f_s, fill=(40, 60, 100))
    txt(d, (96, 326),
        "“无人值守自动降亮”建议常开：降亮等待 0 分钟表示关闭该功能，降亮后亮度 0% 即熄灭背光。",
        f_s, fill=(40, 60, 100))
    return im


# ============================================================
def fig_troubleshoot():
    im = Image.new("RGB", (1080, 540), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "现场常见告警速查：看顶部 pill，按现象处置", f_h, fill=(20, 20, 24))

    rows = [
        ("⚠ 高压：1口-ID 2", "某子板检测到带电", "已自动切断全部加热回路，红灯+蜂鸣器",
         "确认现场停电后再操作；无需在程序里解锁"),
        ("⚠ 备用输入联锁 1 块", "备用输入达到联锁电平", "该子板自动温控停止、加热回路关闭",
         "排除现场信号源后由操作员重新启动自动"),
        ("⚠ 通信异常", "串口断开或写入连续失败", "顶部常驻通信异常，自动重连在后台进行",
         "检查串口线缆与 /dev/ttyS 节点；模拟器重启也会瞬时触发"),
        ("⚠ 全部子板离线", "两口均无在线子板", "数据停止刷新，CSV 暂停落盘",
         "先查线再接板；未接板的口会持续等待"),
        ("⚠ 系统时间异常", "系统时间早于最后记录时间", "顶部常驻红色告警，历史时间将错乱",
         "校正系统时间；每次掉电都出现即 RTC 电池耗尽"),
        ("⚠ 自检异常 N 块", "温湿度读数超出固定量程", "只提示不阻塞，仍可手动操作",
         "检查探头接线；连续 3 次正常自动解除"),
    ]
    heads = ["顶部提示", "含义", "程序动作", "现场处置"]
    xs = [48, 300, 560, 830]
    for i, hd in enumerate(heads):
        txt(d, (xs[i], 88), hd, f_t, fill=(20, 20, 26))
    d.line((40, 110, 1040, 110), fill=(200, 200, 210))
    for r, row in enumerate(rows):
        y = 124 + r * 66
        rrect(d, (40, y - 10, 1040, y + 52), 8,
              fill=(255, 250, 250) if r % 2 == 0 else (250, 250, 252), outline=(225, 225, 232))
        txt(d, (xs[0], y + 4), row[0], f_s, fill=(150, 50, 50))
        for i in range(1, 4):
            txt(d, (xs[i], y + 4), row[i], f_s, fill=(50, 50, 56))
    return im


# ============================================================
def fig_themes():
    im = Image.new("RGB", (1080, 300), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "五套预设主题即时生效；告警红 / 运行绿等安全色不随主题改变", f_h, fill=(20, 20, 24))

    themes = [("标准", (244, 247, 250), (30, 40, 60)), ("低光", (30, 34, 40), (225, 232, 240)),
              ("强光", (255, 255, 255), (20, 20, 24)), ("石墨灰", (24, 24, 26), (242, 242, 247)),
              ("鸿蒙", (242, 244, 247), (20, 25, 35))]
    bw = 194
    for i, (n, bg, fg) in enumerate(themes):
        x = 36 + i * (bw + 14)
        rrect(d, (x, 56, x + bw, 196), 10, fill=bg, outline=(170, 175, 190), width=2)
        txt(d, (x + 16, 68), n, f_t, fill=fg)
        rrect(d, (x + 12, 92, x + 58, 186), 6,
              fill=(232, 236, 242) if n == "标准" else (32, 34, 38))
        for k in range(5):
            rrect(d, (x + 18, 100 + k * 17, x + 52, 112 + k * 17), 4,
                  fill=HARMONY_B if k == 0 else (60, 62, 66))
        for jdx in range(2):
            rrect(d, (x + 66, 92 + jdx * 50, x + 182, 136 + jdx * 50), 6,
                  fill=CARD if n in ("石墨灰", "低光") else (255, 255, 255), outline=(90, 92, 96))
            if jdx == 0:
                txt(d, (x + 74, 100), "串口1·ID1", f_s, fill=fg)
            else:
                txt(d, (x + 74, 148), "● 自动温控", f_s, fill=(22, 143, 79) if n == "标准" else RUN)
                txt(d, (x + 74, 168), "加热器A  2档", f_s, fill=AMBER if n == "石墨灰" else (22, 143, 79))
    txt(d, (36, 216),
        "默认石墨灰：中性深灰，适合无人值守常亮；白底下不追赛Cyber色，避免把外观偏好误解为设备状态。",
        f_s, fill=(60, 60, 66))
    return im


# ============================================================
def fig_registers():
    im = Image.new("RGB", (1080, 500), (250, 250, 252))
    d = ImageDraw.Draw(im)
    f_h = font(17, True)
    f_t = font(13, True)
    f_s = font(11)
    txt(d, (24, 18), "程序实际轮询的寄存器段（一次读段一次读取，外扩输入以实测地址为准）", f_h, fill=(20, 20, 24))

    segs = [
        ("0x0000", "软件版本号", "V-x.x（顶部版本号）", (235, 245, 255), (80, 120, 190)),
        ("0x0001~0x000B", "输入采集区", "高压通电 / 备用 / 外部电压\n三路温湿度 + 两路 PT100",
         (240, 250, 242), (80, 140, 100)),
        ("0x000C", "外扩输入 IN1~IN5", "bit0~bit4（现场实测地址）", (255, 250, 240), (200, 160, 60)),
        ("0x000E", "旧固件回退地址", "协议文档写的地址，现场实测恒 0\n仅当非零时才覆盖 0x000C",
         (255, 246, 244), (200, 120, 110)),
        ("0x0031", "OT1~OT10 位掩码", "读写，bit0~bit9（RMW 保留其他位）", (245, 245, 250), (130, 130, 145)),
        ("0x0033", "外扩 OUT1~OUT7 位掩码", "读写，bit0~bit6（RMW 保留其他位）",
         (245, 245, 250), (130, 130, 145)),
    ]
    y = 56
    for addr, name, desc, fill, edge in segs:
        h = 66 if "\n" in desc else 54
        rrect(d, (40, y, 1040, y + h), 8, fill=fill, outline=edge, width=2)
        rrect(d, (40, y, 200, y + h), 8, fill=edge)
        txt(d, (120, y + h // 2), addr, f_t, fill=(255, 255, 255), anchor="ma")
        txt(d, (216, y + (12 if "\n" in desc else h // 2 - 8)), name, f_t, fill=(20, 20, 26))
        for k, ln in enumerate(desc.split("\n")):
            txt(d, (600, y + 12 + k * 16), ln, f_s, fill=(60, 60, 66))
        y += h + 8
    rrect(d, (40, y + 4, 1040, y + 70), 8, fill=(240, 246, 255), outline=(120, 160, 220))
    txt(d, (56, y + 14),
        "协议文档写的 0x000E 在现场 firmware 上实测恒为 0，外扩输入真实地址是 0x000C（设备端监视器 2026-09-26 确认：",
        f_s, fill=(40, 60, 100))
    txt(d, (56, y + 32), "IN1 保持闭合时 0x000C=0x0001，即 bit0=IN1）。0x000E 仍保留读取，作为旧 firmware 的回退路径。",
        f_s, fill=(40, 60, 100))
    txt(d, (56, y + 52), "温度类寄存器为 INT16 补码（兼容零下温度），原始值放大 10 倍；外部电压同样放大 10 倍后按阈值比较。",
        f_s, fill=(40, 60, 100))
    return im


for fn in [
    fig_main_layout, fig_wiring, fig_boot_flow, fig_nav_map, fig_card_anatomy,
    fig_manual_layout, fig_gear_map, fig_control_modes, fig_interlock,
    fig_data_browser, fig_advanced, fig_dim, fig_troubleshoot, fig_themes,
    fig_registers,
]:
    img = fn()
    name = fn.__name__.replace("fig_", "") + ".png"
    img.save(os.path.join(OUT, name))
    print("saved", name, img.size)
print("ALL DONE")
