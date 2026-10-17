#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标贴 / 合格证 打印版生成器（彩色版）
====================================

用途
    按 A4 纸排版「变压器加热控制器 YTT-TC1500 ×20」与「变压器加热器
    YTT-CR850A ×60」的标贴与合格证，每张序列号唯一，输出可直接打印的
    PDF。标贴与合格证均为彩色：品牌色 + 产品色码 + 检验合格红。

排版口径（全部可在下方 CONFIG 区改）
    A4 210×297 mm，四边 5 mm 安全边 → 可印 200×287 mm。
    标签 47×47 mm（≈50 mm，正方形），横向 4 张：
        4×47 + 3×4 = 200 mm  → 可印宽度 100% 用满
    纵向 5 张：
        5×47 + 4×9 = 271 mm  → 可印高度 94% 用满
    每页 20 张：控制器 20 张 = 1 页；加热器 60 张 = 3 页。

配色来源（不是随手挑的）
    藏青 #26297A 与亮蓝 #54C7F4 取自仓库既有官方证书原稿
    docs/合格证_四川裕泰通新能源科技有限公司.png 的实际主色
    （亮蓝约占 56% 面积、藏青为边框/文字色）。
    产品色码：控制器用品牌藏青，加热器用暖橙（热感语义），
    现场一眼分辨两种标贴，黑白打印也能按深浅区分。

型号写法注意
    仓库《docs/客户使用说明书 (2).md》写的是 YYT-TC1500（两个 T），
    本次按需求方口述采用 YTT-TC1500。以实物铭牌为准，改 PRODUCTS
    里 model 一个字段即可整体切换。

logo 来源
    assets/boot_logo.bmp（1024×600 灰度、黑底），内容边界框
    640×146，横向三段式组合标。按亮度转 alpha 后染成藏青，
    不改变原图形状，也不重绘。

用法
    python3 docs/labels/make_labels.py
    python3 docs/labels/verify.py      # 版面自检
"""
from __future__ import annotations

import io
import os
import sys
import zlib

from PIL import Image, ImageDraw, ImageFont

# ============================================================
# CONFIG —— 现场信息只改这一段
# ============================================================

BRAND = "裕泰通"
MANUFACTURER = "四川裕泰通新能源科技有限公司"
LOGO_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "assets", "boot_logo.bmp")

PRODUCE_DATE = "2026-09-01"              # 生产日期（9 月批次）
INSPECT_DATE = "2026-09-01"              # 检验日期
INSPECTOR = ""                           # 检验员，留空显示签字横线
SN_SEQ_START = 60                        # 序号起始，060 起

FONT_SANS = "/System/Library/Fonts/Hiragino Sans GB.ttc"       # 黑体
FONT_SERIF = "/System/Library/Fonts/Supplemental/Songti.ttc"   # 宋体

A4_W, A4_H = 210.0, 297.0                 # mm
MARGIN = 5.0                              # mm 四边安全边
LABEL = 47.0                              # mm 标签边长（正方形）
H_GAP = 4.0                               # mm 横向间隙
V_GAP = 9.0                               # mm 纵向间隙
COLS, ROWS = 4, 5
PER_PAGE = COLS * ROWS                    # 20

PAD = 3.2                                 # mm 标签内左右边距
VALUE_X = 15.0                            # mm 字段值起点
DPI = 300
PX = DPI / 25.4                           # px per mm
MM_PER_PX = 25.4 / DPI

# ---- 配色 ----
NAVY = (38, 41, 122)          # #26297A 品牌主色（取自官方证书原稿）
NAVY_TINT = (233, 234, 246)   # 藏青浅底
PASS_RED = (178, 34, 34)      # #B22222 检验合格红
INK = (28, 28, 32)            # 正文近黑
GREY = (105, 105, 115)        # 辅助灰
WHITE = (255, 255, 255)

# 产品色码：控制器=品牌藏青；加热器=暖橙（热感语义）
PRODUCTS = [
    dict(key="ctrl",
         name="变压器加热控制器",
         model="YTT-TC1500",
         qty=20,
         color=NAVY,
         tint=NAVY_TINT),
    dict(key="heat",
         name="变压器加热器",
         model="YTT-CR850A",
         qty=60,
         color=(176, 74, 22),            # #B04A16 暖橙
         tint=(253, 240, 227)),
]

LOGO_W_NAMEPLATE = 22.0       # mm 标贴上的 logo 宽（无角标，放大填补）
LOGO_W_CERT = 17.0            # mm 合格证上的 logo 宽

# ---- 二维码（海康风格：二维码 + 编号 + 型号）----
QR_SIZE = 15.0                # mm 二维码视觉边长
QR_ECC = "M"                  # 纠错级
# 二维码内容：型号 + 编号，空格分隔，扫码后两者都直接可见。
# 不放 URL——公司没有可用的真实网站，编造查询链接比只放型号编号更糟。
# 例：YTT-TC1500 YTT-TC1500-2609-060（30 字符 → 版本 2，25×25 模块）
def qr_payload(product: dict, sn: str) -> str:
    return "{} {}".format(product["model"], sn)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qr as _qr                      # noqa: E402  同目录自实现编码器


# 序列号：<型号>-<YYMM>-<3位序号>；型号已含品牌码，不重复前缀
def make_sn(product: dict, seq: int) -> str:
    yymm = PRODUCE_DATE[2:4] + PRODUCE_DATE[5:7]
    return "{}-{}-{:03d}".format(product["model"], yymm, seq)


def sn_list(product: dict) -> list[str]:
    return [make_sn(product, SN_SEQ_START + i) for i in range(product["qty"])]


# ============================================================
# 画布基元
# ============================================================

def mm(v: float) -> int:
    return int(round(v * PX))


_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}


def load_font(pt: float, bold: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont:
    key = (pt, bold, serif)
    if key not in _FONT_CACHE:
        path = FONT_SERIF if serif else FONT_SANS
        _FONT_CACHE[key] = ImageFont.truetype(
            path, int(round(pt * DPI / 72.0)), index=0)
    return _FONT_CACHE[key]


OVERFLOW: list[str] = []


def txt(d: ImageDraw.ImageDraw, x_mm: float, y_mm: float, s: str,
        f: ImageFont.FreeTypeFont, fill=INK, anchor="la",
        limit_mm: float | None = None) -> None:
    """画文字；limit_mm 给出自 x_mm 起允许的最大宽度，超宽即记录。"""
    if limit_mm is not None:
        w = f.getlength(s) * MM_PER_PX
        if w > limit_mm:
            OVERFLOW.append("'{}' 宽 {:.1f} mm > 限 {:.1f} mm".format(s, w, limit_mm))
    d.text((mm(x_mm), mm(y_mm)), s, font=f, fill=fill, anchor=anchor)


def hline(d: ImageDraw.ImageDraw, x1, y, x2, w=0.3, fill=NAVY) -> None:
    d.line([(mm(x1), mm(y)), (mm(x2), mm(y))], fill=fill, width=max(1, mm(w)))


def frame(d: ImageDraw.ImageDraw, ox: float, oy: float, color=NAVY, w_mm=0.35) -> None:
    """标签外框，兼作裁切线。"""
    d.rectangle([mm(ox), mm(oy), mm(ox + LABEL), mm(oy + LABEL)],
                outline=color, width=max(1, mm(w_mm)))


# ============================================================
# logo：从 boot_logo.bmp 提取，按亮度转 alpha，染成指定颜色
# ============================================================

_LOGO_CACHE: dict[tuple, Image.Image] = {}


def build_logo(color: tuple, width_mm: float) -> Image.Image:
    key = (color, width_mm)
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]

    src = Image.open(LOGO_SRC).convert("L")
    mask = src.point(lambda v: 255 if v > 40 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise RuntimeError("logo 源图中找不到内容：{}".format(LOGO_SRC))
    # PIL 的 crop 右/下边界排外，+1 才是完整内容；否则宽高比偏差约 1%
    src = src.crop((bbox[0], bbox[1], bbox[2] + 1, bbox[3] + 1))

    # 亮度 → 不透明度；原图为白字黑底，故内容不透明、背景全透明
    alpha = src.point(lambda v: min(255, int(v * 1.12)))
    rgba = Image.new("RGBA", src.size, color + (0,))
    rgba.putalpha(alpha)

    tw = max(1, mm(width_mm))
    th = max(1, int(round(tw * src.height / src.width)))
    out = rgba.resize((tw, th), Image.LANCZOS)
    _LOGO_CACHE[key] = out
    return out


def paste_logo(im: Image.Image, color: tuple, width_mm: float,
               x_mm: float, y_mm: float) -> tuple[float, float]:
    """把 logo 贴到 (x_mm, y_mm) 左上角，返回其占位宽高（mm）。"""
    logo = build_logo(color, width_mm)
    im.paste(logo, (mm(x_mm), mm(y_mm)), logo)
    return logo.width * MM_PER_PX, logo.height * MM_PER_PX


# ============================================================
# 二维码：渲染 qr.qr_matrix() 的矩阵，最近邻放大，不做抗锯齿
# ============================================================
# 二维码模块必须棱角分明，插值/抗锯齿会让扫码枪识别率下降，故按整数
# 像素倍率放大。静区（白边）不画进图里——标签底面本身就是白的，
# 只要四周留足 ≥2 个模块的空白即满足 ISO/IEC 18004 的静区要求。

_QR_CACHE: dict[tuple, Image.Image] = {}


def build_qr(product: dict, sn: str, color: tuple) -> Image.Image:
    key = (product["model"], sn, color)
    if key not in _QR_CACHE:
        m, ver, mask = _qr.qr_matrix(qr_payload(product, sn), QR_ECC)
        n = len(m)
        mod = max(2, mm(QR_SIZE) // n)          # 每模块像素数（整数）
        im = Image.new("RGB", (n * mod, n * mod), WHITE)
        dd = ImageDraw.Draw(im)
        for r in range(n):
            for c in range(n):
                if m[r][c]:
                    dd.rectangle([c * mod, r * mod,
                                  (c + 1) * mod - 1, (r + 1) * mod - 1],
                                 fill=color)
        _QR_CACHE[key] = im
    return _QR_CACHE[key]


def paste_qr(im: Image.Image, product: dict, sn: str, color: tuple,
             cx_mm: float, top_mm: float) -> tuple[float, float, float]:
    """把二维码水平居中于 cx_mm、顶边在 top_mm 贴上。

    返回 (实际宽mm, 实际高mm, 每模块mm)。模块尺寸需 ≥0.5 mm 才好扫。
    """
    q = build_qr(product, sn, color)
    w_mm = q.width * MM_PER_PX
    h_mm = q.height * MM_PER_PX
    im.paste(q, (mm(cx_mm) - q.width // 2, mm(top_mm)))
    n = len(_qr.qr_matrix(qr_payload(product, sn), QR_ECC)[0])
    mod_mm = q.width / n * MM_PER_PX
    return w_mm, h_mm, mod_mm


# ============================================================
# 单张标签：标贴
# ============================================================

def draw_nameplate(im: Image.Image, d: ImageDraw.ImageDraw,
                   ox: float, oy: float, product: dict, sn: str) -> None:
    """标贴：海康摄像头风格——二维码 + 编号 + 型号 + 品名 + 厂家。

    不印「合格证」字样：那是证书的标题，标贴上重复反而冗余。

    版面（相对标签左上角，单位 mm）：
        0.35~10.2  品牌带：logo(左) + 厂家名
        11.0       分隔线
        12.5       产品名称 12pt 居中
        17.4       型　号
        21.7       分隔线
        22.7       二维码 15mm 居中（编码型号 + 编号）
        38.5       编　号 8pt 加粗，产品色，全宽一行
        42.0       日　期
    """
    frame(d, ox, oy, color=product["color"])
    cx = ox + LABEL / 2.0
    inner = LABEL - 2 * PAD
    col, tint = product["color"], product["tint"]

    # 品牌带：产品色浅底 + 公司 logo + 厂家名
    d.rectangle([mm(ox + 0.35), mm(oy + 0.35), mm(ox + LABEL - 0.35), mm(oy + 10.2)],
                fill=tint, outline=None)
    paste_logo(im, NAVY, LOGO_W_NAMEPLATE, ox + PAD, oy + 2.3)
    # 厂家名放在品牌带内，省出底部一整行给编号
    txt(d, ox + PAD, oy + 7.8, MANUFACTURER, load_font(5.8), fill=GREY,
        limit_mm=inner)

    hline(d, ox + PAD, oy + 11.0, ox + LABEL - PAD, w=0.4, fill=col)

    # 产品名称
    txt(d, cx, oy + 12.5, product["name"], load_font(12, bold=True),
        anchor="ma", limit_mm=inner)

    # 型号
    txt(d, ox + PAD, oy + 17.4, "型  号", load_font(8.2), fill=GREY)
    txt(d, ox + VALUE_X, oy + 17.0, product["model"], load_font(9.5),
        limit_mm=LABEL - PAD - VALUE_X)

    hline(d, ox + PAD, oy + 21.7, ox + LABEL - PAD, w=0.4, fill=col)

    # 二维码：居中，编码「型号 + 编号」
    qw, qh, mod_mm = paste_qr(im, product, sn, col, cx, oy + 22.7)
    if mod_mm < 0.5:
        OVERFLOW.append("{} 二维码模块仅 {:.3f} mm，小于 0.5 mm 不利扫码".format(
            sn, mod_mm))

    # 编号：单独一行，全宽，加粗，产品色——现场最常扫/抄的一行
    txt(d, cx, oy + 38.5, sn, load_font(8.0, bold=True), fill=col,
        anchor="ma", limit_mm=inner)

    # 日期
    txt(d, cx, oy + 42.0, PRODUCE_DATE, load_font(5.8), fill=GREY,
        anchor="ma", limit_mm=inner)


# ============================================================
# 单张标签：合格证
# ============================================================

def draw_certificate(im: Image.Image, d: ImageDraw.ImageDraw,
                     ox: float, oy: float, product: dict, sn: str) -> None:
    frame(d, ox, oy, color=product["color"], w_mm=0.5)
    cx = ox + LABEL / 2.0
    inner = LABEL - 2 * PAD
    col = product["color"]

    # 页眉：公司 logo（左）+ 合格证标题（右）
    paste_logo(im, NAVY, LOGO_W_CERT, ox + PAD, oy + 3.4)
    txt(d, ox + LABEL - PAD, oy + 3.2, "合 格 证", load_font(15, bold=True, serif=True),
        fill=NAVY, anchor="ra", limit_mm=inner - LOGO_W_CERT - 2.0)

    hline(d, ox + 6.0, oy + 10.0, ox + LABEL - 6.0, w=0.6, fill=NAVY)

    for label, value, y, pt in (("产品名称", product["name"], oy + 11.4, 7.8),
                                ("型　　号", product["model"], oy + 15.3, 8.2),
                                ("检验日期", INSPECT_DATE, oy + 19.1, 8.2)):
        txt(d, ox + PAD, y, label, load_font(7.4), fill=GREY)
        txt(d, ox + VALUE_X, y - 0.3, value, load_font(pt),
            limit_mm=LABEL - PAD - VALUE_X)

    hline(d, ox + PAD, oy + 23.5, ox + LABEL - PAD, w=0.4, fill=col)

    # 编号单独一行，产品色加粗
    txt(d, ox + PAD, oy + 24.8, "编　　号", load_font(7.0), fill=GREY)
    txt(d, ox + PAD, oy + 27.5, sn, load_font(8.8, bold=True), fill=col,
        limit_mm=inner)

    # 检验结论框：结论用合格红
    by = oy + 31.9
    d.rectangle([mm(ox + PAD), mm(by), mm(ox + LABEL - PAD), mm(by + 7.0)],
                outline=col, width=max(1, mm(0.45)))
    txt(d, ox + PAD + 1.8, by + 3.0, "检验结论", load_font(7.4), fill=GREY, anchor="lm")
    txt(d, ox + LABEL - PAD - 1.8, by + 3.0, "合　格", load_font(10, bold=True),
        fill=PASS_RED, anchor="rm", limit_mm=inner - 13.0)

    # 检验员签字位
    txt(d, ox + PAD, oy + 40.0, "检 验 员", load_font(7.2), fill=GREY)
    sig = INSPECTOR if INSPECTOR else "＿" * 7
    txt(d, ox + VALUE_X - 1.0, oy + 39.7, sig, load_font(7.6),
        limit_mm=LABEL - PAD - VALUE_X + 1.0)

    txt(d, cx, oy + 43.2, MANUFACTURER, load_font(6.0), fill=GREY,
        anchor="ma", limit_mm=inner)


# ============================================================
# 页面合成
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
OUT_PDF = os.path.join(OUT_DIR, "标贴与合格证_打印版.pdf")
OUT_LOGO = os.path.join(OUT_DIR, "公司logo_藏青.png")

SLOTS = [(MARGIN + c * (LABEL + H_GAP), MARGIN + r * (LABEL + V_GAP))
         for r in range(ROWS) for c in range(COLS)]


def new_page():
    im = Image.new("RGB", (mm(A4_W), mm(A4_H)), WHITE)
    return im, ImageDraw.Draw(im)


def write_sn_list() -> str:
    """导出序列号清单 CSV，供生产留档与 SN-整机对应。"""
    import csv
    path = os.path.join(OUT_DIR, "序列号清单.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["产品名称", "型号", "序列号", "生产日期", "制造商"])
        for prod in PRODUCTS:
            for sn in sn_list(prod):
                w.writerow([prod["name"], prod["model"], sn,
                            PRODUCE_DATE, MANUFACTURER])
    return path


def write_sn_list_pdf() -> str:
    """序列号清单 PDF：80 行表格，A4 两栏排，供仓库核对粘贴。"""
    rows = [(prod["name"], prod["model"], sn, PRODUCE_DATE)
            for prod in PRODUCTS for sn in sn_list(prod)]
    per_col = 41
    half = (len(rows) + 1) // 2
    cols = [rows[:half], rows[half:]]

    im, d = new_page()
    paste_logo(im, NAVY, 22.0, MARGIN, 8.0)
    txt(d, MARGIN, 16.5, "序列号清单", load_font(15, bold=True, serif=True), fill=NAVY)
    txt(d, MARGIN, 22.0,
        "{} ~ {}　共 {} 个　生产日期 {}".format(
            rows[0][2], rows[-1][2], len(rows), PRODUCE_DATE),
        load_font(7.5), fill=GREY)
    hline(d, MARGIN, 27.5, A4_W - MARGIN, w=0.5, fill=NAVY)

    heads = ("产品名称", "型号", "序列号", "日期")
    cw = [46.0, 26.0, 34.0, 20.0]
    for ci, col_rows in enumerate(cols):
        x0 = MARGIN + ci * (A4_W - 2 * MARGIN) / 2.0
        # 表头
        xx = x0
        for h, w in zip(heads, cw):
            txt(d, xx, 31.5, h, load_font(6.8, bold=True), fill=NAVY)
            xx += w
        hline(d, x0, 35.5, x0 + sum(cw), w=0.3, fill=NAVY)
        # 数据行
        y = 37.5
        for (nm, mo, sn, dt) in col_rows:
            xx = x0
            for val, w in zip((nm, mo, sn, dt), cw):
                txt(d, xx, y, val, load_font(6.0), fill=INK)
                xx += w
            y += 6.1
        hline(d, x0, y - 1.5, x0 + sum(cw), w=0.3, fill=NAVY)

    txt(d, MARGIN, A4_H - MARGIN - 4.0, MANUFACTURER, load_font(7.0),
        fill=GREY, anchor="ls")
    path = os.path.join(OUT_DIR, "05_序列号清单.pdf")
    save_pdf_lossless([im], path, DPI)
    return path


# ============================================================
# PDF 输出：无损 FlateDecode
# ============================================================
# 为什么不用 PIL 自带的 PDF 保存：PIL 对 RGB 图固定走 DCTDecode(JPEG)，
# 且用 libjpeg 默认参数（质量 75 + 4:2:0 色度抽样）。实测彩色文字边缘最大
# 偏差 153、3.85% 像素劣化——印 47 mm 小标签有糊边风险。
# 而标签页大片白底+平色，zlib 无损压缩只要 0.35 MB/页，比 JPEG q95 的
# 2.08 MB 还小 6 倍。故自行写 PDF：FlateDecode + DeviceRGB，完全无损。

def _num(v: float) -> bytes:
    s = "{:.4f}".format(v).rstrip("0").rstrip(".")
    return s.encode("ascii") if s else b"0"


def save_pdf_lossless(pages: list[Image.Image], path: str, dpi: int) -> None:
    buf = io.BytesIO()
    offsets: dict[int, int] = {}
    buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    def obj(num: int, body: bytes) -> None:
        offsets[num] = buf.tell()
        buf.write(b"%d 0 obj\n" % num)
        buf.write(body)
        buf.write(b"\nendobj\n")

    n = len(pages)
    obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = b" ".join(b"%d 0 R" % (3 + i * 3) for i in range(n))
    obj(2, b"<< /Type /Pages /Count %d /Kids [ %s ] >>" % (n, kids))

    for i, im in enumerate(pages):
        page_no = 3 + i * 3
        cont_no, img_no = page_no + 1, page_no + 2
        wpt, hpt = im.width * 72.0 / dpi, im.height * 72.0 / dpi
        obj(page_no, (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [ 0 0 " + _num(wpt) + b" " + _num(hpt) + b" ] "
            b"/Resources << /XObject << /Im0 " + str(img_no).encode() + b" 0 R >> "
            b"/ProcSet [ /ImageC ] >> "
            b"/Contents " + str(cont_no).encode() + b" 0 R >>"))
        content = (b"q " + _num(wpt) + b" 0 0 " + _num(hpt) +
                   b" 0 0 cm /Im0 Do Q")
        obj(cont_no, b"<< /Length %d >>\nstream\n" % len(content) +
            content + b"\nendstream")
        data = zlib.compress(im.tobytes(), 9)
        obj(img_no, (
            b"<< /Type /XObject /Subtype /Image /Width " + str(im.width).encode() +
            b" /Height " + str(im.height).encode() +
            b" /ColorSpace /DeviceRGB /BitsPerComponent 8 "
            b"/Filter /FlateDecode /Length " + str(len(data)).encode() +
            b" >>\nstream\n" + data + b"\nendstream"))

    xref_off = buf.tell()
    total = 2 + 3 * n
    buf.write(b"xref\n0 %d\n" % (total + 1))
    buf.write(b"0000000000 65535 f \n")
    for k in range(1, total + 1):
        buf.write(b"%010d 00000 n \n" % offsets[k])
    buf.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (total + 1, xref_off))

    with open(path, "wb") as f:
        f.write(buf.getvalue())


def build() -> list[tuple[str, str, int]]:
    """生成 5 个独立 PDF 到一个文件夹，返回 (文件名, 说明, 张数)。"""
    os.makedirs(OUT_DIR, exist_ok=True)
    summary: list[tuple[str, str, int]] = []
    made: list[str] = []

    n = 0
    for prod in PRODUCTS:
        sns = sn_list(prod)
        for kind, drawer in (("标贴", draw_nameplate), ("合格证", draw_certificate)):
            n += 1
            pages: list[Image.Image] = []
            i = 0
            while i < len(sns):
                im, d = new_page()
                for (x, y) in SLOTS:
                    if i >= len(sns):
                        break
                    drawer(im, d, x, y, prod, sns[i])
                    i += 1
                pages.append(im)
            fn = "{:02d}_{}{}_{}_{}张.pdf".format(
                n, prod["name"], kind, prod["model"], prod["qty"])
            path = os.path.join(OUT_DIR, fn)
            save_pdf_lossless(pages, path, DPI)
            made.append(path)
            summary.append((fn, "{} {}（每页 {} 张）".format(
                prod["name"], kind, PER_PAGE), prod["qty"]))

    # 第 5 个：序列号清单
    p = write_sn_list_pdf()
    made.append(p)
    summary.append((os.path.basename(p), "序列号清单（两栏表格）", 80))

    # 清掉上一版合并 PDF，避免文件夹里出现新旧混放
    old = os.path.join(OUT_DIR, "标贴与合格证_打印版.pdf")
    if os.path.exists(old):
        os.remove(old)
        print("已移除旧合并版 :", old)

    build_logo(NAVY, 60.0).save(OUT_LOGO)
    write_sn_list()
    return summary


if __name__ == "__main__":
    pw, ph = A4_W - 2 * MARGIN, A4_H - 2 * MARGIN
    print("A4 可印区域 {:.0f}×{:.0f} mm（四边 {:.0f} mm 安全边）".format(pw, ph, MARGIN))
    print("标签 {:.0f}×{:.0f} mm 正方形".format(LABEL, LABEL))
    print("横向 {} 张：{:.0f}+{:.0f}×{} = {:.0f} mm → 宽度用满 {:.0f}%".format(
        COLS, LABEL * COLS, H_GAP, COLS - 1, LABEL * COLS + H_GAP * (COLS - 1),
        100 * (LABEL * COLS + H_GAP * (COLS - 1)) / pw))
    print("纵向 {} 张：{:.0f}+{:.0f}×{} = {:.0f} mm → 高度用满 {:.0f}%".format(
        ROWS, LABEL * ROWS, V_GAP, ROWS - 1, LABEL * ROWS + V_GAP * (ROWS - 1),
        100 * (LABEL * ROWS + V_GAP * (ROWS - 1)) / ph))
    print("每页 {} 张".format(PER_PAGE))
    print("序列号起始序号 {}，日期前缀 {}".format(SN_SEQ_START, PRODUCE_DATE[2:4] + PRODUCE_DATE[5:7]))
    print("二维码：ECC-{}，编码内容=型号+编号（如 {}）".format(
        QR_ECC, qr_payload(PRODUCTS[0], sn_list(PRODUCTS[0])[0])))
    print("-" * 64)
    for fn, desc, cnt in build():
        print("  {:<44} {:<26} {:>3} 张".format(fn, desc, cnt))
    print("-" * 64)
    if OVERFLOW:
        print("文字超宽 {} 处：".format(len(OVERFLOW)))
        for o in OVERFLOW[:10]:
            print("   ", o)
        sys.exit(1)
    print("文字宽度自检 : 全部通过")
    print("输出目录     :", OUT_DIR)
    print("logo 素材    :", OUT_LOGO)
    print("SN 清单      :", write_sn_list())
