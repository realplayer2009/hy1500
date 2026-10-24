#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DWG(DXF) → SVG 直转器：如实整理现场原图，不重新排版、不改内容。

与 make_zuoan_wiring.py 的区别：那个是按原图风格重新设计内容（已作废删除），
本脚本只做格式转换——把 EPLAN 生成的 DWG 端子接线图转成 SVG，坐标、端子号、
回路号、电缆编号、标题栏全部照抄原图。

用法:
    python3 dwg2svg.py <in.dxf> <out.svg> [x0 y0 x1 y1]
    python3 dwg2svg.py --all            # 转 /tmp/zw_drag 下全部原图
"""
import sys
import os
import ezdxf

FONT = ("Heiti SC, STHeiti, Hiragino Sans GB, Songti SC, "
        "Hiragino Sans, Arial Unicode MS, sans-serif")
SCALE = 3.0          # DXF mm → SVG px
MIN_LEN = 250.0      # 判定图框的长线段阈值


# ---------------------------------------------------------------- 实体扁平化
def flatten(msp, depth=0):
    """递归展开 INSERT 块，返回普通实体列表（EPLAN 的表格网格全在块里）。"""
    out = []
    if depth > 10:
        return out
    for e in msp:
        t = e.dxftype()
        if t == "INSERT":
            try:
                for v in e.virtual_entities():
                    out.extend(flatten([v], depth + 1))
            except Exception:
                pass
        else:
            out.append(e)
    return out


# ---------------------------------------------------------------- 图框探测
def find_frames(ents):
    """用长横线/长竖线配对找出所有图框，返回 [(x0,y0,x1,y1), ...]。"""
    H, V = [], []
    for e in ents:
        if e.dxftype() != "LINE":
            continue
        try:
            a, b = e.dxf.start, e.dxf.end
        except Exception:
            continue
        if abs(a.y - b.y) < 0.02 and abs(a.x - b.x) > MIN_LEN:
            H.append((a.y, min(a.x, b.x), max(a.x, b.x)))
        elif abs(a.x - b.x) < 0.02 and abs(a.y - b.y) > MIN_LEN:
            V.append((a.x, min(a.y, b.y), max(a.y, b.y)))
    frames = []
    for i in range(len(H)):
        for j in range(i + 1, len(H)):
            y1, ax0, ax1 = H[i]
            y2, bx0, bx1 = H[j]
            if ax0 > bx0 or ax1 < bx1:
                continue
            for p in range(len(V)):
                for q in range(len(V)):
                    if p == q:
                        continue
                    x1, ay0, ay1 = V[p]
                    x2, by0, by1 = V[q]
                    if (abs(x1, ) if False else True) and (
                            abs(ax0 - x1) < 1.0 and abs(ax1 - x2) < 1.0
                            and abs(bx0 - x1) < 1.0 and abs(bx1 - x2) < 1.0
                            and abs(ay0 - min(y1, y2)) < 1.0
                            and abs(ay1 - max(y1, y2)) < 1.0
                            and abs(by0 - min(y1, y2)) < 1.0
                            and abs(by1 - max(y1, y2)) < 1.0):
                        frames.append((min(x1, x2), min(y1, y2),
                                       max(x1, x2), max(y1, y2)))
    # 去重（同框可能被多条线重复命中）
    uniq = []
    for f in frames:
        if not any(abs(f[0] - g[0]) < 2 and abs(f[1] - g[1]) < 2
                   and abs(f[2] - g[2]) < 2 and abs(f[3] - g[3]) < 2
                   for g in uniq):
            uniq.append(f)
    return sorted(uniq, key=lambda f: (f[1], f[0]))


# ---------------------------------------------------------------- 文字提取
def txt_of(e):
    t = e.dxftype()
    try:
        if t == "TEXT":
            return e.dxf.text, e.dxf.insert, e.dxf.height, e.dxf.rotation
        if t == "MTEXT":
            s = e.plain_text()
            s = s.replace("\n", " ").replace("\r", " ")
            return s, e.dxf.insert, e.dxf.char_height, e.dxf.rotation
    except Exception:
        return None
    return None


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


# ---------------------------------------------------------------- 转换
def convert(dxf_path, svg_path, frame=None, title=""):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.layouts.get("Model")
    ents = flatten(msp)

    if frame is None:
        frames = find_frames(ents)
        if not frames:
            xs, ys = [], []
            for e in ents:
                if e.dxftype() == "LINE":
                    a, b = e.dxf.start, e.dxf.end
                    xs += [a.x, b.x]
                    ys += [a.y, b.y]
            frame = (min(xs), min(ys), max(xs), max(ys))
        else:
            frame = frames[0]
    x0, y0, x1, y1 = frame
    pad = 6.0
    x0 -= pad
    y0 -= pad
    x1 += pad
    y1 += pad
    W = (x1 - x0) * SCALE
    H = (y1 - y0) * SCALE

    def px(x):
        return (x - x0) * SCALE

    def py(y):
        return (y1 - y) * SCALE          # DXF y 向上 → SVG y 向下

    parts = []
    n_line = n_txt = n_circ = n_other = 0
    for e in ents:
        t = e.dxftype()
        try:
            if t == "LINE":
                a, b = e.dxf.start, e.dxf.end
                if not (min(a.x, b.x) <= x1 and max(a.x, b.x) >= x0
                        and min(a.y, b.y) <= y1 and max(a.y, b.y) >= y0):
                    continue
                lw = 0.4
                try:
                    lw = float(e.dxf.lineweight) / 100.0
                    if lw <= 0:
                        lw = 0.4
                except Exception:
                    pass
                parts.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" '
                             'stroke="#000" stroke-width="%.2f"/>'
                             % (px(a.x), py(a.y), px(b.x), py(b.y), lw))
                n_line += 1
            elif t in ("LWPOLYLINE", "POLYLINE"):
                pts = []
                if t == "LWPOLYLINE":
                    pts = [(p[0], p[1]) for p in e.get_points()]
                else:
                    pts = [(v.dxf.location.x, v.dxf.location.y)
                           for v in e.vertices]
                if not pts:
                    continue
                if not (min(p[0] for p in pts) <= x1
                        and max(p[0] for p in pts) >= x0
                        and min(p[1] for p in pts) <= y1
                        and max(p[1] for p in pts) >= y0):
                    continue
                d = "M " + " L ".join("%.2f %.2f" % (px(p[0]), py(p[1]))
                                      for p in pts)
                if e.closed:
                    d += " Z"
                lw = 0.4
                try:
                    lw = max(0.3, float(e.dxf.lineweight) / 100.0)
                except Exception:
                    pass
                parts.append('<path d="%s" fill="none" stroke="#000" '
                             'stroke-width="%.2f"/>' % (d, lw))
                n_line += 1
            elif t == "CIRCLE":
                c, r = e.dxf.center, e.dxf.radius
                if not (c.x + r >= x0 and c.x - r <= x1
                        and c.y + r >= y0 and c.y - r <= y1):
                    continue
                parts.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" '
                             'stroke="#000" stroke-width="0.6"/>'
                             % (px(c.x), py(c.y), r * SCALE))
                n_circ += 1
            elif t == "ARC":
                c, r = e.dxf.center, e.dxf.radius
                sa, ea = e.dxf.start_angle, e.dxf.end_angle
                import math
                xa, ya = px(c.x + r * math.cos(math.radians(sa))), \
                    py(c.y + r * math.sin(math.radians(sa)))
                xb, yb = px(c.x + r * math.cos(math.radians(ea))), \
                    py(c.y + r * math.sin(math.radians(ea)))
                large = 1 if (ea - sa) % 360 > 180 else 0
                parts.append('<path d="M %.2f %.2f A %.2f %.2f 0 %d 0 %.2f '
                             '%.2f" fill="none" stroke="#000" '
                             'stroke-width="0.6"/>'
                             % (xa, ya, r * SCALE, r * SCALE, large, xb, yb))
                n_other += 1
            elif t in ("TEXT", "MTEXT"):
                r = txt_of(e)
                if not r:
                    continue
                s, ip, h, rot = r
                if not s or not s.strip():
                    continue
                if not (x0 <= ip.x <= x1 and y0 <= ip.y <= y1):
                    continue
                size = max(6.0, float(h) * SCALE)
                parts.append('<text x="%.2f" y="%.2f" font-family="%s" '
                             'font-size="%.2f" fill="#000" '
                             'transform="rotate(%.2f %.2f %.2f)">%s</text>'
                             % (px(ip.x), py(ip.y), FONT, size,
                                -float(rot), px(ip.x), py(ip.y), esc(s)))
                n_txt += 1
        except Exception:
            continue

    head = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            'width="%d" height="%d" viewBox="0 0 %d %d">\n'
            '<!-- %s -->\n' % (W, H, W, H, esc(title)))
    body = "\n".join(parts)
    tail = "\n</svg>\n"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(head + body + tail)
    print("  %-46s 线段%5d 文字%4d 圆%4d 其他%3d  框(%.0f,%.0f)-(%.0f,%.0f)"
          % (os.path.basename(svg_path), n_line, n_txt, n_circ, n_other,
             frame[0], frame[1], frame[2], frame[3]))
    return frame


# ---------------------------------------------------------------- 批量
JOBS = [
    # (dxf, svg 基名, 图框或 None)
    ("out/left_949.dxf", "左岸01-励磁变端子柜端子接线图(1of5)",
     (0.0, 0.1, 297.0, 420.1)),
    ("out/left_949.dxf", "左岸-灭磁电阻柜端子接线图(2of2)",
     (1077.6, 669.0, 1374.6, 1089.0)),
    ("out/left_950.dxf", "左岸02-励磁变端子柜端子接线图(2of5)",
     (10.8, 0.4, 307.8, 420.4)),
    ("out/left_951.dxf", "左岸03-励磁变端子柜端子接线图(3of5)",
     (0.1, 0.4, 307.8, 420.4)),
    ("out/left_952.dxf", "左岸04-励磁变端子柜端子接线图(4of5)",
     (0.1, 0.1, 307.8, 420.1)),
    ("out/left_953.dxf", "左岸05-励磁变端子柜端子接线图(5of5)",
     (0.1, 0.0, 307.8, 420.0)),
    ("out/right_993.dxf", "右岸01-励磁变端子箱端子接线图(1of3)", None),
    ("out/right_994.dxf", "右岸02-励磁变端子箱端子接线图(2of3)", None),
    ("out/right_995.dxf", "右岸03-励磁变端子箱端子接线图(3of3)", None),
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "svg")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    for dxf, base, frame in JOBS:
        src = os.path.join(here, dxf)
        if not os.path.exists(src):
            print("  缺文件 %s" % src)
            continue
        convert(src, os.path.join(outdir, base + ".svg"), frame, base)


if __name__ == "__main__":
    main()
