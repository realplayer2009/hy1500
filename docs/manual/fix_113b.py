#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§11.3 输出速查表：OT10 标现场接线、OUT5 标选配未接。"""
import io

PATH = "docs/manual/build_manual.py"
OLD1 = "OT7 绿 / OT8 黄 / OT9 红 / OT10 蜂鸣器"
NEW1 = "OT7 绿 / OT8 黄 / OT9 红 / OT10 蜂鸣器（现场接线）"
OLD2 = "OUT4 = 备用扩展输出、OUT5 = 操作提示蜂鸣器"
NEW2 = "OUT4 = 备用扩展输出、OUT5 = 操作确认音（选配 未接）"

with io.open(PATH, encoding="utf-8") as f:
    s = f.read()

hit = 0
for old, new in ((OLD1, NEW1), (OLD2, NEW2)):
    if new in s:
        print("[SKIP] 已是新文案:", new[:30])
        continue
    n = s.count(old)
    if n == 0:
        print("[MISS] 未找到:", old[:30])
        continue
    s = s.replace(old, new)
    hit += n
    print("[OK] 替换", n, "处:", new[:30])

if hit:
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(s)
    print("已写回", PATH, "共", hit, "处")
