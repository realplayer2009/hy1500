#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 往返几何校验
================
用 LibreOffice(pdfium) 把交付的 5 个 PDF 逐一渲成 PNG，再与原始渲染比对：
  ① 页数是否一致（pdfium 能否解析我们的手写 PDF）
  ② 页面尺寸（A4）
  ③ 4×5 网格几何：每格墨迹边界框位置是否保持
  ④ 二维码是否仍能反解（印刷链路端到端）
这是不依赖肉眼的最后一关：能抓住 cm 矩阵写错、图像放错位置、缩放不对等问题。
"""
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, "/Users/han24-m5air/gitw/hy1500-1/docs/labels")
import make_labels as M
import qr as Q

OUT = M.OUT_DIR
LO_DIR = "/tmp/lo_rt5"
CLI = ("/Applications/DeepSeek Harness.app/Contents/Resources/app.asar.unpacked/"
       "dsh/node_modules/@deepseek-ai/libreoffice-kit/lib/cli.js")
NODE = ("/Applications/DeepSeek Harness.app/Contents/Resources/runtime/"
        "primary-runtime/dependencies/node/bin/node")
fails = []

if os.path.isdir(LO_DIR):
    subprocess.run(["rm", "-rf", LO_DIR], check=True)

print("=" * 70)
print("PDF 往返几何校验（LibreOffice pdfium 独立渲染）")
print("=" * 70)

# 重新渲染原始页面
ref = {}
for prod in M.PRODUCTS:
    sns = M.sn_list(prod)
    for kind, drawer in (("标贴", M.draw_nameplate), ("合格证", M.draw_certificate)):
        fn = "{:02d}_{}{}_{}_{}张.pdf".format(
            (0 if prod["key"] == "ctrl" else 2) + (1 if kind == "标贴" else 2),
            prod["name"], kind, prod["model"], prod["qty"])
        pgs = []
        i = 0
        while i < len(sns):
            im, d = M.new_page()
            for (x, y) in M.SLOTS:
                if i >= len(sns):
                    break
                drawer(im, d, x, y, prod, sns[i])
                i += 1
            pgs.append((im, sns[i - len(M.SLOTS):i] if i >= len(M.SLOTS) else sns[:i]))
        ref[fn] = pgs

SC = 2   # 300 DPI → 150 DPI


def prod_of(fn):
    for p in M.PRODUCTS:
        if p["model"] in fn:
            return p
    return M.PRODUCTS[0]


def qr_geom(sn, prod=None):
    payload = M.qr_payload(prod, sn) if prod else sn
    n = len(Q.qr_matrix(payload, M.QR_ECC)[0])
    mod_px = max(2, M.mm(M.QR_SIZE) // n)
    return n, mod_px, n * mod_px


for fn in sorted(os.listdir(OUT)):
    if not fn.endswith(".pdf") or fn not in ref:
        continue
    path = os.path.join(OUT, fn)
    d2 = "/tmp/lo_one5"
    if os.path.isdir(d2):
        subprocess.run(["rm", "-rf", d2], check=True)
    r = subprocess.run([NODE, CLI, "render", "--input", path,
                        "--output-dir", d2, "--pages", "all", "--dpi", "150"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] {} LibreOffice 渲染失败".format(fn))
        fails.append(fn + " 渲染失败")
        continue
    import json
    info = json.loads(r.stdout)
    print()
    print("--- {} ---".format(fn))
    npages = info.get("pageCount", 0)
    exp = len(ref[fn])
    print("  pdfium 解析页数 {} （期望 {}） {}".format(
        npages, exp, "PASS" if npages == exp else "FAIL"))
    if npages != exp:
        fails.append(fn + " 页数不符")
    mf = info.get("missingFonts", [])
    print("  missingFonts {} {}".format(mf, "PASS" if not mf else "FAIL"))
    if mf:
        fails.append(fn + " 缺字体")

    # 逐页几何 + 二维码
    geo_bad = qr_bad = fid_bad = 0
    for pi, (im0, sns0) in enumerate(ref[fn]):
        lo_path = os.path.join(d2, "page-{:04d}.png".format(pi + 1))
        if not os.path.exists(lo_path):
            continue
        lo = Image.open(lo_path).convert("RGB")
        mine = im0.resize((im0.width // SC, im0.height // SC), Image.BOX).convert("RGB")
        if lo.size != mine.size:
            fails.append(fn + " 页{} 尺寸不符".format(pi + 1))
            continue
        g1, g2 = mine.convert("L"), lo.convert("L")
        k = M.PX / SC          # 300 DPI → 150 DPI 的像素/毫米

        # ① 平色区精确性
        # 不能硬编码采样点：版面一改，某个点就可能落到 logo 图案或抗锯齿
        # 边缘上，pdfium 的重采样与本地降采样自然有差异，会误报。
        # 改为自适应——在本地渲染图上扫一片候选点，只取 7×7 邻域完全
        # 均匀（真正的纯色区）的那些点，再要求 pdfium 在同样位置
        # 精确复现。这样查的是"平色有没有被搞花"，与版面细节无关。
        for (x, y) in M.SLOTS[:6]:
            for fx in range(1, 47, 3):
                for fy in range(1, 47, 3):
                    sx = int((x + fx) * k)
                    sy = int((y + fy) * k)
                    if sx < 3 or sy < 3 or sx + 3 >= mine.width or sy + 3 >= mine.height:
                        continue
                    vals = [mine.getpixel((sx + dx, sy + dy))
                            for dx in (-2, -1, 0, 1, 2)
                            for dy in (-2, -1, 0, 1, 2)]
                    if len(set(vals)) != 1:
                        continue          # 非纯色区，跳过
                    c2 = lo.getpixel((sx, sy))
                    if abs(vals[0][0] - c2[0]) + abs(vals[0][1] - c2[1]) \
                            + abs(vals[0][2] - c2[2]) > 6:
                        fid_bad += 1

        # ② 每格墨迹边界框
        for (x, y) in M.SLOTS[:len(sns0)]:
            box = (x + 0.9, y + 0.9, x + M.LABEL - 0.9, y + M.LABEL - 0.9)
            b1 = g1.crop((int(box[0] * k), int(box[1] * k),
                          int(box[2] * k), int(box[3] * k))).point(
                lambda v: 255 if v < 200 else 0).getbbox()
            b2 = g2.crop((int(box[0] * k), int(box[1] * k),
                          int(box[2] * k), int(box[3] * k))).point(
                lambda v: 255 if v < 200 else 0).getbbox()
            if b1 is None or b2 is None:
                geo_bad += 1
                continue
            if max(abs(b1[0] - b2[0]), abs(b1[1] - b2[1]),
                   abs(b1[2] - b2[2]), abs(b1[3] - b2[3])) > 4:
                geo_bad += 1

        # ③ 二维码反解（仅标贴）
        # 不能在 150 DPI 上用整数步长采样：v2 有 25 个模块，code_px/2/25 的
        # 整数除法会把网格压缩，越采越偏。改为先在渲染图里量出二维码的
        # 真实墨迹边界框，按实际宽度算浮点步长。
        if "标贴" in fn:
            for ci, (x, y) in enumerate(M.SLOTS[:len(sns0)]):
                sn = sns0[ci]
                pr = prod_of(fn)
                n, mod_px, code_px = qr_geom(sn, pr)
                cxm = x + M.LABEL / 2.0
                reg = (cxm - M.QR_SIZE / 2 - 1.0, y + 22.7,
                       cxm + M.QR_SIZE / 2 + 1.0, y + 22.7 + M.QR_SIZE + 0.3)
                crop = g2.crop((int(reg[0] * k), int(reg[1] * k),
                                int(reg[2] * k), int(reg[3] * k)))
                bb = crop.point(lambda v: 255 if v < 160 else 0).getbbox()
                if bb is None:
                    qr_bad += 1
                    continue
                bw = bb[2] - bb[0]
                if abs(bw - (bb[3] - bb[1])) > 3 or bw < n:
                    qr_bad += 1          # 不是正方形或尺寸不足，说明没框准
                    continue
                step = bw / float(n)
                mmx = []
                for rr in range(n):
                    row = []
                    for cc in range(n):
                        sx = int(bb[0] + (cc + 0.5) * step)
                        sy = int(bb[1] + (rr + 0.5) * step)
                        row.append(crop.getpixel((sx, sy)) < 160)
                    mmx.append(row)
                try:
                    if Q.qr_decode(mmx, M.QR_ECC) != M.qr_payload(pr, sn):
                        qr_bad += 1
                except Exception:
                    qr_bad += 1

    print("  平色区超差 {} 处  网格几何超差 {} 格  二维码反解失败 {} 个".format(
        fid_bad, geo_bad, qr_bad))
    if fid_bad:
        fails.append(fn + " 平色区超差")
    if geo_bad:
        fails.append(fn + " 网格几何超差")
    if qr_bad:
        fails.append(fn + " 二维码反解失败")

print()
print("=" * 70)
print("总体判定: {}".format("PASS" if not fails else "FAIL（{} 项）".format(len(fails))))
print("=" * 70)
sys.exit(1 if fails else 0)
