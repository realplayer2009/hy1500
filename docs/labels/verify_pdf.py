#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付文件端到端校验（逐字节级）
============================
不校验内存里的渲染结果，而是解析最终 PDF 文件本身：
  1. 结构完整性：文件头 / xref 偏移是否真指向对象 / trailer / %%EOF
  2. 每页图像流解压后，与重新渲染的原始页面**逐字节**比对（无损要求完全相同）
  3. 页数、MediaBox、分辨率、压缩方式
覆盖全部 5 个 PDF。
"""
import os
import re
import sys
import zlib

sys.path.insert(0, "/Users/han24-m5air/gitw/hy1500-1/docs/labels")
import make_labels as M

OUT = M.OUT_DIR
fails = []


def ok(cond, msg):
    print("  [{}] {}".format("PASS" if cond else "FAIL", msg))
    if not cond:
        fails.append(msg)


def extract_image(raw, objno):
    s = raw.find(b"stream", raw.find(b"%d 0 obj" % objno)) + len(b"stream")
    if raw[s:s + 2] == b"\r\n":
        s += 2
    elif raw[s:s + 1] in (b"\n", b"\r"):
        s += 1
    e = raw.find(b"endstream", s)
    return raw[s:e].rstrip(b"\r\n")


# 重新渲染全部页面作为基准：(文件名, [(kind, im), ...])
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
            pgs.append(im)
        ref[fn] = pgs
# 第 5 个文件单独校验（表格页，不做逐字节比对，只查结构）
LIST_PDF = "05_序列号清单.pdf"

print("=" * 70)
print("交付 PDF 端到端校验（逐字节级，覆盖 5 个文件）")
print("=" * 70)

total = 0
for fn in sorted(os.listdir(OUT)):
    if not fn.endswith(".pdf"):
        continue
    path = os.path.join(OUT, fn)
    raw = open(path, "rb").read()
    total += len(raw)
    print()
    print("--- {} ({:,} bytes) ---".format(fn, len(raw)))
    ok(raw.startswith(b"%PDF-1."), "文件头 %PDF-1.x")
    ok(raw.rstrip().endswith(b"%%EOF"), "以 %%EOF 结尾")
    ok(b"/FlateDecode" in raw, "使用 FlateDecode 无损压缩")
    ok(b"/DCTDecode" not in raw, "不含 DCTDecode（无 JPEG 有损）")

    m = re.search(rb"startxref\s+(\d+)\s+%%EOF", raw)
    xo = int(m.group(1)) if m else -1
    ok(xo > 0 and raw[xo:xo + 4] == b"xref",
       "startxref 偏移 {} 真指向 xref 表".format(xo))
    xr = raw[xo:]
    entries = re.findall(rb"(\d{10}) (\d{5}) (n|f) ?\n", xr)
    bad = sum(1 for i, (off, gen, t) in enumerate(entries)
              if t == b"n" and not re.match(rb"%d 0 obj" % i, raw[int(off):int(off) + 12]))
    ok(bad == 0, "xref 共 {} 条在用对象，偏移全部正确".format(
        sum(1 for e in entries if e[2] == b"n")))

    n_pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    if fn in ref:
        ok(n_pages == len(ref[fn]),
           "页数 {} == 渲染页数 {}".format(n_pages, len(ref[fn])))
    ok(len(boxes) == n_pages, "每页都有 MediaBox")
    for w, h in set(boxes):
        wmm, hmm = float(w) * 25.4 / 72, float(h) * 25.4 / 72
        ok(abs(wmm - 210) < 0.5 and abs(hmm - 297) < 0.5,
           "页面 {:.2f}×{:.2f} mm = A4".format(wmm, hmm))

    # 逐字节比对（仅标贴/合格证四个文件）
    if fn in ref:
        img_objs = re.findall(
            rb"(\d+) 0 obj\s*<<[^>]*?/Subtype /Image(.*?)>>\s*stream\r?\n", raw, re.S)
        ok(len(img_objs) == n_pages,
           "图像对象数 {} == 页数 {}".format(len(img_objs), n_pages))
        all_exact = True
        for idx, (objno, _) in enumerate(img_objs):
            try:
                dec = zlib.decompress(extract_image(raw, int(objno)))
            except Exception as ex:
                print("    页{} 解压失败: {}".format(idx + 1, ex))
                all_exact = False
                continue
            if dec != ref[fn][idx].tobytes():
                all_exact = False
                print("    页{} 与原始渲染不一致".format(idx + 1))
        ok(all_exact, "全部页面解压后与原始渲染逐字节一致")

print()
print("=" * 70)
print("5 个文件合计 {:,} bytes".format(total))
print("总体判定: {}".format("PASS" if not fails else "FAIL（{} 项）".format(len(fails))))
print("=" * 70)
sys.exit(1 if fails else 0)
