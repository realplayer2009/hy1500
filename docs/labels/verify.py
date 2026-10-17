#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版面自检
========
1. 5 个 PDF 的结构（页数/尺寸/A4/无损压缩）
2. 逐格版面：内容存在、左右/下间隙无溢出、内容不触边框
3. **二维码反解**：从渲染好的页面里裁出二维码区域、二值化、按模块采样、
   用 qr.qr_decode() 解回序列号，与应有的 SN 逐一比对。
   这是端到端测试——印刷模糊、模块尺寸不足、位置偏移都会在这里暴露。
4. 字形覆盖、序列号唯一性
"""
import os
import re
import sys

from PIL import Image

sys.path.insert(0, "/Users/han24-m5air/gitw/hy1500-1/docs/labels")
import make_labels as M
import qr as Q

PX = M.PX
OUT = M.OUT_DIR
fails = []


def px(v):
    return int(round(v * PX))


def ink_bbox(g, box):
    """box=(l,t,r,b) 单位 mm；返回该区域内墨迹边界框或 None。"""
    return g.crop((px(box[0]), px(box[1]), px(box[2]), px(box[3]))) \
             .point(lambda v: 255 if v < 200 else 0).getbbox()


def ok(cond, msg):
    print("  [{}] {}".format("PASS" if cond else "FAIL", msg))
    if not cond:
        fails.append(msg)


# ---------- 二维码几何（与 make_labels.build_qr 保持一致）----------
def qr_geom(sn, prod=None):
    payload = M.qr_payload(prod, sn) if prod else sn
    n = len(Q.qr_matrix(payload, M.QR_ECC)[0])
    mod_px = max(2, M.mm(M.QR_SIZE) // n)
    return n, mod_px, n * mod_px, n * mod_px * M.MM_PER_PX


def read_qr_from_page(g, x, y, sn, prod=None):
    """从页面灰度图 g 中，标签 (x,y) 处的二维码区域解出矩阵。"""
    n, mod_px, code_px, code_mm = qr_geom(sn, prod)
    cx = x + M.LABEL / 2.0
    x0 = px(cx) - code_px // 2
    y0 = px(y + M.QR_TOP)
    if x0 < 0 or y0 < 0 or x0 + code_px > g.width or y0 + code_px > g.height:
        return None
    m = []
    for r in range(n):
        row = []
        for c in range(n):
            sx = x0 + c * mod_px + mod_px // 2
            sy = y0 + r * mod_px + mod_px // 2
            # 取 3×3 邻域中值，抗单点噪点
            vals = [g.getpixel((sx + dx, sy + dy))
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            row.append(sorted(vals)[4] < 160)
        m.append(row)
    return m


# ============================================================
print("=" * 68)
print("1) 5 个 PDF 结构")
print("=" * 68)
pdfs = sorted(f for f in os.listdir(OUT) if f.endswith(".pdf"))
ok(len(pdfs) == 5, "输出目录共 {} 个 PDF（期望 5）".format(len(pdfs)))
expect_pages = {"01": 1, "02": 1, "03": 3, "04": 3, "05": 1}
total_bytes = 0
for fn in pdfs:
    raw = open(os.path.join(OUT, fn), "rb").read()
    total_bytes += len(raw)
    n = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    mb = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    w, h = (float(mb.group(1)) * 25.4 / 72, float(mb.group(2)) * 25.4 / 72) if mb else (0, 0)
    key = fn[:2]
    exp = expect_pages.get(key)
    a4 = abs(w - 210) < 1 and abs(h - 297) < 1
    lossless = b"/FlateDecode" in raw and b"/DCTDecode" not in raw
    print("  {:<46} {:>9,} B  页数 {}  {:.0f}×{:.0f}mm  {}".format(
        fn, len(raw), n, w, h,
        "PASS" if (n == exp and a4 and lossless) else "FAIL"))
    if not (n == exp and a4 and lossless):
        fails.append("{} 结构异常".format(fn))
ok(True, "合计 {:,} bytes".format(total_bytes))

# ============================================================
print()
print("=" * 68)
print("2) 逐格版面（4 类文书，每页 20 格全画）")
print("=" * 68)
for prod in M.PRODUCTS:
    for kind, drawer in (("标贴", M.draw_nameplate), ("合格证", M.draw_certificate)):
        im, d = M.new_page()
        sns = M.sn_list(prod)
        for i, (x, y) in enumerate(M.SLOTS):
            if i >= len(sns):
                break
            drawer(im, d, x, y, prod, sns[i])
        g = im.convert("L")
        problems = []
        n = min(len(sns), 20)
        for i, (x, y) in enumerate(M.SLOTS[:n]):
            interior = (x + 2.5, y + 2.5, x + M.LABEL - 2.5, y + M.LABEL - 2.5)
            ib = ink_bbox(g, interior)
            if ib is None:
                problems.append("格{} 无内容".format(i + 1))
                continue
            if i % M.COLS != M.COLS - 1:
                if ink_bbox(g, (x + M.LABEL + 0.6, y + 1.0,
                                x + M.LABEL + M.H_GAP - 0.6, y + M.LABEL - 1.0)):
                    problems.append("格{} 右溢出".format(i + 1))
            elif x + M.LABEL > M.A4_W - M.MARGIN + 0.01:
                problems.append("格{} 超出可印右边界".format(i + 1))
            if i // M.COLS != M.ROWS - 1:
                if ink_bbox(g, (x + 1.0, y + M.LABEL + 0.6,
                                x + M.LABEL - 1.0, y + M.LABEL + M.V_GAP - 0.6)):
                    problems.append("格{} 下溢出".format(i + 1))
            else:
                if ink_bbox(g, (x + 1.0, y + M.LABEL + 0.6,
                                x + M.LABEL - 1.0, M.A4_H - M.MARGIN)):
                    problems.append("格{} 下溢出至页边".format(i + 1))
            # 内容离边框线的真实净距（不是固定内缩线）：裁掉边框本身后量墨迹边界。
            # frame() 的 outline 宽 0.5mm 且画在边界内侧，故内缩 0.55mm 刚好排除它；
            # 早先内缩 0.9mm 会把这 0.35mm 也算进"空隙"，比真实边框严，导致误报。
            cb = ink_bbox(g, (x + 0.55, y + 0.55, x + M.LABEL - 0.55, y + M.LABEL - 0.55))
            if cb is None:
                problems.append("格{} 边框内无内容".format(i + 1))
            else:
                cw_px = px(M.LABEL - 1.1)
                ch_px = px(M.LABEL - 1.1)
                cl = cb[0] * M.MM_PER_PX          # 离左边框的墨迹间距 mm
                ct = cb[1] * M.MM_PER_PX
                cr = (cw_px - cb[2]) * M.MM_PER_PX
                cbm = (ch_px - cb[3]) * M.MM_PER_PX
                if min(cl, ct, cr, cbm) < 1.2:
                    problems.append("格{} 净距 {:.1f}/{:.1f}/{:.1f}/{:.1f} mm".format(
                        i + 1, cl, ct, cr, cbm))
        tag = "{} {}".format(prod["name"], kind)
        if problems:
            fails.append("版面: " + "；".join(problems[:4]))
            print("  [FAIL] {:<20} {}".format(tag, "；".join(problems[:6])))
        else:
            print("  [PASS] {:<20} {} 格内容完整，间隙无溢出".format(tag, n))

# ============================================================
print()
print("=" * 68)
print("3) 二维码反解（从渲染页面裁出 → 二值化 → 解回序列号）")
print("=" * 68)
for prod in M.PRODUCTS:
    im, d = M.new_page()
    sns = M.sn_list(prod)
    for i, (x, y) in enumerate(M.SLOTS):
        if i >= len(sns):
            break
        M.draw_nameplate(im, d, x, y, prod, sns[i])
    g = im.convert("L")
    bad = []
    mods = []
    for i, (x, y) in enumerate(M.SLOTS[:len(sns)]):
        sn = sns[i]
        n, mod_px, code_px, code_mm = qr_geom(sn, prod)
        mods.append(code_mm / n)
        m = read_qr_from_page(g, x, y, sn, prod)
        if m is None:
            bad.append("格{} 二维码越界".format(i + 1))
            continue
        try:
            back = Q.qr_decode(m, M.QR_ECC)
        except Exception as e:
            bad.append("格{} 解码异常 {}".format(i + 1, e))
            continue
        if back != M.qr_payload(prod, sn):
            bad.append("格{} 解出 {} ≠ {}".format(i + 1, back, M.qr_payload(prod, sn)))
    avg_mod = sum(mods) / len(mods)
    if bad:
        fails.append("二维码: " + "；".join(bad[:4]))
        print("  [FAIL] {:<20} {}".format(prod["model"], "；".join(bad[:4])))
    else:
        print("  [PASS] {:<20} {} 个二维码全部解回正确序列号".format(
            prod["model"], len(sns)))
    print("         模块尺寸 {:.3f} mm（≥0.5 mm 才好扫）".format(avg_mod))


def quiet_zone_ink(g, x, y, sn, prod):
    """量二维码四周 4 模块静区内的墨点数。规范要求静区为纯白，混进深色
    墨迹会让微信等 App 的码框定位直接失败——这是实际发生过的事故：
    版面把分隔线和编号排得离码太近，反解脚本按理论坐标采样照样全过，
    但手机扫不出来。故单列此项，四向必须全零。"""
    n, mod_px, code_px, code_mm = qr_geom(sn, prod)
    module = code_mm / n
    qz = 4 * module
    cx = x + M.LABEL / 2.0
    left, right = cx - code_mm / 2, cx + code_mm / 2
    top, bot = y + M.QR_TOP, y + M.QR_TOP + code_mm
    sides = (("上", left + 0.5, top - qz, right - 0.5, top),
             ("下", left + 0.5, bot, right - 0.5, bot + qz),
             ("左", left - qz, top + 0.5, left, bot - 0.5),
             ("右", right, top + 0.5, right + qz, bot - 0.5))
    out = []
    for name, a, b, c, e in sides:
        reg = g.crop((px(a), px(b), px(c), px(e)))
        out.append((name, sum(1 for v in reg.get_flattened_data() if v < 200)))
    return out, qz


print()
print("=" * 68)
print("3b) 二维码静区（四周 4 模块必须纯白，否则手机 App 定位不到码）")
print("=" * 68)
for prod in M.PRODUCTS:
    im, d = M.new_page()
    sns = M.sn_list(prod)
    for i, (x, y) in enumerate(M.SLOTS):
        if i >= len(sns):
            break
        M.draw_nameplate(im, d, x, y, prod, sns[i])
    g = im.convert("L")
    worst = {}
    dirty = []
    for i, (x, y) in enumerate(M.SLOTS[:len(sns)]):
        sides, qz = quiet_zone_ink(g, x, y, sns[i], prod)
        for name, cnt in sides:
            worst[name] = max(worst.get(name, 0), cnt)
            if cnt:
                dirty.append("格{}{}侧 {} 墨点".format(i + 1, name, cnt))
    if dirty:
        fails.append("静区: " + "；".join(dirty[:4]))
        print("  [FAIL] {:<20} {}".format(prod["model"], "；".join(dirty[:4])))
    else:
        print("  [PASS] {:<20} 四向静区全净（各需 {:.2f} mm，最多墨点 {}/{}/{}/{}）".format(
            prod["model"], qz, worst.get("上", 0), worst.get("下", 0),
            worst.get("左", 0), worst.get("右", 0)))

# ============================================================
print()
print("=" * 68)
print("4) 字形覆盖 / 序列号唯一")
print("=" * 68)
probe = ("变压器加热控制器合格证编号型号检验日期结论裕泰通四川新能源科技"
         "YTT-CR850A-2609-060＿")
missing = [c for c in set(probe)
           if M.load_font(10).getmask(c).size == (0, 0)]
ok(not missing, "探针 {} 字，缺字形 {} 个 {}".format(
    len(set(probe)), len(missing), missing if missing else "→ 全部可渲染"))

sns = [s for p in M.PRODUCTS for s in M.sn_list(p)]
ok(len(sns) == 80, "序列号总数 {} （期望 80）".format(len(sns)))
ok(len(set(sns)) == 80, "序列号去重 {} （期望 80）".format(len(set(sns))))
for p in M.PRODUCTS:
    print("  {:<12} {} … {} （{} 张）".format(
        p["model"], M.sn_list(p)[0], M.sn_list(p)[-1], p["qty"]))

print()
print("=" * 68)
print("总体判定: {}".format("PASS" if not fails else "FAIL（{} 项）".format(len(fails))))
print("=" * 68)
sys.exit(1 if fails else 0)
