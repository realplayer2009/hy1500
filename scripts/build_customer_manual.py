#!/usr/bin/env python3
"""将客户使用说明书 Markdown 和本地插图生成 Word。

用法：python3 scripts/build_customer_manual.py [说明书.md]
依赖：python-docx、Pillow。PDF 使用 LibreOffice 从同一 Word 导出。
"""

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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


def add_table(document, rows):
    if len(rows[0]) == 2:
        widths = [4.0, 12.8]
    elif rows[0][0] == "操作":
        widths = [6.0, 9.3, 1.5]
    elif rows[0][0] == "参数":
        widths = [4.7, 3.7, 8.4]
    elif rows[0][0] == "提示":
        widths = [3.2, 7.2, 6.4]
    else:
        widths = [3.3, 6.8, 6.7]
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
    for side, value in (("top", 90), ("bottom", 90), ("left", 110), ("right", 110)):
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
            paragraph.paragraph_format.line_spacing = Pt(14)
            if rows[0][0] == "操作" and column_index == 2:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            text_runs(paragraph, value)
            for run in paragraph.runs:
                run.font.size = Pt(9.5)
                run.bold = index == 0
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.line_spacing = Pt(2)
    paragraph.add_run().font.size = Pt(2)


source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "docs/客户使用说明书.md"

# 图示只说明软件关系与操作顺序，不代表现场物理接线。
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
diagram_font = ImageFont.truetype(font_path, 34)
diagram_small = ImageFont.truetype(font_path, 27)
diagram_large = ImageFont.truetype(font_path, 48)


def label(draw, xy, value, font=diagram_font):
    draw.text(xy, value, font=font, fill="black", anchor="mm")


def arrow(draw, start, end):
    draw.line((start, end), fill="black", width=4)
    x, y = end
    draw.line(((x - 14, y - 10), end, (x - 14, y + 10)), fill="black", width=4)


def heater(draw, x, y, title):
    draw.rounded_rectangle((x, y, x + 140, y + 130), radius=10, outline="black", width=4)
    for offset in (30, 55, 80, 105):
        draw.line(((x + offset, y + 25), (x + offset, y + 105)), fill="black", width=3)
    label(draw, (x + 70, y + 170), title)


image_dir = source.parent / "客户使用说明书插图"
image_dir.mkdir(exist_ok=True)
canvas = Image.new("RGB", (1600, 960), "white")
draw = ImageDraw.Draw(canvas)
# 面板、总线与单块子板的关系示意。
draw.rounded_rectangle((400, 45, 1200, 400), radius=22, outline="black", width=5)
draw.rectangle((455, 85, 1145, 345), outline="black", width=3)
draw.line(((635, 400), (610, 450), (990, 450), (965, 400)), fill="black", width=5)
label(draw, (800, 150), "裕泰通加热器", diagram_large)
for i, title in enumerate(("A", "B", "C")):
    x = 580 + i * 155
    draw.rectangle((x, 215, x + 130, 305), outline="black", width=3)
    label(draw, (x + 65, 260), title)
draw.line(((800, 450), (800, 530)), fill="black", width=4)
label(draw, (1020, 490), "RS485 两路总线", diagram_small)
draw.rounded_rectangle((650, 530, 950, 650), radius=8, outline="black", width=4)
label(draw, (800, 590), "控制子板")
draw.line(((800, 650), (800, 695), (430, 695), (1170, 695)), fill="black", width=4)
for x, title in ((360, "加热器 A"), (730, "加热器 B"), (1100, "加热器 C")):
    draw.line(((x + 70, 695), (x + 70, 735)), fill="black", width=4)
    heater(draw, x, 735, title)
canvas.save(image_dir / "system.png")

canvas = Image.new("RGB", (1600, 240), "white")
draw = ImageDraw.Draw(canvas)
for i, title in enumerate(("关闭", "1 档", "2 档", "3 档")):
    x = 70 + i * 400
    label(draw, (x + 100, 36), title)
    for j in range(3):
        left = x + j * 68
        draw.rectangle((left, 78, left + 50, 128), outline="black", width=3,
                       fill="black" if j < i else "white")
        if i == 0:
            draw.line(((left + 12, 90), (left + 38, 116)), fill="black", width=3)
            draw.line(((left + 12, 116), (left + 38, 90)), fill="black", width=3)
    if i < 3:
        arrow(draw, (x + 230, 104), (x + 340, 104))
draw.line(((1370, 157), (1370, 210), (170, 210), (170, 157)), fill="black", width=3)
draw.line(((160, 170), (170, 157), (180, 170)), fill="black", width=3)
label(draw, (790, 184), "再按一次回到关闭", diagram_small)
canvas.save(image_dir / "stages.png")

canvas = Image.new("RGB", (1600, 240), "white")
draw = ImageDraw.Draw(canvas)
for i, title in enumerate(("记录来源", "排除故障", "确认关闭", "重新启动")):
    x = 60 + i * 405
    draw.ellipse((x + 65, 15, x + 155, 105), outline="black", width=4)
    label(draw, (x + 110, 60), str(i + 1), diagram_large)
    label(draw, (x + 110, 165), title)
    if i < 3:
        arrow(draw, (x + 240, 60), (x + 345, 60))
canvas.save(image_dir / "alarm_flow.png")

document = Document()
section = document.sections[0]
section.page_width, section.page_height = Cm(21), Cm(29.7)
section.left_margin = section.right_margin = Cm(2.1)
section.top_margin = section.bottom_margin = Cm(1.65)
section.footer_distance = Cm(0.65)
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
run = footer.add_run("RS485Control    ")
run.font.size = Pt(8)
field = OxmlElement("w:fldSimple")
field.set(qn("w:instr"), "PAGE")
footer._p.append(field)

lines = source.read_text(encoding="utf-8").splitlines()
index = 0
page_break_pending = False
while index < len(lines):
    line = lines[index].strip()
    index += 1
    if not line:
        continue
    if line == "<!-- pagebreak -->":
        page_break_pending = True
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
        add_table(document, rows)
        continue
    image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
    if image_match:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.keep_with_next = image_match[2].split("/")[-1] != "system.png"
        paragraph.paragraph_format.space_after = Pt(3)
        picture = paragraph.add_run().add_picture(str(source.parent / image_match[2]), width=Cm(16.8))
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

document.core_properties.title = "裕泰通加热器控制软件使用说明书"
document.core_properties.subject = "现场操作图解"
document.core_properties.author = ""
document.core_properties.comments = ""
output = source.with_suffix(".docx")
document.save(output)
print(output)
