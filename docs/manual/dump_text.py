#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出 docx 全文线性文本用于人工校对。"""
import sys

import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

path = sys.argv[1] if len(sys.argv) > 1 else "docs/manual/变压器加热系统-使用手册.docx"
d = docx.Document(path)


def iters(parent):
    for child in parent.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


out = []
for b in iters(d):
    if isinstance(b, Paragraph):
        t = b.text.strip()
        if t:
            out.append(t)
    else:
        out.append("[TABLE %dx%d]" % (len(b.rows), len(b.columns)))
        for row in b.rows:
            out.append("  | " + " | ".join(c.text.replace("\n", " ") for c in row.cells))
print("\n".join(out))
