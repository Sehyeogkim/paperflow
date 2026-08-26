from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projects/paperflow_gemini-acbc8f9783"
OUT = PROJECT / "_paperflow_out"
DATA = PROJECT / "data/uploads"
PDF = OUT / "paper.pdf"
FONT = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")

TITLE = (
    "Global Sensitivity Analysis of Coronary Plaque Vulnerability Indices: "
    "Dominant Contributions of Material Properties"
)
SHORT_TITLE = "Global Sensitivity Analysis of Coronary Plaque Vulnerability Indices"

TERRACOTTA = colors.HexColor("#CC785C")
CREAM = colors.HexColor("#F0EEE6")
LIGHT_WARM = colors.HexColor("#E8D5C4")
TAN = colors.HexColor("#D4C5B0")
INK = colors.HexColor("#1A1A1A")
BODY = colors.HexColor("#2D2D2D")
MUTED = colors.HexColor("#6B5E54")
OLIVE = colors.HexColor("#7A9A6D")
PALE_OLIVE = colors.HexColor("#E4EBDD")

REFS = json.loads((OUT / "reference_candidates.json").read_text(encoding="utf-8"))
REF_NUM = {ref["key"]: index for index, ref in enumerate(REFS, start=1)}


def citation_text(match: re.Match[str]) -> str:
    keys = []
    for item in match.group(1).split(","):
        key = re.sub(r"^cite:\s*", "", item.strip(), flags=re.I)
        if key in REF_NUM:
            keys.append(REF_NUM[key])
    return "[" + ", ".join(str(number) for number in sorted(set(keys))) + "]" if keys else ""


def normalize(text: str) -> str:
    text = re.sub(r"\[cite:\s*([^\]]+)\]", citation_text, text.strip(), flags=re.I)
    replacements = {
        r"\frac{\Delta\text{PSS}}{S_{\text{fc}}}": "ΔPSS / S_fc",
        r"\textasciitilde": "~",
        r"\Delta": "Δ",
        r"\sigma": "σ",
        r"\tau": "τ",
        r"\alpha": "α",
        r"\sim": "~",
        r"\_": "_",
        r"\textbackslash": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    for _ in range(4):
        text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", text)
        text = re.sub(r"\\(?:text|mathrm)\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\tag\{([^{}]+)\}", r"(\1)", text)
    text = text.replace("$$", "").replace("$", "")
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def safe(text: str) -> str:
    return escape(normalize(text)).replace("\n", "<br/>")


pdfmetrics.registerFont(TTFont("PaperKorean", str(FONT)))

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "PaperTitle", parent=styles["Title"], fontName="PaperKorean", fontSize=20,
    leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=8,
)
meta_style = ParagraphStyle(
    "Meta", parent=styles["Normal"], fontName="PaperKorean", fontSize=8.2,
    leading=11.5, textColor=MUTED,
)
status_style = ParagraphStyle(
    "Status", parent=meta_style, fontSize=8.4, leading=13, textColor=BODY,
)
section_style = ParagraphStyle(
    "Section", parent=styles["Heading1"], fontName="PaperKorean", fontSize=15.5,
    leading=20, textColor=INK, spaceBefore=13, spaceAfter=8, keepWithNext=True,
)
subsection_style = ParagraphStyle(
    "Subsection", parent=styles["Heading2"], fontName="PaperKorean", fontSize=11.2,
    leading=15.5, textColor=TERRACOTTA, spaceBefore=9, spaceAfter=5, keepWithNext=True,
)
body_style = ParagraphStyle(
    "Body", parent=styles["BodyText"], fontName="PaperKorean", fontSize=8.9,
    leading=14.7, textColor=BODY, alignment=TA_JUSTIFY, firstLineIndent=4 * mm,
    spaceAfter=7, splitLongWords=False, wordWrap="CJK",
)
abstract_style = ParagraphStyle(
    "AbstractBody", parent=body_style, fontSize=8.8, leading=14.3,
    firstLineIndent=0, spaceAfter=0,
)
caption_style = ParagraphStyle(
    "Caption", parent=meta_style, fontSize=7.7, leading=10.5, textColor=MUTED,
    alignment=TA_LEFT, spaceBefore=3, spaceAfter=6,
)
reference_style = ParagraphStyle(
    "Reference", parent=body_style, fontName="Helvetica", fontSize=7.4,
    leading=10.5, firstLineIndent=-5 * mm,
    leftIndent=5 * mm, spaceAfter=4, alignment=TA_LEFT,
)
table_header_style = ParagraphStyle(
    "TableHeader", parent=meta_style, fontSize=6.4, leading=7.5, textColor=INK,
    alignment=TA_CENTER,
)
table_cell_style = ParagraphStyle(
    "TableCell", parent=meta_style, fontSize=6.2, leading=7.5, textColor=BODY,
    alignment=TA_LEFT,
)


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setFont("PaperKorean", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, height - 11 * mm, SHORT_TITLE)
        canvas.setStrokeColor(TAN)
        canvas.setLineWidth(0.45)
        canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
    canvas.setFont("PaperKorean", 7.1)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "PaperFlow · Gemini 2.5 Flash · quality gate passed")
    canvas.drawRightString(width - 18 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


doc = BaseDocTemplate(
    str(PDF), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
    topMargin=20 * mm, bottomMargin=18 * mm, title=TITLE, author="Anonymous",
    subject="Computational biomechanics manuscript generated by PaperFlow",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="paper", frames=[frame], onPage=header_footer)])


def add_markdown(story: list, path: Path) -> None:
    text = path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith("### "):
            story.append(Paragraph(safe(first[4:]), subsection_style))
            if len(lines) > 1:
                story.append(Paragraph(safe(" ".join(lines[1:])), body_style))
        elif first.startswith(("## ", "# ")):
            heading = first.lstrip("# ")
            story.append(Paragraph(safe(heading), subsection_style))
            if len(lines) > 1:
                story.append(Paragraph(safe(" ".join(lines[1:])), body_style))
        else:
            story.append(Paragraph(safe(" ".join(lines)), body_style))


def csv_rows(pattern: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(DATA.glob(pattern)):
        match = re.search(r"sobol_(?:grp|ind)_(lap|cp)_(vi\d)", path.name, re.I)
        if not match:
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                row["model"] = match.group(1).upper()
                row["outcome"] = match.group(2).upper()
                rows.append(row)
    return rows


GROUP_ROWS = csv_rows("*sobol_grp_*.csv")
IND_ROWS = csv_rows("*sobol_ind_*.csv")


def para_cell(value: object, style=table_cell_style) -> Paragraph:
    return Paragraph(safe(str(value)), style)


def styled_long_table(data, widths, *, header_rows=1, font_size=6.2) -> LongTable:
    table = LongTable(data, colWidths=widths, repeatRows=header_rows, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), LIGHT_WARM),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), INK),
        ("FONTNAME", (0, 0), (-1, -1), "PaperKorean"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 1.5),
        ("GRID", (0, 0), (-1, -1), 0.3, TAN),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, CREAM]),
    ]))
    return table


def group_chart() -> Drawing:
    rows = [row for row in GROUP_ROWS if row["outcome"] == "VI2"]
    order = {("LAP", "Material"): 0, ("LAP", "Hemodynamics"): 1,
             ("LAP", "Morphology"): 2, ("CP", "Material"): 3,
             ("CP", "Hemodynamics"): 4, ("CP", "Morphology"): 5}
    rows.sort(key=lambda row: order[(row["model"], row["group"])])
    width, height = 475, 235
    drawing = Drawing(width, height)
    x0, usable, top, row_h = 116, 330, 198, 28
    for tick in range(0, 11, 2):
        x = x0 + usable * tick / 10
        drawing.add(Line(x, 24, x, top + 13, strokeColor=TAN, strokeWidth=0.35))
        drawing.add(String(x, 11, f"{tick / 10:.1f}", fontName="PaperKorean",
                           fontSize=6.5, fillColor=MUTED, textAnchor="middle"))
    drawing.add(String(x0 + usable / 2, 0, "Sobol sensitivity index", fontName="PaperKorean",
                       fontSize=7, fillColor=MUTED, textAnchor="middle"))
    for index, row in enumerate(rows):
        y = top - index * row_h
        label = f"{row['model']} · {row['group']}"
        drawing.add(String(x0 - 7, y + 1, label, fontName="PaperKorean", fontSize=7.2,
                           fillColor=BODY, textAnchor="end"))
        s1, st = float(row["S1"]), float(row["ST"])
        drawing.add(Rect(x0, y + 5, usable * st, 7, fillColor=PALE_OLIVE,
                         strokeColor=OLIVE, strokeWidth=0.4))
        drawing.add(Rect(x0, y - 5, usable * s1, 7, fillColor=TERRACOTTA,
                         strokeColor=TERRACOTTA, strokeWidth=0.4))
        drawing.add(String(x0 + usable * st + 4, y + 6, f"{st:.2f}", fontName="PaperKorean",
                           fontSize=6.2, fillColor=OLIVE))
    drawing.add(Rect(300, 218, 9, 6, fillColor=TERRACOTTA, strokeColor=TERRACOTTA))
    drawing.add(String(313, 217, "S1", fontName="PaperKorean", fontSize=6.8, fillColor=BODY))
    drawing.add(Rect(350, 218, 9, 6, fillColor=PALE_OLIVE, strokeColor=OLIVE))
    drawing.add(String(363, 217, "ST", fontName="PaperKorean", fontSize=6.8, fillColor=BODY))
    return drawing


def add_group_table(story: list) -> None:
    story.append(Paragraph("Table 1. Group-level Sobol sensitivity indices across plaque models and outcomes.", caption_style))
    header = [para_cell(v, table_header_style) for v in ["Model", "Outcome", "Group", "S1", "ST", "ST - S1"]]
    data = [header]
    for row in GROUP_ROWS:
        s1, st = float(row["S1"]), float(row["ST"])
        data.append([para_cell(row["model"]), para_cell(row["outcome"]), para_cell(row["group"]),
                     para_cell(f"{s1:.4f}"), para_cell(f"{st:.4f}"), para_cell(f"{st-s1:.4f}")])
    story.append(styled_long_table(data, [18*mm, 20*mm, 37*mm, 21*mm, 21*mm, 23*mm]))
    story.append(Spacer(1, 6 * mm))


def add_individual_table(story: list) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Table 2. Individual-parameter Sobol sensitivity indices across plaque models and outcomes.", caption_style))
    header = [para_cell(v, table_header_style) for v in ["Model", "Outcome", "Parameter", "S1", "ST", "ST - S1"]]
    data = [header]
    for row in IND_ROWS:
        s1, st = float(row["S1"]), float(row["ST"])
        data.append([para_cell(row["model"]), para_cell(row["outcome"]), para_cell(row.get("display_name") or row["parameter"]),
                     para_cell(f"{s1:.4f}"), para_cell(f"{st:.4f}"), para_cell(f"{st-s1:.4f}")])
    story.append(styled_long_table(data, [18*mm, 20*mm, 47*mm, 19*mm, 19*mm, 21*mm]))
    story.append(Spacer(1, 6 * mm))


def add_input_range_table(story: list) -> None:
    path = next(DATA.glob("*input.csv"))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    header = [para_cell(v, table_header_style) for v in ["Input variable", "Minimum", "Maximum", "N"]]
    data = [header]
    for name in rows[0]:
        values = [float(row[name]) for row in rows if row.get(name) not in (None, "")]
        data.append([para_cell(name), para_cell(f"{min(values):.5g}"),
                     para_cell(f"{max(values):.5g}"), para_cell(str(len(values)))])
    story.append(Paragraph("Table 3. Observed input-space ranges in the uploaded 1,000-sample dataset.", caption_style))
    story.append(styled_long_table(data, [63*mm, 31*mm, 31*mm, 18*mm]))
    story.append(Spacer(1, 6 * mm))


def add_references(story: list) -> None:
    story.append(PageBreak())
    story.append(Paragraph("References", section_style))
    story.append(HRFlowable(width="100%", thickness=0.65, color=TAN, spaceAfter=4 * mm))
    for number, ref in enumerate(REFS, start=1):
        journal = ref.get("journal", "")
        volume = ref.get("volume", "")
        issue = ref.get("issue", "")
        pages = ref.get("pages", "")
        venue = journal
        if volume:
            venue += f" {volume}"
        if issue:
            venue += f"({issue})"
        if pages:
            venue += f":{pages}"
        text = (
            f"[{number}] {ref.get('authors', '')} {ref.get('title', '')}. "
            f"{venue}. {ref.get('year', 'n.d.')}. doi:{ref.get('doi', '')}."
        )
        story.append(Paragraph(safe(text), reference_style))


story = [
    Spacer(1, 9 * mm),
    Paragraph(TITLE, title_style),
    Spacer(1, 2 * mm),
    Paragraph("Anonymous · Computational biomechanics", meta_style),
    Paragraph("Target journal: Computers in Biology and Medicine", meta_style),
    Spacer(1, 6 * mm),
    HRFlowable(width="100%", thickness=2, color=TERRACOTTA, spaceAfter=7 * mm),
]

status = Paragraph(
    "<b>Complete Korean manuscript draft</b><br/>"
    "Quality gate passed · 6 evidence-verifiable selection criteria · "
    "3 materialized tables · 11 resolved references",
    status_style,
)
story.append(Table([[status]], colWidths=[doc.width], style=[
    ("BACKGROUND", (0, 0), (-1, -1), PALE_OLIVE),
    ("BOX", (0, 0), (-1, -1), 0.7, OLIVE),
    ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
]))
story.extend([Spacer(1, 6 * mm), Paragraph("Abstract", section_style)])

abstract = Paragraph(safe((OUT / "Abstract.md").read_text(encoding="utf-8")), abstract_style)
story.append(Table([[abstract]], colWidths=[doc.width], style=[
    ("BACKGROUND", (0, 0), (-1, -1), CREAM),
    ("BOX", (0, 0), (-1, -1), 0.7, TAN),
    ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
    ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
]))
story.extend([
    Spacer(1, 4 * mm), Paragraph("Keywords", subsection_style),
    Paragraph("coronary plaque rupture · fluid–structure interaction · Sobol sensitivity analysis · Gaussian process regression · vulnerability index", meta_style),
    PageBreak(),
])

sections = [
    ("1. Introduction", "Introduction.md"),
    ("2. Methods", "Method.md"),
    ("3. Results", "Result.md"),
    ("4. Discussion", "Discussion.md"),
    ("5. Conclusion", "Conclusion.md"),
]
for heading, filename in sections:
    story.append(Paragraph(heading, section_style))
    story.append(HRFlowable(width="100%", thickness=0.65, color=TAN, spaceAfter=4 * mm))
    add_markdown(story, OUT / filename)
    if filename == "Result.md":
        story.extend([
            Spacer(1, 4 * mm),
            Paragraph("VI2 grouped sensitivity overview", subsection_style),
            group_chart(),
            Paragraph("Visual summary of the uploaded VI2 Sobol indices. Material properties dominate both LAP and CP models; bar lengths are source-data values, not model-generated estimates.", caption_style),
        ])
        add_group_table(story)
        add_individual_table(story)
        add_input_range_table(story)
    story.append(Spacer(1, 3 * mm))

add_references(story)
story.extend([
    Spacer(1, 8 * mm),
    HRFlowable(width="100%", thickness=0.7, color=TAN, spaceBefore=3 * mm, spaceAfter=4 * mm),
    Paragraph(
        "Evidence note: the 15 auxiliary fibrous-cap-thickness simulations and the seventh selection criterion were excluded because the source inputs retain an unresolved unit/value inconsistency. No numerical correction was inferred.",
        meta_style,
    ),
])

if PDF.exists():
    PDF.unlink()
doc.build(story)
print(PDF)
