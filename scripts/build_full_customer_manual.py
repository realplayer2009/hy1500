#!/usr/bin/env python3
"""将完整软件操作册 Markdown 和本地插图生成 170×240 mm 24 开 Word。

用法：python3 scripts/build_full_customer_manual.py [说明书.md]
依赖：python-docx。PDF 使用 LibreOffice 从同一 Word 导出。
"""

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


def text_runs(paragraph, value):
    value = re.sub(r"(\d) (℃|%RH|V|GB|秒|分钟)", r"\1" + "\u00a0" + r"\2", value)
    for index, part in enumerate(re.split(r"\*\*(.*?)\*\*", value)):
        run = paragraph.add_run(part)
        run.bold = index % 2 == 1


def add_table(document, rows, compact):
    if len(rows[0]) == 2:
        widths = [4.0, 12.8]
    elif rows[0][0] == "章节":
        widths = [1.8, 13.5, 1.5]
    elif rows[0][0] == "操作":
        widths = [6.0, 9.3, 1.5]
    elif rows[0][0] == "参数":
        widths = [4.7, 3.7, 8.4]
    elif rows[0][0] == "提示":
        widths = [3.2, 7.2, 6.4]
    elif rows[0][0] == "加热器":
        widths = [3.0, 6.9, 6.9]
    else:
        widths = [3.3, 6.8, 6.7]
    widths = [width * 14.2 / 16.8 for width in widths]
    table = document.add_table(rows=1, cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for column, width in zip(table.columns, widths):
        column.width = Cm(width)
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement("w:" + side)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), "D9D9D9")
        borders.append(element)
    table._tbl.tblPr.append(borders)
    margins = OxmlElement("w:tblCellMar")
    for side, value in (("top", 70 if compact else 90), ("bottom", 70 if compact else 90), ("left", 110), ("right", 110)):
        element = OxmlElement("w:" + side)
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    table._tbl.tblPr.append(margins)
    for index, values in enumerate(rows):
        row = table.rows[0] if index == 0 else table.add_row()
        properties = row._tr.get_or_add_trPr()
        properties.append(OxmlElement("w:cantSplit"))
        if index == 0:
            properties.append(OxmlElement("w:tblHeader"))
        for column_index, (cell, value, width) in enumerate(zip(row.cells, values, widths)):
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            shade = OxmlElement("w:shd")
            shade.set(qn("w:fill"), "EEEEEE" if index == 0 else "FFFFFF")
            cell._tc.get_or_add_tcPr().append(shade)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = Pt(13 if compact else 14)
            if rows[0][0] in ("操作", "章节") and column_index == 2:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            text_runs(paragraph, value)
            for run in paragraph.runs:
                run.font.size = Pt(9.5)
                run.bold = index == 0
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.line_spacing = Pt(2)
    paragraph.add_run().font.size = Pt(2)


source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "docs/products/客户使用说明书.md"

document = Document()
section = document.sections[0]
section.page_width, section.page_height = Cm(17), Cm(24)
section.left_margin = section.right_margin = Cm(1.4)
section.top_margin = section.bottom_margin = Cm(1.2)
section.footer_distance = Cm(0.5)
section.different_first_page_header_footer = True
for grid in section._sectPr.findall(qn("w:docGrid")):
    section._sectPr.remove(grid)
for border in document.styles.element.xpath(".//w:pBdr"):
    border.getparent().remove(border)
for name, size in (("Normal", 10.5), ("Title", 28), ("Subtitle", 10), ("Heading 1", 19), ("Heading 2", 12), ("List Bullet", 10.5), ("Caption", 9)):
    style = document.styles[name]
    style.font.name = "Noto Sans CJK SC"
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string("000000")
    style.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Noto Sans CJK SC")
    style.paragraph_format.space_after = Pt(7)
    style.paragraph_format.line_spacing = Pt(16)
    style.paragraph_format.widow_control = True
    style.paragraph_format.keep_together = True
    snap = OxmlElement("w:snapToGrid")
    snap.set(qn("w:val"), "0")
    style.element.get_or_add_pPr().append(snap)
    for color in style.element.xpath(".//w:color"):
        for attr in ("themeColor", "themeTint", "themeShade"):
            color.attrib.pop(qn("w:" + attr), None)
    if name == "Title":
        style.font.bold = True
        style.paragraph_format.line_spacing = Pt(39)
        style.paragraph_format.space_before = Pt(20)
        style.paragraph_format.space_after = Pt(16)
    elif name.startswith("Heading"):
        style.font.bold = True
        style.paragraph_format.line_spacing = Pt(37 if name == "Heading 1" else 18)
        style.paragraph_format.space_before = Pt(8 if name == "Heading 2" else 0)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True
    elif name in ("Subtitle", "Caption"):
        style.font.color.rgb = RGBColor.from_string("555555")
        style.paragraph_format.line_spacing = Pt(13)
    elif name == "List Bullet":
        style.paragraph_format.left_indent = Cm(0.45)
        style.paragraph_format.first_line_indent = Cm(-0.35)
        style.paragraph_format.keep_with_next = False

footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
field = OxmlElement("w:fldSimple")
field.set(qn("w:instr"), "PAGE")
footer._p.append(field)

lines = source.read_text(encoding="utf-8").splitlines()
index = 0
page_break_pending = False
on_cover = True
compact = False
dense = False
while index < len(lines):
    line = lines[index].strip()
    index += 1
    if not line:
        continue
    if line == "<!-- pagebreak -->":
        page_break_pending = True
        on_cover = False
        compact = False
        dense = False
        continue
    if line == "<!-- compact -->":
        compact = True
        continue
    if line == "<!-- dense -->":
        compact = True
        dense = True
        continue
    if on_cover:
        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
        paragraph = document.add_paragraph(style="Title" if line.startswith("# ") else "Normal")
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = False
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(10)
        paragraph.paragraph_format.line_spacing = Pt(20)
        if image_match:
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.space_after = Pt(18)
            picture = paragraph.add_run().add_picture(str(source.parent / image_match[2]), height=Cm(10.2))
            picture._inline.docPr.set("descr", image_match[1])
            continue
        run = paragraph.add_run(line[2:] if line.startswith("# ") else line)
        run.font.italic = False
        run.font.color.rgb = RGBColor.from_string("000000")
        if line.startswith("# "):
            run.font.size = Pt(30)
            run.bold = True
            paragraph.paragraph_format.line_spacing = Pt(44)
            paragraph.paragraph_format.space_after = Pt(10)
        elif line == "使用说明书":
            run.font.size = Pt(22)
            paragraph.paragraph_format.line_spacing = Pt(30)
            paragraph.paragraph_format.space_after = Pt(16)
        elif line.startswith("型号"):
            run.font.size = Pt(14)
            run.bold = True
        elif re.fullmatch(r"\d{4}年\d{1,2}月", line):
            run.font.size = Pt(10)
            paragraph.paragraph_format.line_spacing = Pt(16)
        else:
            run.font.size = Pt(13)
            paragraph.paragraph_format.space_before = Pt(15)
            paragraph.paragraph_format.space_after = Pt(16)
        continue
    if line.startswith("|"):
        rows = []
        while True:
            row = [value.strip() for value in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", value) for value in row):
                rows.append(row)
            if index == len(lines) or not lines[index].strip().startswith("|"):
                break
            line = lines[index].strip()
            index += 1
        add_table(document, rows, compact)
        continue
    image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
    if image_match:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.keep_with_next = image_match[2].split("/")[-1] != "system.png"
        paragraph.paragraph_format.space_after = Pt(3)
        picture = paragraph.add_run().add_picture(str(source.parent / image_match[2]), width=Cm(12.6 if compact else 14.2))
        picture._inline.docPr.set("descr", image_match[1])
        continue
    if line.startswith("# "):
        paragraph = document.add_paragraph(line[2:], "Title")
    elif line.startswith("## "):
        paragraph = document.add_paragraph(style="Heading 1")
        number = re.match(r"^(\d{2}) (.*)", line[3:])
        if number:
            run = paragraph.add_run(number[1] + "  ")
            run.font.size = Pt(30)
            paragraph.add_run(number[2])
        else:
            paragraph.add_run(line[3:])
    elif line.startswith("### "):
        paragraph = document.add_paragraph(line[4:], "Heading 2")
    elif line.startswith("RS485Control "):
        paragraph = document.add_paragraph(line, "Subtitle")
    elif line.startswith("图 "):
        paragraph = document.add_paragraph(line, "Caption")
    else:
        paragraph = document.add_paragraph(style="List Bullet" if line.startswith("- ") else "Normal")
        step = re.match(r"^(\d+)\. (.*)", line)
        if step:
            paragraph.paragraph_format.left_indent = Cm(0.85)
            paragraph.paragraph_format.first_line_indent = Cm(-0.85)
            paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(0.85))
            run = paragraph.add_run(step[1] + "\t")
            run.bold = True
            run.font.size = Pt(15)
            text_runs(paragraph, step[2])
            paragraph.paragraph_format.line_spacing = Pt(18)
            paragraph.paragraph_format.space_after = Pt(9)
        else:
            text_runs(paragraph, line[2:] if line.startswith("- ") else line)
    if page_break_pending:
        paragraph.paragraph_format.page_break_before = True
        page_break_pending = False
    if dense and not line.startswith(("## ", "### ", "图 ")):
        paragraph.paragraph_format.line_spacing = Pt(14)
        for run in paragraph.runs:
            run.font.size = Pt(9.5)
    if dense and line.startswith("### "):
        paragraph.paragraph_format.space_before = Pt(5)
        paragraph.paragraph_format.space_after = Pt(4)
    if compact and not line.startswith(("## ", "### ")):
        paragraph.paragraph_format.space_after = Pt(3)
        if re.match(r"^\d+\. ", line):
            paragraph.paragraph_format.line_spacing = Pt(16.5)

document.core_properties.title = "裕泰通加热器控制箱使用说明书"
document.core_properties.subject = "现场操作图解"
document.core_properties.author = ""
document.core_properties.comments = ""
output = source.with_suffix(".docx")
document.save(output)
print(output)
