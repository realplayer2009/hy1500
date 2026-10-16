#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建《变压器加热系统 使用手册》.docx
- 以当前工程代码为唯一事实来源
- 图文并茂：15 张程序界面/流程/速查插图（docs/manual/images/）
"""
import os

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "变压器加热系统-使用手册.docx")

# ---------------- 视觉规范 ----------------
NAV = RGBColor(0x00, 0x7D, 0xFF)      # 鸿蒙蓝（标题强调）
DARK = RGBColor(0x1F, 0x1F, 0x21)      # 石墨灰卡片
GREY = RGBColor(0x5F, 0x5F, 0x66)
RED = RGBColor(0xC9, 0x36, 0x32)
GREEN = RGBColor(0x16, 0x8F, 0x4F)
CYBER = RGBColor(0x00, 0xB8, 0x5F)
AMBER = RGBColor(0xFF, 0x91, 0x00)
BODY_FONT = "微软雅黑"
EN_FONT = "Segoe UI"

doc = Document()

# 页面：A4 纵向
sec = doc.sections[0]
sec.orientation = WD_ORIENT.PORTRAIT
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = Cm(2.2)
sec.bottom_margin = Cm(2.0)
CONTENT_W = sec.page_width - sec.left_margin - sec.right_margin


# ---------------- 基础工具 ----------------
def set_cn(run, name=BODY_FONT, size=10.5, bold=False, color=None, italic=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    r = run._element.rPr.rFonts
    r.set(qn("w:eastAsia"), name)
    r.set(qn("w:ascii"), name)
    r.set(qn("w:hAnsi"), name)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hexcolor)
    tcPr.append(el)


def cell_borders(cell, color="D8D8DE", sz=6):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:color"), color)
        borders.append(e)
    tcPr.append(borders)


def set_cell_text(cell, text, size=9, bold=False, color=None, align=None, font=BODY_FONT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    if align is not None:
        p.alignment = align
    for i, line in enumerate(str(text).split("\n")):
        if i:
            run = p.add_run()
            run.add_break()
        run = p.add_run(line)
        set_cn(run, font, size, bold, color)
    return p


def p_normal(text="", size=10.5, bold=False, color=None, align=None,
             before=3, after=3, indent=0, line=1.35):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if indent:
        pf.left_indent = Cm(indent)
    if align is not None:
        p.alignment = align
    if text:
        run = p.add_run(text)
        set_cn(run, BODY_FONT, size, bold, color)
    return p


def p_rich(parts, size=10.5, before=3, after=3, indent=0, line=1.35, align=None):
    """parts: list of (text, bold, color)"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if indent:
        pf.left_indent = Cm(indent)
    if align is not None:
        p.alignment = align
    for text, bold, color in parts:
        run = p.add_run(text)
        set_cn(run, BODY_FONT, size, bold, color)
    return p


def bullet(text, size=10.5, level=0, bold_head=None, color=None):
    p = doc.add_paragraph(style=None)
    pf = p.paragraph_format
    pf.left_indent = Cm(0.8 + 0.6 * level)
    pf.first_line_indent = Cm(-0.4)
    pf.space_before = Pt(1.5)
    pf.space_after = Pt(1.5)
    pf.line_spacing = 1.3
    mark = "• " if level == 0 else "– "
    r0 = p.add_run(mark)
    set_cn(r0, BODY_FONT, size, False, color)
    if bold_head:
        r1 = p.add_run(bold_head)
        set_cn(r1, BODY_FONT, size, True, color)
    r = p.add_run(text)
    set_cn(r, BODY_FONT, size, False, color)
    return p


def h1(text, num=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16)
    pf.space_after = Pt(6)
    pf.keep_with_next = True
    # 左侧竖杆效果用字符模拟
    r = p.add_run("▎")
    set_cn(r, BODY_FONT, 16, True, NAV)
    if num:
        r = p.add_run(f"{num}  ")
        set_cn(r, BODY_FONT, 16, True, NAV)
    r = p.add_run(text)
    set_cn(r, BODY_FONT, 16, True, DARK)
    # 底部分隔线
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "007DFF")
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(10)
    pf.space_after = Pt(4)
    pf.keep_with_next = True
    r = p.add_run(text)
    set_cn(r, BODY_FONT, 12.5, True, NAV)
    return p


def h3(text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(7)
    pf.space_after = Pt(3)
    pf.keep_with_next = True
    r = p.add_run(text)
    set_cn(r, BODY_FONT, 11, True, DARK)
    return p


def caption(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(8)
    r = p.add_run(text)
    set_cn(r, BODY_FONT, 9, False, GREY)
    return p


def image(fname, width_cm=None, cap=None):
    path = os.path.join(IMG, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    if width_cm is None:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            w, h = im.size
        width_cm = min(CONTENT_W.cm, 16.2)
        width_cm = width_cm * min(1.0, 10.5 / (h / w * width_cm))
    run.add_picture(path, width=Cm(width_cm))
    if cap:
        caption(cap)
    return p


def table(headers, rows, widths=None, header_fill="EAF2FF", zebra="F7F8FA",
          size=9, header_size=9.5, first_col_bold=False, align_center_cols=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    align_center_cols = align_center_cols or []
    hdr = t.rows[0].cells
    for i, htxt in enumerate(headers):
        set_cell_text(hdr[i], htxt, header_size, True, DARK,
                      WD_ALIGN_PARAGRAPH.CENTER)
        shade(hdr[i], header_fill)
        cell_borders(hdr[i])
    for ridx, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            bold = first_col_bold and i == 0
            color = None
            txt = str(val)
            if txt.startswith("⚠") or txt.startswith("禁止"):
                color = RED
                bold = True
            elif txt.startswith("✓") or txt in ("自动温控", "绿"):
                color = GREEN
            set_cell_text(cells[i], txt, size, bold, color,
                          WD_ALIGN_PARAGRAPH.CENTER if i in align_center_cols else None)
            cell_borders(cells[i])
            if zebra and ridx % 2 == 1:
                shade(cells[i], zebra)
    if widths:
        for r in t.rows:
            for i, w in enumerate(widths):
                r.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def callout(title, body, kind="info"):
    fills = {"info": "EAF2FF", "warn": "FFF3E6", "danger": "FFEDEC", "ok": "EDF7F0"}
    edges = {"info": "007DFF", "warn": "C77700", "danger": "C93632", "ok": "168F4F"}
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    c.width = CONTENT_W
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(title + "  ")
    set_cn(r, BODY_FONT, 10, True, RGBColor.from_string(edges[kind]))
    r2 = p.add_run(body)
    set_cn(r2, BODY_FONT, 9.5, False, DARK)
    shade(c, fills[kind])
    cell_borders(c, edges[kind], 8)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def pagebreak():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ============================================================
# 封面
# ============================================================
for _ in range(2):
    p_normal(before=0, after=0)

p_normal("四川裕泰通新能源科技有限公司", 11, False, GREY, WD_ALIGN_PARAGRAPH.CENTER, after=2)
p_normal("一站式科技服务提供商 · 电力检测实验设备 · 科技创新项目研发 · 系统应用装置研制",
         8.5, False, GREY, WD_ALIGN_PARAGRAPH.CENTER, after=26)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("变压器加热系统")
set_cn(r, BODY_FONT, 34, True, DARK)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(10)
r = p.add_run("使 用 手 册")
set_cn(r, BODY_FONT, 26, True, NAV)

p_normal("干式变压器箱内温湿度控制设备（YTT-TC1500）控制端软件", 11, False, GREY,
         WD_ALIGN_PARAGRAPH.CENTER, after=4)
p_normal("适用于 RK3562 工控触屏一体机（1024 × 600）· 鸿蒙界面外观", 10, False, GREY,
         WD_ALIGN_PARAGRAPH.CENTER, after=30)

image("main_layout.png", 16.0, "图 1-1　程序主界面（石墨灰主题，即出厂默认外观）")

t = doc.add_table(rows=4, cols=4)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
meta = [("文档名称", "变压器加热系统 使用手册", "文档版本", "V2.0"),
        ("适用程序", "变压器加热系统（RS485Control）", "发布日期", "2026 年 10 月"),
        ("目标硬件", "PA0715-N 7 寸工控一体机", "屏幕分辨率", "1024 × 600"),
        ("产品网址", "https://www.yttne.com/", "产品型号", "YTT-TC1500")]
for r_i, row in enumerate(meta):
    for c_i, val in enumerate(row):
        cell = t.rows[r_i].cells[c_i]
        set_cell_text(cell, val, 9,
                      bold=(c_i % 2 == 0),
                      color=GREY if c_i % 2 == 0 else DARK)
        shade(cell, "F2F4F8" if c_i % 2 == 0 else "FFFFFF")
        cell_borders(cell)
        cell.width = Cm(3.4)

pagebreak()

# ============================================================
# 目录
# ============================================================
h1("目 录")
toc = [
    ("1", "产品概述与安全须知", ""),
    ("1.1", "产品简介与工作原理", ""),
    ("1.2", "装箱清单", ""),
    ("1.3", "安全须知（务必先读）", ""),
    ("2", "安装、接线与启动", ""),
    ("2.1", "系统接线示意图", ""),
    ("2.2", "控制端与加热装置端安装要点", ""),
    ("2.3", "开机启动与自检流程", ""),
    ("3", "界面导览：六个页面各管一件事", ""),
    ("3.1", "主窗口布局", ""),
    ("3.2", "六个导航页面地图", ""),
    ("4", "域控子板总览", ""),
    ("4.1", "页面结构与摘要信息", ""),
    ("4.2", "单张子板卡片逐行解读", ""),
    ("5", "子板手自控制", ""),
    ("5.1", "页面布局：左测量、右操作", ""),
    ("5.2", "启动 / 停止自动温控", ""),
    ("5.3", "加热器手动控制（屏幕与实体按键同效）", ""),
    ("5.4", "档位、继电器与工作灯的对应关系", ""),
    ("5.5", "只读状态灯与扩展输出", ""),
    ("6", "加热参数设置", ""),
    ("6.1", "目标温度来源", ""),
    ("6.2", "三种温控模式", ""),
    ("6.3", "计算说明与操作要点", ""),
    ("7", "安全联锁与自检", ""),
    ("7.1", "高压安全联锁", ""),
    ("7.2", "备用输入联锁", ""),
    ("7.3", "温湿度自检", ""),
    ("7.4", "现场常见告警速查", ""),
    ("8", "数据浏览", ""),
    ("8.1", "筛选与查询", ""),
    ("8.2", "曲线图交互", ""),
    ("8.3", "明细表格与实时追加", ""),
    ("9", "高级设置", ""),
    ("9.1", "接口配置", ""),
    ("9.2", "安全保护", ""),
    ("9.3", "数据采集与存储", ""),
    ("9.4", "显示与声音", ""),
    ("10", "关于本机与运维设置", ""),
    ("10.1", "关于本机页", ""),
    ("10.2", "屏幕亮度与无人值守自动降亮", ""),
    ("11", "寄存器与通信参数速查", ""),
    ("12", "现场维护与故障恢复", ""),
    ("13", "附录：术语表与联系我们", ""),
]
for num, title, _ in toc:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(1)
    pf.space_after = Pt(1)
    pf.left_indent = Cm(0 if "." not in num else 0.9)
    r = p.add_run(f"{num}　")
    set_cn(r, EN_FONT, 10.5, True, NAV)
    r = p.add_run(title)
    set_cn(r, BODY_FONT, 10.5, False, DARK)

pagebreak()

# ============================================================
# 1 产品概述与安全须知
# ============================================================
h1("产品概述与安全须知", "1")

h2("1.1 产品简介与工作原理")
p_normal(
    "变压器加热系统是一款专为保障干式变压器运行安全而设计的箱内温湿度精准调控设备，"
    "由控制端与加热装置端协同组成。设备核心功能是变压器箱内温湿度的智能管控，"
    "同时集成多重安全保护与闭锁机制，用于解决干式变压器箱内结露受潮、停机后湿气滞留、"
    "温度异常波动引发的绝缘性能下降、内部元件老化加速与电气性能受干扰等问题。"
    "控制端程序在国产化工控触屏一体机上运行，按鸿蒙界面外观呈现。")

p_rich([("工作方式：", True, DARK),
        ("控制端通过高压带电传感器实时监测变压器带电状态。检测到断电时，控制端依据采集的"
         "温湿度数据自动或手动调节三路加热器档位，带走箱内湿气、抑制结露；一旦检测到带电，"
         "立即切断全部加热回路并声光报警，联锁优先级高于一切操作。", False, None)])

h3("三种工作模式")
bullet("由程序按设定目标自动切档，维持箱内合理温度环境，无需人工干预；", bold_head="自动模式：")
bullet("可强制启停三路加热器、逐路切换继电器状态，适配应急场景与现场调试；", bold_head="手动模式：")
bullet("防止停机后箱内结露，按露点余量独立切档（详见 6.2 节）。", bold_head="防凝露控制：")

h3("主要功能一览")
table(
    ["功能", "说明"],
    [["温湿度精准调控", "三种控制模式（阈值 / PID / 防凝露）各三档，参数全部界面可调"],
     ["安全闭锁防护", "高压带电检测切断全部加热回路并声光报警；备用输入联锁可按电平静默"],
     ["数据查询", "按日期与子板筛选历史记录，曲线 + 明细联动，支持秒级聚合"],
     ["运行记录", "CSV 按日期分文件落盘，默认 12 GB 容量内全部保留"],
     ["故障报警", "三色灯（OT7/OT8/OT9）+ 蜂鸣器（OT10）声光提示，顶部同时列出告警子板的串口与 Modbus ID"],
     ["操作确认", "屏幕按键与实体按键默认有确认音；当前现场蜂鸣器统一接 OT（OT10 高压报警），"
                 "确认音走外扩 OUT5（选配，需另接蜂鸣器）"]],
    widths=[4.2, 12.2], first_col_bold=True)

callout("提示：",
        "本手册描述的软件部分全部依据随程序发布的控制端固件行为编写。"
        "若现场更换了不同版本固件，请以出厂随附的《接线与参数对照表》为准。",
        "info")

h2("1.2 装箱清单")
table(
    ["#", "部件", "说明", "数量"],
    [["1", "7 寸工控触屏一体机（PA0715-N）", "RK3562 / 1024×600，鸿蒙界面外观", "1"],
     ["2", "RS485 主控板", "Modbus RTU，19200 / N / 8 / 1", "1"],
     ["3", "子板（加热控制板）", "每路 RS485 最多 16 块，从站地址 1~247", "最多 2×16"],
     ["4", "温湿度传感器", "外置三路，菊花链方式接入", "1 ~ 3"],
     ["5", "PT100 温度传感器", "子板内部两路温度测量", "1 ~ 2"],
     ["6", "高压带电传感器", "数字量或模拟量两种检测方式", "1"],
     ["7", "三色灯（绿 / 黄 / 红）", "OT7 绿、OT8 黄、OT9 红", "1"],
     ["8", "蜂鸣器", "接主控板 OT10，高压带电时持续报警", "1"],
     ["9", "多路继电器板", "每路加热器由一对 OT 继电器驱动", "3 ~ 5 组"],
     ["10", "加热装置 A / B / C", "箱内加热与风量执行机构", "最多 6 台"]],
    widths=[0.9, 5.0, 7.6, 2.9], align_center_cols=[0, 3])

h2("1.3 安全须知（务必先读）")
table(
    ["事项", "要求"],
    [["禁止带电接线", "所有 RS485 线缆、传感器线缆的连接与断开，必须在断电状态下进行。"],
     ["高压信号最高优先级", "检测到带电时，系统自动切断全部加热回路并声光报警；此状态下手动或"
                            "自动开启加热均无效，必须确认现场停电后再操作。"],
     ["严禁带电强行操作", "严禁变压器带电时强行启动加热装置或改动接线。"],
     ["专业人员操作", "安装、接线、维修需由具备相应资质的专业电气人员操作，严格遵守电气安全规范。"],
     ["手动模式仅限应急", "正常运行建议保持自动模式；应急操作后请切回自动模式。"],
     ["传感器标定", "高压阈值等安全参数的默认值仅供开发，正式使用前必须按现场传感器标定。"],
    ["禁止带电拆壳", "运行中禁止随意拆卸设备外壳或接线端子，维修前务必断开电源。"]],
    widths=[4.0, 12.4], first_col_bold=True)

callout("高压联锁优先级最高：",
        "高压带电检测是控制安全的最高优先级，高于自动温控与一切手动操作。"
        "解除告警后不会自动恢复自动运行，须由操作员确认现场安全后重新启动。",
        "danger")

pagebreak()

# ============================================================
# 2 安装、接线与启动
# ============================================================
h1("安装、接线与启动", "2")

h2("2.1 系统接线示意图")
image("wiring.png", 16.2, "图 2-1　控制端、子板、传感器与指示设备的接线关系")

h3("两条 RS485 总线")
table(
    ["总线", "程序配置", "默认串口", "接入内容"],
    [["Port0（主线）", "RS485-A", "/dev/ttyS4", "上位机主控板"],
     ["Port1（子板）", "RS485-B", "/dev/ttyS2", "各子板（最多 16 块/口）"]],
    widths=[3.2, 3.0, 3.6, 6.6], align_center_cols=[1, 2], first_col_bold=True)

callout("⚠ 换屏或重烧系统后必须核对串口：",
        "该机型规格书标注 COM1=ttyS01、COM2=ttyS02，但现场 RS485 实际挂在 ttyS4。"
        "换屏、重烧系统或按规格书重新接线后，请用 ls /dev/ttyS* 与调试脚本确认有从站"
        "响应的串口，再同步修改 app.ini。", "warn")

h3("子板输出与现场设备的对应")
table(
    ["输出", "现场设备", "行为说明"],
    [["OT1 ~ OT6", "加热器与备用回路", "三组加热器各占一对 OT；其余可配置联动模式"],
     ["OT7", "三色灯 - 绿色", "自动温控运行时点亮"],
     ["OT8", "三色灯 - 黄色", "停留在手动操作页时点亮"],
     ["OT9", "三色灯 - 红色", "故障 / 高压 / 备用输入联锁时点亮"],
     ["OT10", "蜂鸣器（当前现场接线）", "现场蜂鸣器统一接 OT10：高压带电时持续报警"],
     ["OUT1 ~ OUT3", "加热器 A/B/C 工作灯", "对应加热器有档位即点亮，关闭即熄灭"],
     ["OUT5", "操作确认音输出（选配）", "程序每次操作闭合 0.2 秒；当前现场未在此口接蜂鸣器，"
                                       "故按键暂无提示音响（需要时在该口并接一只蜂鸣器即可）"],
     ["OUT4", "备用扩展输出", "唯一保留手动切换入口的扩展输出"]],
    widths=[2.4, 4.6, 9.4], align_center_cols=[0], first_col_bold=True)

callout("OT 与 OUT 的分工：",
        "开合继电器回路与蜂鸣器一律走 OT（0x0031 位掩码，bit0～bit9）：三组加热器各占一对 OT 开合加热，"
        "OT7/OT8/OT9 三色灯、OT10 蜂鸣器（当前现场唯一接线的那只蜂鸣器）都挂在 OT 上。"
        "OUT1～OUT7（0x0033）是外扩输出板上的辅助通道，只做工作灯与扩展指示，只读回读，"
        "仅 OUT4 保留手动切换；OUT5 是给外接提示音预留的通道，现场没接就不响。"
        "排查：回路不动作查 OT 接线与主控板，灯不亮再查外扩输出板。", "info")

h2("2.2 控制端与加热装置端安装要点")
h3("控制端")
bullet("安装于变压器箱外便于观察、操作，且无强烈振动、腐蚀的平整位置；")
bullet("按接线图牢固连接线路，确保极性正确、绝缘良好；")
bullet("串口端子剥线约 3 mm，按橙色按钮插底后松手；芯片向下、缺口在左；")
bullet("DC 12 V 圆孔供电（外径 5.5 mm / 内径 2.1 mm）。")

h3("加热装置端")
bullet("选择通风良好、不影响其他设备运行维护的位置，保证气流覆盖箱内目标区域；")
bullet("通过适配安装结构牢固固定，接线符合电气规范；")
bullet("加热装置与箱内带电体保持足够安全距离，外壳按现场装配要求可靠接地。")

h3("整机使用注意")
bullet("屏幕常亮、定时开关机与看门狗守护由设备系统自身设置保证，"
       "与程序内“无人值守自动降亮”是两回事，二者不要互相撤掉；")
bullet("恢复出厂设置类操作会清空现场已部署的程序与配置，执行前须留存部署包，现场慎用；")
bullet("远程维护通道按设备厂商提供的网络方式接入，不要改动系统底层设置。")

h2("2.3 开机启动与自检流程")
image("boot_flow.png", 16.0, "图 2-2　从上电到正常监控的流程与异常分支")

h3("启动过程做了什么")
bullet("启动链路自动拉起程序，进入前屏；")
bullet("从工作目录加载 app.ini（串口、通信参数、数据存储路径等）；")
bullet("两条 RS485 总线分别扫描 Modbus ID 1~247，每口发现第一块子板即停止，"
       "最多保留 16 块/口；未接板的口持续等待，接板即被发现；")
bullet("顶部出现最多 60 秒的自检倒计时，所有在线子板正确读到温湿度数据后立即显示"
       "“✓ 自检正常”；")
bullet("此后可按 4~10 节进行日常操作。")

callout("多子板场景：",
        "启动时每口只扫到第一块子板即停。如果现场接了多块子板但界面上只显示一块，"
        "请在“高级设置 → 安全保护”旁的“重新扫描子板”执行一轮完整扫描，"
        "扫描完成后会自动停止。", "info")

pagebreak()

# ============================================================
# 3 界面导览
# ============================================================
h1("界面导览：六个页面各管一件事", "3")

h2("3.1 主窗口布局")
image("nav_map.png", 16.0, "图 3-1　主窗口由侧栏导航、顶部状态栏、内容区与底部状态栏组成")

table(
    ["区域", "内容", "说明"],
    [["左侧导航栏", "品牌名 + 六个页面按钮", "固定宽 182 px，按钮最小高 58 px，适合触摸操作；"
                                              "当前页按钮蓝底白字高亮"],
     ["顶部状态栏", "页面标题 / 自检 pill / 系统状态 pill / 版本号 / 实时时钟",
      "时钟每秒刷新；良性状态（自动运行 X/Y 块、系统正常）时系统状态 pill 隐藏，"
      "只保留自检 pill，告警与搜索等中性态照常显示"],
     ["内容区", "当前页面的完整内容", "各页面独立滚动，触摸滚动条加宽到 36 px"],
     ["底部状态栏", "初始化进度、通信状态、操作结果", "实时反映最近一次操作与总线状态"]],
    widths=[2.8, 6.6, 7.0], first_col_bold=True)

h2("3.2 六个导航页面地图")
table(
    ["页面", "用途", "详见"],
    [["域控子板总览", "所有已发现子板的状态卡片，一眼看全场的运行模式、档位与告警", "第 4 节"],
     ["子板手自控制", "选中子板的测量显示、加热器与继电器操作、自动温控启停", "第 5 节"],
     ["加热参数设置", "温控模式、目标温度与计算说明", "第 6 节"],
     ["数据浏览", "历史曲线与明细表格，按日期 / 子板筛选", "第 8 节"],
     ["高级设置", "接口配置、安全保护、数据存储、显示与声音", "第 9 节"],
     ["关于本机", "程序版本、芯片与操作系统信息", "第 10 节"]],
    widths=[3.6, 9.6, 3.2], first_col_bold=True, align_center_cols=[2])

callout("未保存就切页会拦住你：",
        "在“加热参数设置”或“高级设置”里改了参数但没保存时切换页面，程序会询问"
        "“保存 / 不保存 / 取消”。“不保存”只撤销当前页的临时修改，主题仍沿用即时保存。",
        "info")

pagebreak()

# ============================================================
# 4 域控子板总览
# ============================================================
h1("域控子板总览", "4")

h2("4.1 页面结构与摘要信息")
image("card_anatomy.png", 16.0, "图 4-1　总览卡片信息分区")

p_normal("总览页首屏完整显示四块子板（两列 × 两行），更多子板可垂直滚动浏览；"
         "只有一块子板时卡片铺满整行。顶部摘要条显示“共 N 块 · 在线 N · 离线 N · 告警 N”。")

h3("摘要条与刷新")
bullet("卡片随轮询实时刷新，无需手动刷新；")
bullet("离线子板的卡片保留在网格中，并显示“● 离线”，其缓存的旧读数只保留在设备状态里，"
       "不充当实时数据；")
bullet("点击任意卡片即跳转到“子板手自控制”并自动选中该子板。")

h2("4.2 单张子板卡片逐行解读")
table(
    ["卡片行", "内容", "怎么读"],
    [["第一行", "串口号 · 子板 ID + 运行模式", "“● 自动温控”为绿色，“● 手动”为蓝色；"
                                                "子板离线时显示“离线”"],
     ["第二行", "三栏测量值", "平均温度、平均湿度（均取外部三路有效值的平均）、"
                             "PT100 均温（两路内部温度平均）"],
     ["第三行", "三组加热器档位", "A / B / C 各自显示“关闭 / 1档 / 2档 / 3档”，"
                                 "颜色随主题的安全语义显示"],
     ["第四行", "只读状态灯与蜂鸣器", "绿灯=自动运行、黄灯=手动模式、红灯=故障/告警、蜂鸣器；"
                                     "被加热器占用的 OT 不在卡片上重复显示"],
     ["第五行", "安全状态", "“● 在线 / ⚠ 高压告警 / ⚠ 备用输入联锁 / ⚠ 传感器异常”，"
                           "并列出外部电压与备用输入电平"]],
    widths=[2.0, 4.6, 9.8], first_col_bold=True)

callout("卡片上的档位来自实际输出回读：",
        "不论是手动点击还是自动温控驱动继电器，卡片档位都按该子板 OT 输出对的回读解码，"
        "保证界面显示与实际接线状态一致。", "ok")

pagebreak()

# ============================================================
# 5 子板手自控制
# ============================================================
h1("子板手自控制", "5")

h2("5.1 页面布局：左测量、右操作")
image("manual_layout.png", 16.2, "图 5-1　左侧测量区（约 70%）+ 右侧控制区（约 30%）")

h3("左侧测量区")
bullet("子板下拉框列出所有已发现子板（串口 + ID），离线子板仍可选择查看；")
bullet("温湿度 A/B/C 三张卡显示每路温度（℃）与湿度（%RH）；")
bullet("加热器状态 A/B/C 三张卡显示目标温度与三个 36×36 px 档位方框；")
bullet("PT100 温度 1/2 与外部电压三张小卡在底部；")
bullet("“最后更新”时间戳显示最近一次轮询时间。")

h3("右侧控制区（可滚动）")
bullet("自动温控区：运行状态标签、三路平均温度、当前工作状态与“启动自动 / 停止自动”按钮；")
bullet("操作横幅：提示当前是否可以操作（正常 / 高压联锁 / 等待数据 / 自动运行中）；")
bullet("加热器按键区：三个大按钮对应加热器 A/B/C，显示当前档位；")
bullet("加热回路操作区：按实际用途命名的继电器按钮，可逐路开 / 关；")
bullet("外扩输出：OUT4 备用扩展输出保留手动切换入口。")

callout("中间状态区还有这些只读信息：",
        "当前工作状态、自动温控参数摘要、状态指示灯 OT7~OT10、现场开关与按键"
        "（外扩输入 IN1~IN5）、工作灯与扩展设备（OUT1~OUT7）。指示灯与蜂鸣器只读，"
        "不提供手动切换——手动写入会在下一轮轮询被自动逻辑覆盖。", "info")

h2("5.2 启动 / 停止自动温控")
table(
    ["操作", "前提条件", "结果"],
    [["启动自动", "子板在线、无高压告警、无备用输入联锁",
      "三路加热器先一律退到关闭，再按温控程序执行；绿灯亮起"],
     ["停止自动", "自动运行中",
      "自动运行期间的加热输出全部关闭（继电器 + 工作灯同步断），绿灯熄灭"]],
    widths=[2.4, 6.4, 7.6], first_col_bold=True)

bullet("启动 / 停止只作用于当前选中子板，不影响其他子板的自动状态；")
bullet("自动温控运行期间，加热器手动按键与逐路继电器按钮被禁用，避免与自动指令冲突；")
bullet("高压告警发生时会自动停止全部子板的自动温控。")

h2("5.3 加热器手动控制（屏幕与实体按键同效）")
p_normal("三个加热器 A/B/C 各有四档，每按一次进一档，循环切换：")
p_rich([("关闭 → 1 档 → 2 档 → 3 档 → 关闭", True, NAV)], align=WD_ALIGN_PARAGRAPH.CENTER, before=4, after=6)

bullet("屏幕按键：点击右侧控制区的加热器按钮；")
bullet("实体按键：拨动外扩输入开关（按“高级设置 → 外扩输入接入配置”分配为加热器 A/B/C 按键后），"
       "程序检测上升沿即切档，效果与屏幕按键完全相同；")
bullet("每次操作（屏幕或实体）都有操作确认音动作：程序默认驱动外扩 OUT5 闭合 0.2 秒，"
       "连按时先强制断开再闭合保证完整上升沿；当前现场蜂鸣器统一接在 OT（OT10 高压报警），"
       "OUT5 未并接蜂鸣器时该动作无声，需要提示音请在 OUT5 上并接一只；")
bullet("以下状态下手动加热被拒绝：子板离线、自动温控运行中、高压告警、备用输入联锁。")

callout("自动运行期间加热器让位自动：",
        "切到自动温控时，三路加热器先退到关闭，再由温控程序驱动各自的 OT 输出对。"
        "因此自动运行时点不动加热器按钮，这是正常保护，不是故障。", "warn")

h2("5.4 档位、继电器与工作灯的对应关系")
image("gear_map.png", 16.0, "图 5-2　四档状态如何映射到一对继电器与工作灯")

bullet("每个加热器由一对 OT 继电器驱动：低位继电器=1 档、高位继电器=2 档、两路同开=3 档；")
bullet("第一档用哪一路继电器由“两个单路档位顺序”统一指定（加热参数页与防凝露共用一个配置）；")
bullet("三路加热器各自独立计算，互不影响，即使强功率接近也可分别开启；")
bullet("工作灯 OUT1~OUT3 按每个加热器输出对的实际档位同步，只在档位变化时写一次。")

h2("5.5 只读状态灯与扩展输出")
table(
    ["显示项", "颜色 / 含义", "能否手动切换"],
    [["自动运行绿灯（OT7）", "绿=该子板自动温控运行中", "只读"],
     ["手动模式黄灯（OT8）", "黄=停留在手动操作页且未自动运行", "只读"],
     ["故障报警红灯（OT9）", "红=传感器异常 / 备用输入联锁 / 高压告警", "只读"],
     ["高压报警蜂鸣器（OT10）", "现场唯一接线的蜂鸣器；高压告警时持续提示", "只读"],
     ["OUT1 ~ OUT3 工作灯", "对应加热器有档位即亮", "只读"],
     ["OUT5 操作确认音输出", "选配通道：程序每次操作闭合 0.2 秒；当前未接蜂鸣器，故无提示音响",
      "只读"],
     ["OUT6 闪烁灯 / OUT7 蜂鸣器", "外扩预留指示，显示回读状态，尚未接入自动联动", "只读"],
     ["OUT4 备用扩展输出", "备用扩展通道", "可手动切换"]],
    widths=[5.4, 7.4, 3.6], first_col_bold=True, align_center_cols=[2])

pagebreak()

# ============================================================
# 6 加热参数设置
# ============================================================
h1("加热参数设置", "6")

h2("6.1 目标温度来源")
table(
    ["选项", "含义", "适用场景"],
    [["跟随内部 PT100", "目标取子板内部两路 PT100 有效读数的平均值；一路有效即用该路，"
                        "两路均无有效值时本轮跳过调度",
      "需要按变压器本体温度而非箱内气温控制时"],
     ["固定温度", "三个加热器各自独立设定目标温度（加热器 A/B/C 目标温度）",
      "三个加热器安装位置或用途不同、需要不同目标时"]],
    widths=[3.2, 8.4, 4.8], first_col_bold=True)

bullet("被控量始终是外部三路温湿度探头的有效平均温度；")
bullet("PT100 的控制有效范围固定为 -40～85 ℃，有一路有效即可跟随；")
bullet("防凝露模式不使用目标温度来源，改用露点余量控制。")

h2("6.2 三种温控模式")
image("control_modes.png", 16.2, "图 6-1　三种模式共用同一套三档输出，只是切档依据不同")

table(
    ["模式", "切档依据", "默认边界", "关键参数"],
    [["阈值三档", "目标 − 外部平均温度的温差", "0.3 / 1.5 / 3.0 ℃，回差 0.2 ℃",
      "三个温差 + 回差；两个单路档位顺序"],
     ["PID 三档", "0～100% 的加热需求", "输出点 10% / 35% / 60%",
      "Kp=12、Ki=0.15、Kd=0；三个输出点；第一档输出点"],
     ["防凝露三档", "露点余量 = PT100 均温 − 最不利露点", "3 / 2 / 1 ℃，回差 0.2 ℃",
      "三个余量 + 回差 + 温升上限（默认 5 ℃）"]],
    widths=[2.4, 4.6, 4.2, 5.2], first_col_bold=True)

h3("防凝露模式补充说明")
bullet("三组外部温湿度分别按 Magnus 公式计算露点，取最高值作为最不利空气条件；")
bullet("表面温度采用内部有效 PT100 平均值，因此露点余量直接反映结露风险；")
bullet("无最高档限制：余量足够低时可以直接开到两路同开；")
bullet("外部平均温度超过 PT100 平均值 + 温升上限（默认 5 ℃）时停止加热，"
       "避免仅为降低相对湿度而持续升温；")
bullet("露点参考（空气温度 / 相对湿度 → 露点）：30 ℃/80 %RH ≈ 26 ℃；25 ℃/80 %RH ≈ 21 ℃；"
       "25 ℃/60 %RH ≈ 17 ℃；20 ℃/80 %RH ≈ 16 ℃；15 ℃/60 %RH ≈ 7 ℃。")

h3("各模式的级档节奏")
table(
    ["档位", "输出状态", "含义"],
    [["关闭（0 档）", "两路继电器均断开", "无需加热"],
     ["1 档", "仅第一路闭合", "低功率单路加热"],
     ["2 档", "仅第二路闭合", "高功率单路加热"],
     ["3 档", "两路同开", "两路同开最高档"]],
    widths=[3.0, 5.0, 8.4], first_col_bold=True, align_center_cols=[0])

h2("6.3 计算说明与操作要点")
bullet("计算说明默认折叠，点击“展开计算说明”可查看当前参数下的切档边界与实际效果，"
       "小屏上避免被长文案占满；")
bullet("参数输入框和下拉框禁用鼠标滚轮，防止触摸屏或鼠标误改数值；")
bullet("SD 周期、删除时长与继电器间隔使用支持长按的外置 − / + 按钮，长按可连续调整；")
bullet("修改参数后点击“保存并应用”，约 3 秒内显示 ✓ / ⚠ 操作反馈；任一参数修改会立即清除旧反馈；")
bullet("继电器两次状态改变默认最短间隔 10 秒（可设 1~3600 秒），只抑制阈值附近的频繁切换，"
       "高压联锁切断不受此限制。")

pagebreak()

# ============================================================
# 7 安全联锁与自检
# ============================================================
h1("安全联锁与自检", "7")

h2("7.1 高压安全联锁")
image("fig_interlock.png" if os.path.exists(os.path.join(IMG, "fig_interlock.png")) else "interlock.png",
      16.0, "图 7-1　高压联锁的触发、切断与解除流程")

table(
    ["检测类型", "读取寄存器", "触发条件", "说明"],
    [["模拟信号", "0x0003（外部电压）", "原始值 ÷ 10 后严格高于阈值时触发",
      "默认检测方式；随附配置阈值 5.0 V（代码内建 1.0 V），投运前须按现场传感器标定"],
     ["数字信号", "0x0001（高压通电输入）", "输入值等于触发值（0 或 1）时触发",
      "传感器为数字量时选用"]],
    widths=[2.4, 4.0, 5.2, 4.8], first_col_bold=True)

h3("触发后程序做什么")
bullet("立即切断全部子板的三个加热器输出对及对应工作灯（OUT1~OUT3）；")
bullet("清空各加热器的手动档位会话；")
bullet("点亮故障红灯（OT9）与高压报警蜂鸣器（OT10）；")
bullet("停止所有子板的自动温控；")
bullet("顶部状态栏列出每个告警子板的串口与 Modbus ID，例如“⚠ 高压：1口-ID 2、2口-ID 3”；")
bullet("此期间拒绝手动开启加热回路，也拒绝“重新扫描子板”。")

h3("解除后")
bullet("检测到失电后立即解除告警，继电器状态随下一轮轮询回读刷新；")
bullet("不会自动恢复自动温控，须由操作员确认现场安全后重新启动；"
       "这是防止带电恢复后意外启动加热的必备设计。")

callout("⚠ 正式投运前必须标定：",
        "高压阈值等安全参数的默认值仅供开发调试。请按现场高压带电传感器的实际输出"
        "标定阈值与检测类型，并在“高级设置 → 安全保护”中保存。", "danger")

h2("7.2 备用输入联锁")
bullet("备用输入寄存器 0x0002 可配置为仅监视、高电平联锁或低电平联锁；")
bullet("联锁触发时：停止该子板自动温控、关闭全部加热回路与工作灯、清除手动档位、点亮红灯；")
bullet("弹窗显示该子板的串口与 Modbus ID，提示已停止自动温控；")
bullet("解除后需重新启动自动温控；联锁只作用于该子板，不影响其他子板。")

h2("7.3 温湿度自检")
table(
    ["检查项", "默认值", "行为"],
    [["自检倒计时", "60 秒（固定，不开放修改）", "所有在线子板正确读到温湿度数据后立即显示“✓ 自检正常”"],
     ["温度有效范围", "-40 ～ 85 ℃", "超出即报传感器异常，自动调度排除该探头，用剩余正常探头平均继续"],
     ["湿度有效范围", "0 ～ 100 %RH", "超出即报传感器异常"],
     ["自动恢复", "连续 3 次正常（固定）", "恢复期间显示剩余次数，不向用户开放这些参数"]],
    widths=[3.2, 4.6, 8.6], first_col_bold=True)

bullet("三路探头允许处于不同位置，程序不做相互偏差判断；")
bullet("缺数据只保持“数据未齐”通知，不报故障；")
bullet("自检告警不停止整体自动温控、不拦截手动操作，只在顶部醒目提示。")

h2("7.4 现场常见告警速查")
image("troubleshoot.png", 16.2, "图 7-2　按顶部提示查原因与处置")

pagebreak()

# ============================================================
# 8 数据浏览
# ============================================================
h1("数据浏览", "8")

h2("8.1 筛选与查询")
image("data_browser.png", 16.2, "图 8-1　筛选栏、曲线区与明细表格")

bullet("日期范围：“从 / 至”两个日期选择器，默认最近 7 天；")
bullet("子板下拉框合并了当前在线子板与 CSV 中出现过的历史子板，离线旧子板仍可选，"
       "只存在于 CSV 的条目标注“历史”；")
bullet("点“查询”发起后台查询，界面不冻结；右侧摘要显示精确记录数与曲线时间点数；")
bullet("“仅看表格”按钮在小屏上把空间集中给明细数据，再点一次恢复曲线。")

h3("“全部子板”与单块子板的区别")
bullet("选择具体子板：只返回该子板记录，曲线按时间连续显示；")
bullet("选择“全部子板”：先按整秒聚合各子板样本，主曲线显示总体平均值，"
       "橙色半透明带显示当秒各子板平均温度的最高—最低范围；点击曲线时详细信息同时给出"
       "温度范围和参与聚合的记录数；表格不做聚合，仍保留单板原始明细。")

h2("8.2 曲线图交互")
table(
    ["交互", "操作", "效果"],
    [["十字线检视", "点击曲线任意位置", "显示该时间点的子板、时间、温度、湿度"],
     ["拖动查看旧数据", "左右拖动曲线", "切换时间段，新数据不会抢回视图位置"],
     ["恢复跟随最新", "拖回最右端", "新记录自动追加并跟随最新"],
     ["水平时间滚动条", "拖动滚动条", "滚动条高 36 px，拖块最小宽 100 px，适合触摸"]],
    widths=[3.4, 5.2, 7.8], first_col_bold=True)

bullet("三条固定颜色曲线便于跨主题识别：橙色实线=温湿度计温度、蓝色点线=温湿度计湿度、"
       "紫色虚线=PT100 温度；")
bullet("曲线背景、坐标与十字线跟随当前主题调色板；")
bullet("大数据量自动抽样（上限 2400 点），查询经后台线程执行，UI 轮询取结果。")

h2("8.3 明细表格与实时追加")
bullet("表格五列：时间、子板、平均温度、平均湿度、高压状态（“带电”以警示色标出）；")
bullet("列宽自动拉伸、交替行背景色、整行选中、只读不可编辑；")
bullet("表格默认隐藏，点“仅看表格”后显示，最多显示最新 500 行；")
bullet("停留在数据浏览页时，新记录持续增量更新曲线与表格（单次进内存上限 5 万条，"
       "超限后暂停追加并提示重新查询）；")
bullet("首次进入页面才读取 CSV，之后切页复用内存缓存；只有日期 / 子板条件改变后才重读。")

h3("CSV 文件说明")
bullet("按日期分文件存储：dataPath/YYYY-MM-DD.csv；")
bullet("新表头保存身份列、三路温湿度、两路 PT100、外部电压、备用输入与 OT1～OT6；"
       "不保存可由其他列推导的平均值、设定参数与指示灯；")
bullet("当天已有旧版 CSV 时继续按旧格式写到当天结束，避免同一文件混用两套列定义；")
bullet("历史解析同时兼容旧六列 JSON 格式与新的精简列格式，升级当天即可查看旧数据。")

pagebreak()

# ============================================================
# 9 高级设置
# ============================================================
h1("高级设置", "9")
image("advanced.png", 16.2, "图 9-1　高级设置的四个分组")

p_normal("“高级设置”独立成页，收纳全部运维配置。加热参数页只保留温控参数与计算说明，"
         "两页保存时只写各自负责的字段，不会互相覆盖。")

h2("9.1 接口配置")
h3("外扩输入接入配置")
bullet("IN1~IN5 可各自分配功能：未使用 / 手自动选择（仅监视）/ 加热器 A 按键 / "
       "加热器 B 按键 / 加热器 C 按键 / 高压闭锁（仅监视）；")
bullet("随附配置默认 IN2=加热器 A 按键、IN3=加热器 B 按键、IN4=加热器 C 按键，"
       "IN1/IN5 未使用（代码内建默认为全部未使用，按现场实配为准）；")
bullet("用途是现场防错线排查：拨动现场开关，看哪一路 IN 的实时状态在跳，"
       "就把实际功能分配给该 IN；")
bullet("加热器 A/B/C 映射驱动实体按键上升沿切档；手自动选择与高压闭锁映射目前仅用于显示，"
       "其联动行为按现场要求暂不接入；")
bullet("高级设置里的实时 IN 状态只跟随手动页当前选中的子板，避免多子板轮询时闪烁。")

h3("加热器输出配置")
bullet("每个加热器使用两路继电器，可在 5 组输出对里选择（第 1、2 路 ~ 第 9、10 路）；")
bullet("随附配置默认 A=第 1 组（OT1+OT2）、B=第 2 组（OT3+OT4）、C=第 3 组（OT5+OT6）；")
bullet("保存时拒绝三个加热器共用同一组回路；读取旧配置时若有重复依次分配到未占用的输出对；")
bullet("映射改变时自动停止自动温控，并关断旧、新回路及 OUT1~OUT3，避免旧回路保持带电。")

h3("备用接口逻辑")
table(
    ["配置项", "可选值", "行为"],
    [["OT1 / OT2 / OT5 / OT6", "安全关闭 / 手动控制 / 跟随自动运行 / 跟随报警 / 跟随 OT3 / 跟随 OT4",
      "跟随主回路时优先同步本次下发值，没有主回路指令时按该子板当前状态同步"],
     ["备用输入", "仅监视 / 高电平时联锁 / 低电平时联锁", "联锁时停止自动并切断加热回路"]],
    widths=[3.6, 6.2, 6.6], first_col_bold=True)

h2("9.2 安全保护")
bullet("高压安全联锁：检测类型（模拟 / 数字）、数字触发值、模拟量电压阈值，详见 7.1 节；")
bullet("继电器切换保护：各加热器两次回路状态改变的最短间隔，默认 10 秒，可设 1~3600 秒；"
       "该限制只抑制阈值附近的频繁切换，高压联锁切断不延时；")
bullet("“重新扫描子板”按钮位于本分组旁，点击后会先停止全部自动温控并清空旧发现列表，"
       "高压告警期间拒绝重新扫描。")

h2("9.3 数据采集与存储")
table(
    ["配置项", "范围 / 默认", "说明"],
    [["轮询周期", "0.1 ~ 3600 秒，默认 0.1 秒", "单板现场快速采样；轮询快保证控制响应"],
     ["记录周期", "0.1 ~ 3600 秒，默认 1 秒", "独立配置，控制存储增长；单板约 7.8 MB/天"],
     ["日志容量上限", "1 ~ 100 GB，默认 12 GB", "上限内全部保留，不再按天数自动删除；"
                                                 "12 GB 约合 4 年历史"],
     ["手动清理", "按天 / 月 / 年设定截止日期", "先预览文件数量与容量，二次确认后才删除"]],
    widths=[3.0, 5.4, 8.0], first_col_bold=True)

bullet("“存储信息”区显示存储总量、剩余空间、日志占用、CSV 文件数与日期范围，"
       "参数页每 10 秒自动刷新，也可点“刷新存储信息”；")
bullet("清理采用严格小于：选择“删除超过 30 天”时，今天起第 30 天当天的文件不会被删除；"
       "删除只作用于合法的 YYYY-MM-DD.csv。")

h2("9.4 显示与声音")
image("themes.png", 16.0, "图 9-2　五套预设主题")

table(
    ["主题", "定位", "适用场景"],
    [["标准", "浅色常规样式", "室内明亮环境或初次调试"],
     ["低光", "深色低亮样式", "弱光环境，减少眩光"],
     ["强光", "高对比浅色", "户外或强光直射下读取"],
     ["石墨灰（默认）", "中性深灰", "无人值守常亮场景的首选"],
     ["鸿蒙", "鸿蒙外观主色 #007DFF、圆角卡片化", "与现场鸿蒙系统外观一致"]],
    widths=[3.4, 5.6, 7.4], first_col_bold=True)

bullet("主题选择后即时生效并单独持久化；")
bullet("告警红、运行绿等安全语义颜色不随主题改变，避免把外观偏好误解为设备状态；")
bullet("操作提示音：屏幕按键与实体加热器按键操作时，程序都发一次确认音动作（外扩 OUT5 闭合 "
       "0.2 秒）；当前现场蜂鸣器统一接在 OT10（高压报警），OUT5 未并接蜂鸣器时听不到该音，"
       "需要提示音请在 OUT5 上并接一只；可整体关闭。")

pagebreak()

# ============================================================
# 10 关于本机与运维设置
# ============================================================
h1("关于本机与运维设置", "10")

h2("10.1 关于本机页")
bullet("显示程序名称“裕泰通加热器”与程序版本（版本：RS485Control 1.0.0）；")
bullet("名称下方一句话说明本机用途：域控子板温湿度采集、自动温控与历史数据浏览；")
bullet("芯片与操作系统信息：芯片 RK3568，操作系统为鸿蒙操作系统；")
bullet("本页为静态信息页，不带可修改参数；顶栏最右侧的版本号标签显示当前在线子板回报的"
       "固件版本（v××，未读到时显示 v--）。")

h2("10.2 屏幕亮度与无人值守自动降亮")
image("dim.png", 16.0, "图 10-1　亮度随时间自动降低，任意触摸立即恢复")

table(
    ["配置项", "范围", "行为"],
    [["屏幕亮度滑条", "5% ~ 100%，即时生效", "亮度越高背光衰减越快，建议按现场光照设定"],
     ["无人值守自动降亮", "等待 0 ~ 1440 分钟", "达到等待时间后降到目标亮度，0 分钟表示关闭该功能"],
     ["降亮后亮度", "0% ~ 100%", "0% 即关闭背光；任意触摸立即恢复"]],
    widths=[3.6, 4.8, 8.0], first_col_bold=True)

bullet("99.9% 无人值守的现场，背光衰减与图像残留是屏幕的主要磨损源（质保通常不覆盖）；")
bullet("活动检测挂在应用级事件过滤器上：鼠标、触摸、滚轮、按键都会恢复亮度；")
bullet("若设备上亮度控制路径不可用（如开发机），程序静默降级，不影响其他功能。")

h3("系统时间异常检测")
bullet("程序把最后一条记录的时间原子写入数据目录的 .last_record_time；")
bullet("启动时若发现系统时间早于该时间 1 分钟以上，顶部常驻红色“⚠ 系统时间异常”；")
bullet("断电丢失实时时钟时靠它避免错误时间静默污染历史数据；")
bullet("若每次掉电都出现该提示，说明内置 RTC 电池耗尽，需硬件维修。")

pagebreak()

# ============================================================
# 11 寄存器与通信参数速查
# ============================================================
h1("寄存器与通信参数速查", "11")

h2("11.1 通信参数")
table(
    ["项", "值"],
    [["协议", "Modbus RTU"],
     ["波特率 / 数据位 / 校验 / 停止位", "19200 / 8 / N / 1"],
     ["读取功能码 / 写入功能码", "0x03（读保持寄存器）/ 0x10（写多个寄存器）"],
     ["从站地址范围", "1 ~ 247（按现场装配设置）"],
     ["每口最多子板数", "16 块"],
     ["发现超时 / 正常轮询超时", "150 ms 发现 / 按配置超时"],
     ["默认串口", "Port0 = /dev/ttyS4，Port1 = /dev/ttyS2"]],
    widths=[6.4, 10.0], first_col_bold=True)

h2("11.2 程序实际轮询的寄存器段")
image("registers.png", 16.0, "图 11-1　主程序每个轮询周期读取的寄存器段")

table(
    ["地址", "字段", "解析规则"],
    [["0x0000", "软件版本号", "整形，显示为 V-x.x"],
     ["0x0001", "高压通电输入", "0=无，1=有（数字量联锁源）"],
     ["0x0002", "备用输入", "可配置联锁电平"],
     ["0x0003", "外部电压", "原始值放大 10 倍，÷10 后按阈值比较"],
     ["0x0004 ~ 0x0009", "三路温湿度", "温度在前、湿度在后，均放大 10 倍，INT16 补码"],
     ["0x000A ~ 0x000B", "PT100 温度 1/2", "放大 10 倍，INT16 补码"],
     ["0x000C", "外扩输入 IN1~IN5", "bit0~bit4，现场实测地址"],
     ["0x000E", "外扩输入（旧地址）", "协议文档地址，现场实测恒 0；仅当非零时覆盖 0x000C"],
     ["0x0031", "OT1~OT10 位掩码", "读写，bit0~bit9，位掩码 RMW 保留其他位"],
     ["0x0033", "外扩 OUT1~OUT7 位掩码", "读写，bit0~bit6，位掩码 RMW 保留其他位"]],
    widths=[3.2, 4.6, 8.6], first_col_bold=True)

callout("现场实测结论（重要）：",
        "协议文档写的外扩输入地址 0x000E 在现场 firmware 上实测恒为 0，"
        "实际地址是 0x000C（IN1~IN5 = bit0~bit4）。程序保留 0x000E 的读取作为旧固件回退，"
        "只有非零时才覆盖 0x000C 的结果。用调试脚本核对时请以 0x000C 为准。", "warn")

h2("11.3 输出与输入字段速查")
table(
    ["类别", "编号", "名称"],
    [["OT 输出（0x0031 位掩码）", "OT1 ~ OT10", "加热器 A/B/C 由成对 OT 驱动；"
                                                  "OT7 绿 / OT8 黄 / OT9 红 / OT10 蜂鸣器（现场接线）"],
     ["外扩输入（0x000C）", "IN1 ~ IN5", "IN1 = bit0，依次到 IN5 = bit4"],
     ["外扩输出（0x0033 位掩码）", "OUT1 ~ OUT7", "OUT1~OUT3 = 加热器工作灯、"
                                                    "OUT4 = 备用扩展输出、OUT5 = 操作确认音（选配 未接）"]],
    widths=[4.6, 3.2, 8.6], first_col_bold=True)

h2("11.4 调试脚本常用命令")
table(
    ["命令", "用途"],
    [["ports", "列出电脑上的串口设备"],
     ["scan", "扫描 Modbus 从站地址（默认 1~15）"],
     ["read 0x0021 5", "读取 0x0021 起的 5 个寄存器"],
     ["snapshot", "按项目文档读取全部寄存器组快照"],
     ["monitor 0x0041 2", "每秒读取温湿度传感器 1 的温度与湿度"],
     ["write 0x0001 1 --allow-write", "写寄存器（危险操作，需人工确认大写 WRITE）"],
     ["-v snapshot", "显示原始 TX/RX 报文与 CRC 校验"]],
    widths=[6.0, 10.4], first_col_bold=True)

callout("地址口径提醒：",
        "调试脚本按《RS485 / Modbus RTU 调试脚本使用说明》的寄存器口径寻址"
        "（如 0x0021 状态区、0x0041 温湿度传感器 1），与 11.2 节主程序轮询段地址编号不同。"
        "核对现场数据时请以随附《协议文档》与本节说明为准，避免混用两套编号。", "warn")

callout("⚠ 写寄存器是危险操作：",
        "未获得负责人许可、未确认现场安全、不了解寄存器含义时，不要执行 write。"
        "写寄存器可能启动加热器、蜂鸣器或自动控制。", "danger")

pagebreak()

# ============================================================
# 12 现场维护与故障恢复
# ============================================================
h1("现场维护与故障恢复", "12")

h2("12.1 日常维护要点")
bullet("定期在“高级设置 → 数据存储”查看存储占用与文件数，必要时按截止日期手动清理；")
bullet("确认设备端屏幕常亮与守护设置生效，避免无人值守时系统回收程序进程；")
bullet("远程维护走设备厂商提供的网络通道，不要随意改动系统底层设置；")
bullet("更换屏幕、重新烧录系统或重新接线后，必须核对串口节点与 RS485 接线方向；")
bullet("掉电重启后先看顶部：若每次掉电都出现“⚠ 系统时间异常”，安排更换 RTC 电池。")

h2("12.2 按现象快分流")
table(
    ["现象", "先查什么", "处置"],
    [["屏幕全黑，不确定设备是否在运行", "设备供电与程序进程是否都在",
      "进程都在只是熄屏，按电源键唤醒；长期熄屏检查设备屏幕常亮设置"],
     ["界面看得见，触摸点不动", "屏幕触控方式与校准", "在设备显示设置里把触控改回直接触摸，取消触控板/鼠标模拟模式"],
     ["界面能出但无数据", "串口节点与线缆", "查 /dev/ttyS* 权限与接线；用调试脚本 scan 找到有响应的口"],
     ["放置一段时间控制系统消失", "系统熄屏回收进程组", "确认设备看门狗/守护与屏幕常亮两项措施同时生效"],
     ["重启后不回到控制界面", "开机自启链路", "按 设备启动 → 常驻服务 → 控制程序 的顺序分层排查"]],
    widths=[4.4, 4.4, 7.6], first_col_bold=True)

h2("12.3 分层排查法")
bullet("先分层定位，再单点验证：设备系统层 → 常驻服务层 → 串口通信层 → 界面显示层 → 操作触控层；")
bullet("报错文案是线索不是结论，系统日志才是证据；")
bullet("改完任何一层，按回归清单逐项验收（上电自启、重复启动不重开、回到程序、断电重启恢复、"
       "长时间放置进程保在、屏幕常亮、中文与触控）；")
bullet("需要重刷时：先断电重启等待自然启动完成；仍无画面再按开机自启链路手工拉起一次，"
       "确认是链路问题还是系统问题；都进不去时联系硬件厂商。")

pagebreak()

# ============================================================
# 13 附录
# ============================================================
h1("附录：术语表与联系我们", "13")

h2("13.1 术语表")
table(
    ["术语", "含义"],
    [["子板", "挂接在 RS485 总线上的加热控制板，每块有独立 Modbus ID"],
     ["OT 输出", "主控板上的继电器输出位，OT1~OT10，用 0x0031 位掩码读写"],
     ["OUT 输出", "外扩输出位，OUT1~OUT7，用 0x0033 位掩码读写"],
     ["IN 输入", "外扩输入位，IN1~IN5，实测地址 0x000C"],
     ["菊花链", "多个传感器串联接入同一条总线，共用总线与地址"],
     ["露点余量", "内部 PT100 平均温度减去最不利露点，反映结露风险"],
     ["自检倒计时", "上电后等最多 60 秒，直到所有在线子板读到温湿度数据"],
     ["备用输入联锁", "备用输入达到设定电平时停止自动并切断加热回路"],
     ["RMW", "读-改-写：只改指定位，保留其他位不变"]],
    widths=[3.6, 12.8], first_col_bold=True)

h2("13.2 出厂默认参数")
table(
    ["分类", "参数", "默认值"],
    [["温控", "控制模式 / 目标来源", "PID 三档 / 固定温度（A=30 / B=25 / C=28 ℃）"],
     ["温控", "阈值温差 / 回差", "0.3 / 1.5 / 3.0 ℃，回差 0.2 ℃"],
     ["温控", "PID 参数 / 输出点", "Kp=12、Ki=0.15、Kd=0；10% / 35% / 60%"],
     ["温控", "防凝露余量 / 温升上限", "3 / 2 / 1 ℃，回差 0.2 ℃；上限 5 ℃"],
     ["加热器", "输出组", "A=第 1 组、B=第 2 组、C=第 3 组"],
     ["安全", "高压检测", "模拟量模式，阈值 5.0 V，数字触发值 0（投运前须现场标定）"],
     ["安全", "备用输入", "仅监视"],
     ["安全", "继电器最短切换间隔", "10 秒"],
     ["采集", "轮询周期 / 记录周期", "0.1 秒 / 1 秒"],
     ["存储", "日志容量上限", "12 GB"],
     ["显示", "主题 / 亮度 / 自动降亮", "石墨灰 / 100% / 10 分钟降到 0%"],
     ["交互", "操作提示音", "开启"]],
    widths=[2.4, 6.0, 8.0], first_col_bold=True)

callout("未配置时代码内建默认值：",
        "控制模式回落阈值三档、目标来源回落跟随 PT100、外扩输入全部未使用、高压模拟量阈值 1.0 V。"
        "现场以随附 config/app.ini 为准；上表整理自该文件的出厂值。", "info")

h2("13.3 联系我们")
table(
    ["项", "内容"],
    [["公司", "四川裕泰通新能源科技有限公司"],
     ["地址", "中国（四川）自由贸易试验区成都高新区天府大道中段 530 号 2 栋 12 楼 1223 号"],
     ["邮箱", "admin@yttne.com"],
     ["产品网址", "https://www.yttne.com/"],
     ["服务热线", "服务电话与在线支持方式见产品官网首页公示"]],
    widths=[3.2, 13.2], first_col_bold=True)

p_normal()
p_rich([("文档结束。", True, GREY)], align=WD_ALIGN_PARAGRAPH.CENTER, before=10)
p_rich([("本手册依据变压器加热系统（RS485Control）当前版本控制端程序行为编写，"
         "随程序版本升级持续更新。", False, GREY)],
       align=WD_ALIGN_PARAGRAPH.CENTER, before=2)

# ============================================================
# 页脚
# ============================================================
footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = footer_p.add_run("变压器加热系统 使用手册 ｜ 四川裕泰通新能源科技有限公司 ｜ 第 ")
set_cn(r, BODY_FONT, 8, False, GREY)
fld = OxmlElement("w:fldSimple")
fld.set(qn("w:instr"), "PAGE")
run_el = OxmlElement("w:r")
rpr = OxmlElement("w:rPr")
sz = OxmlElement("w:sz")
sz.set(qn("w:val"), "16")
rpr.append(sz)
run_el.append(rpr)
t_el = OxmlElement("w:t")
t_el.text = "1"
run_el.append(t_el)
fld.append(run_el)
footer_p._p.append(fld)
r = footer_p.add_run(" 页")
set_cn(r, BODY_FONT, 8, False, GREY)

doc.save(OUT)
print("saved:", OUT)
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables))
