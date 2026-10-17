#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量出标签内每段文字的实际宽度，找出超宽的行。"""
import sys

from PIL import ImageFont

sys.path.insert(0, "/Users/han24-m5air/gitw/hy1500-1/docs/labels")
import make_labels as M

DPI = M.DPI
MM_PER_PX = 25.4 / DPI          # getlength 返回像素，按 300 DPI 换算成 mm


def width_mm(s, pt, bold=False, serif=False):
    f = M.load_font(pt, bold=bold, serif=serif)
    return f.getlength(s) * MM_PER_PX


LABEL = M.LABEL
PAD = 3.2
VALUE_X = 15.0
avail = LABEL - PAD - VALUE_X
print("标签内字段值可用宽度: {:.1f} mm（起点 {:.1f}，右边距 {:.1f}）".format(
    avail, VALUE_X, PAD))
print()

samples = [
    ("标贴-产品名称", "变压器加热控制器", 12.5, True, False, LABEL - 2 * PAD),
    ("标贴-型号", "YTT-TC1500", 10.0, False, False, avail),
    ("标贴-编号 SN", "YTT-TC1500-2610-001", 10.0, True, False, avail),
    ("标贴-编号 SN", "YTT-CR850A-2610-001", 10.0, True, False, avail),
    ("标贴-日期", "2026-10-17", 10.0, False, False, avail),
    ("标贴-品牌", M.BRAND, 14, True, False, LABEL - 2 * PAD - 14),
    ("标贴-角标", "合格品", 7.2, False, False, 12.0),
    ("标贴-厂家", M.MANUFACTURER, 6.8, False, False, LABEL - 2 * PAD),
    ("合格证-标题", "合 格 证", 15, True, True, LABEL - 14),
    ("合格证-品名", "变压器加热控制器", 8.0, False, False, avail),
    ("合格证-型号", "YTT-TC1500", 8.4, False, False, avail),
    ("合格证-编号", "YTT-TC1500-2610-001", 9.2, True, False, avail),
    ("合格证-日期", "2026-10-17", 8.4, False, False, avail),
    ("合格证-结论", "合　格", 10, True, False, LABEL - 2 * PAD - 6),
    ("合格证-检验员", "＿" * 6, 8.4, False, False, avail),
    ("合格证-脚注", "本产品经检验合格，准予出厂", 6.0, False, False, LABEL - 2 * PAD),
]

worst = 0.0
for name, s, pt, bold, serif, limit in samples:
    w = width_mm(s, pt, bold, serif)
    over = w - limit
    if over > worst:
        worst = over
    print("  {:<16} {:>5.1f} mm / 限 {:>5.1f}   {}".format(
        name, w, limit, "OK" if over <= 0 else "超宽 {:.1f} mm".format(over)))

print()
print("最大超宽: {:.1f} mm".format(worst))
print()
for pt in (10, 9.5, 9, 8.5, 8, 7.5, 7):
    w = width_mm("YTT-TC1500-2610-001", pt, bold=True)
    print("  SN {:>4} pt → {:.1f} mm {}".format(
        pt, w, "放得下" if w <= avail else "放不下"))
