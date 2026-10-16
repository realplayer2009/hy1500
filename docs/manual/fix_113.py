#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾两处：§11.3 输出速查表 OUT5/OT10 措辞 -> 现场口径。"""
import io

PATH = "docs/manual/build_manual.py"
PAIRS = [
    ('"OT7 绿 / OT8 黄 / OT9 红 / OT10 蜂鸣er"],',
     '"OT7 绿 / OT8 黄 / OT9 红 / OT10 蜂鸣器（现场接线）"],'),
    ('"OUT4 = 备用扩展输出、OUT5 = 操作提示蜂鸣er"]],',
     '"OUT4 = 备用扩展输出、OUT5 = 操作确认音（选配 未接）"]],'),
]

with io.open(PATH, encoding="utf-8") as f:
    s = f.read()

hit = 0
for old, new in PAIRS:
    if new in s and old not in s:
        print("[SKIP] 已是新文案:", old[:34])
        continue
    if old in s:
        s = s.replace(old, new, 1)
        hit += 1
        print("[OK]", old[:34])
    else:
        print("[MISS] 未找到:", old[:34])

if hit:
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(s)
    print("已写回", PATH, "共", hit, "处")
