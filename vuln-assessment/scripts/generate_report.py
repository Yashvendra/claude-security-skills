"""
Vulnerability Assessment Report Generator
Generic ReportLab PDF generator — reads a JSON findings file and produces
a professional A4 PDF report with dark navy theme.

Usage:
    python generate_report.py --findings findings.json --output Report.pdf [--logo logo.png]

JSON schema (findings.json):
    {
      "project_name": str,
      "target_path": str,
      "branch": str,                   # Optional git branch name
      "language": str,
      "framework": str,
      "assessment_type": str,          # e.g. "Static Code Review + Architecture Audit"
      "report_date": str,              # YYYY-MM-DD
      "scope_rows": [[str, ...]],      # First row = headers
      "data_flow_summary": str,        # Optional 2–3 sentence description
      "external_deps": [[str, ...]],   # Optional, first row = headers
      "findings": [
        {
          "id": str,                   # VUL-001
          "severity": str,             # CRITICAL / HIGH / MEDIUM / LOW / INFO
          "cvss": str,                 # e.g. "9.8"
          "title": str,
          "location": str,
          "description": str,          # may contain basic HTML: <b>, <i>, <code>
          "impact": str,
          "evidence": str,             # code snippet, plain text
          "remediation": str,
          "references": str            # optional, e.g. "CWE-89 · OWASP A03:2021"
        }
      ]
    }
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from collections import Counter
from html import escape as _he

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import Flowable
except ImportError:
    print("ERROR: reportlab is not installed.")
    print("Install it with:  pip install reportlab")
    sys.exit(1)


# ─────────────────────────── Colour Palette ───────────────────────────────

DARK_BG         = colors.HexColor("#1A1A2E")
ACCENT_BLUE     = colors.HexColor("#16213E")
ACCENT_CYAN     = colors.HexColor("#0F3460")
HIGHLIGHT       = colors.HexColor("#E94560")
LIGHT_GREY      = colors.HexColor("#F5F5F5")
MID_GREY        = colors.HexColor("#CCCCCC")
DARK_TEXT       = colors.HexColor("#1A1A1A")
WHITE           = colors.white

SEV_COLOR_HEX = {
    "CRITICAL": "#C0392B", "HIGH": "#E74C3C",
    "MEDIUM":   "#E67E22", "LOW":  "#27AE60", "INFO": "#2980B9",
}
SEV_BG = {
    "CRITICAL": colors.HexColor("#FADBD8"),
    "HIGH":     colors.HexColor("#FDEDEC"),
    "MEDIUM":   colors.HexColor("#FDEBD0"),
    "LOW":      colors.HexColor("#EAFAF1"),
    "INFO":     colors.HexColor("#EBF5FB"),
}

_styles = getSampleStyleSheet()


# ─────────────────────────── Custom Styles ────────────────────────────────

def _build_styles():
    S = {}
    S["section"] = ParagraphStyle(
        "section", fontSize=15, textColor=DARK_BG,
        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6)
    S["subsection"] = ParagraphStyle(
        "subsection", fontSize=12, textColor=ACCENT_BLUE,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    S["body"] = ParagraphStyle(
        "body", fontSize=9.5, textColor=DARK_TEXT,
        fontName="Helvetica", leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
    S["body_small"] = ParagraphStyle(
        "body_small", fontSize=8.5, textColor=DARK_TEXT,
        fontName="Helvetica", leading=12, spaceAfter=4)
    S["code"] = ParagraphStyle(
        "code", fontSize=7.5, textColor=colors.HexColor("#2D2D2D"),
        fontName="Courier", leading=11, backColor=colors.HexColor("#F4F4F4"),
        leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=4, borderPad=4)
    S["label"] = ParagraphStyle(
        "label", fontSize=8.5, textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Bold", leading=11)
    S["bullet"] = ParagraphStyle(
        "bullet", fontSize=9, textColor=DARK_TEXT,
        fontName="Helvetica", leading=13, leftIndent=14,
        bulletIndent=6, spaceAfter=2)
    return S


S = _build_styles()


def _esc(text: str) -> str:
    """Escape text for ReportLab Paragraph (keeps existing <br/> tags intact)."""
    return _he(str(text), quote=False).replace("&lt;br/&gt;", "<br/>")


def _remediation_para(text: str, style) -> "Paragraph":
    """
    Convert '1. foo 2. bar 3. baz' into a Paragraph with each item on its own
    line, prefixed with a bullet and indented.  Falls back to plain text if the
    input doesn't look like a numbered list.
    """
    items = re.split(r"\s*\d+\.\s+", text.strip())
    items = [i.strip() for i in items if i.strip()]
    if len(items) > 1:
        lines = "<br/>".join(f"&bull;&nbsp;&nbsp;{_esc(i)}" for i in items)
        return Paragraph(lines, style)
    return Paragraph(_esc(text), style)


def hr(color=MID_GREY, thickness=0.5, spaceB=4, spaceA=4):
    return HRFlowable(width="100%", thickness=thickness,
                      color=color, spaceAfter=spaceA, spaceBefore=spaceB)


def _para_rows(rows, body_style, header_color=WHITE):
    """
    Convert a list-of-lists table (first row = headers) so that every cell
    is a Paragraph flowable rather than a raw string.  This is required for
    ReportLab to word-wrap long cell content; plain strings are never wrapped.
    """
    header_style = ParagraphStyle(
        "tbl_hdr", fontSize=body_style.fontSize, fontName="Helvetica-Bold",
        textColor=header_color, leading=body_style.leading or 12, spaceAfter=0)
    result = []
    for r_idx, row in enumerate(rows):
        style = header_style if r_idx == 0 else body_style
        result.append([
            cell if not isinstance(cell, str) else Paragraph(cell, style)
            for cell in row
        ])
    return result


def severity_badge(sev: str):
    fg = SEV_COLOR_HEX.get(sev.upper(), "#1A1A1A")
    bg = SEV_BG.get(sev.upper(), LIGHT_GREY)
    return Paragraph(
        f'<font color="{fg}"><b> {sev.upper()} </b></font>',
        ParagraphStyle("badge", fontSize=8, backColor=bg, borderPad=2,
                       fontName="Helvetica-Bold", alignment=TA_CENTER, leading=10))


# ─────────────────────────── Cover Page ───────────────────────────────────

def draw_cover_canvas(canvas, doc, meta: dict, logo_path: str = None, watermark: str = None):
    w, h = A4
    canvas.saveState()

    # Full background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # Inner card
    canvas.setFillColor(ACCENT_BLUE)
    canvas.roundRect(w * 0.055, h * 0.055, w * 0.89, h * 0.89, 12, fill=1, stroke=0)

    # Decorative circle (top-right)
    canvas.setFillColor(ACCENT_CYAN)
    canvas.circle(w * 0.92, h * 0.88, w * 0.28, fill=1, stroke=0)
    canvas.setFillColor(DARK_BG)
    canvas.circle(w * 0.92, h * 0.88, w * 0.20, fill=1, stroke=0)

    # Top accent stripe (red)
    canvas.setFillColor(HIGHLIGHT)
    canvas.rect(0, h - 0.45 * cm, w, 0.45 * cm, fill=1, stroke=0)

    # Bottom accent stripe (cyan)
    canvas.setFillColor(ACCENT_CYAN)
    canvas.rect(0, 0, w, 0.40 * cm, fill=1, stroke=0)

    # ── Fixed layout zones — all positions are absolute, independent of logo size ──
    # Logo header zone sits in the upper portion of the card: h*0.83 … h*0.90
    LOGO_ZONE_BOTTOM = h * 0.83   # ≈ 699 pt
    LOGO_ZONE_TOP    = h * 0.90   # ≈ 758 pt
    SEP_Y            = h * 0.81   # red separator rule below logo zone
    T1_Y             = h * 0.77   # "VULNERABILITY ASSESSMENT" baseline
    T2_Y             = T1_Y - 32  # "REPORT" baseline
    SUB_Y            = T2_Y - 36  # project name subtitle
    RULE2_Y          = SUB_Y - 16 # thin rule below subtitle
    META_TOP_Y       = RULE2_Y - 22  # first meta row baseline

    # Logo — placed inside the fixed header zone, aspect-ratio preserved
    if logo_path and os.path.isfile(logo_path):
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            if ih > 0:
                aspect = iw / ih
                zone_h = LOGO_ZONE_TOP - LOGO_ZONE_BOTTOM - 0.8 * cm  # inner height after padding
                max_w  = 5.8 * cm
                # Scale to fit within max_w × zone_h, preserving aspect ratio
                logo_w = min(max_w, zone_h * aspect)
                logo_h = logo_w / aspect
                if logo_h > zone_h:
                    logo_h = zone_h
                    logo_w = logo_h * aspect
                logo_x = (w - logo_w) / 2
                # Vertically centre inside the zone
                logo_y = LOGO_ZONE_BOTTOM + (LOGO_ZONE_TOP - LOGO_ZONE_BOTTOM - logo_h) / 2
                pill_px, pill_py = 0.65 * cm, 0.40 * cm
                canvas.setFillColor(WHITE)
                canvas.roundRect(logo_x - pill_px, logo_y - pill_py,
                                 logo_w + 2 * pill_px, logo_h + 2 * pill_py,
                                 7, fill=1, stroke=0)
                canvas.drawImage(logo_path, logo_x, logo_y,
                                 logo_w, logo_h, mask="auto", preserveAspectRatio=True)
        except Exception:
            pass  # logo load failed — continue without it

    # Separator rule
    canvas.setStrokeColor(HIGHLIGHT)
    canvas.setLineWidth(1.4)
    canvas.line(w * 0.22, SEP_Y, w * 0.78, SEP_Y)

    # Title
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 25)
    canvas.drawCentredString(w / 2, T1_Y, "VULNERABILITY ASSESSMENT")
    canvas.drawCentredString(w / 2, T2_Y, "REPORT")

    # Project name subtitle
    canvas.setFillColor(colors.HexColor("#A8C8E8"))
    canvas.setFont("Helvetica", 12.5)
    canvas.drawCentredString(w / 2, SUB_Y, meta.get("project_name", "Security Audit"))

    # Rule under subtitle
    canvas.setStrokeColor(HIGHLIGHT)
    canvas.setLineWidth(1.5)
    canvas.line(w * 0.25, RULE2_Y, w * 0.75, RULE2_Y)

    # Meta block — include branch if present
    meta_items = [
        ("Target",          meta.get("target_path", "")),
        ("Language",        meta.get("language", "")),
        ("Assessment Type", meta.get("assessment_type", "Static Code Review + Architecture Audit")),
        ("Report Date",     meta.get("report_date", str(date.today()))),
        ("Classification",  "CONFIDENTIAL — Internal Use Only"),
    ]
    branch = meta.get("branch", "")
    if branch and branch.lower() not in ("", "n/a", "none"):
        meta_items.insert(1, ("Branch", branch))

    line_gap = 21
    for i, (label, val) in enumerate(meta_items):
        y = META_TOP_Y - i * line_gap
        canvas.setFillColor(colors.HexColor("#7090B0"))
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(w / 2 - 10, y, f"{label}:")
        canvas.setFillColor(colors.HexColor("#D0D8E8"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(w / 2 + 10, y, val)

    # Watermark on cover (if provided)
    if watermark:
        canvas.saveState()
        canvas.translate(w / 2, h / 2)
        canvas.rotate(45)
        canvas.setFillColorRGB(0.55, 0.55, 0.55)
        canvas.setFillAlpha(0.18)
        canvas.setFont("Helvetica-Bold", 80)
        canvas.drawCentredString(0, 0, watermark.upper())
        canvas.restoreState()

    canvas.restoreState()


def build_cover():
    return [PageBreak()]


# ─────────────────────────── Executive Summary ────────────────────────────

def build_executive_summary(meta: dict, findings: list) -> list:
    story = []
    story.append(Paragraph("Executive Summary", S["section"]))
    story.append(hr(color=HIGHLIGHT, thickness=1.5))
    story.append(Spacer(1, 0.2 * cm))

    proj  = meta.get("project_name", "the target system")
    lang  = meta.get("language", "")
    fw    = meta.get("framework", "")
    atype = meta.get("assessment_type", "Static Code Review + Architecture Audit")
    stack = lang + (f" / {fw}" if fw and fw.lower() not in ("", "none") else "")

    intro = (
        f"An in-depth {atype.lower()} was conducted on the "
        f"<b>{proj}</b> codebase" +
        (f" ({stack})" if stack else "") +
        ". The audit examined data flows, trust boundaries, authentication mechanisms, "
        "external integrations, and all code paths handling untrusted input."
    )
    story.append(Paragraph(intro, S["body"]))
    story.append(Spacer(1, 0.1 * cm))

    counts = Counter(f.get("severity", "INFO").upper() for f in findings)
    total  = len(findings)
    sev_parts = [
        f"<b>{counts[s]}</b> {s.lower()}"
        for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] if counts[s]
    ]
    story.append(Paragraph(
        f"The audit identified <b>{total} distinct security finding{'s' if total != 1 else ''}</b> "
        f"({', '.join(sev_parts)}). "
        "Critical findings should be addressed before any production deployment. "
        "High findings should be remediated in the current sprint.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Summary table grouped by severity
    sev_bg_map = {
        "CRITICAL": colors.HexColor("#FADBD8"), "HIGH":   colors.HexColor("#FDEDEC"),
        "MEDIUM":   colors.HexColor("#FDEBD0"), "LOW":    colors.HexColor("#EAFAF1"),
        "INFO":     colors.HexColor("#EBF5FB"),
    }
    by_sev = {s: [f["title"] for f in findings if f.get("severity","").upper() == s]
              for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]}

    rows     = [["Severity", "Count", "Representative Findings"]]
    row_bgs  = [DARK_BG]
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        if not counts[sev]:
            continue
        titles   = by_sev[sev]
        rep_text = " · ".join(titles[:3]) + (" · …" if len(titles) > 3 else "")
        rows.append([severity_badge(sev), str(counts[sev]),
                     Paragraph(rep_text, S["body_small"])])
        row_bgs.append(sev_bg_map[sev])

    t = Table(rows, colWidths=[3*cm, 1.8*cm, 12.2*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 9),
        ("ALIGN",          (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), row_bgs[1:]),
        ("GRID",           (0, 0), (-1, -1), 0.4, MID_GREY),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",       (0, 1), (-1, -1), 8.5),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(
        "Immediate remediation of Critical findings is strongly recommended. "
        "High findings should be resolved in the current sprint. "
        "Medium and Low findings can be scheduled in upcoming maintenance windows.",
        S["body"]
    ))
    story.append(PageBreak())
    return story


# ─────────────────────────── Scope & Architecture ─────────────────────────

def build_scope(meta: dict) -> list:
    story = []
    story.append(Paragraph("Scope & Architecture Overview", S["section"]))
    story.append(hr(color=HIGHLIGHT, thickness=1.5))

    scope_rows = meta.get("scope_rows", [])
    if len(scope_rows) > 1:
        story.append(Paragraph("In-Scope Components", S["subsection"]))
        n_cols = len(scope_rows[0])
        col_w  = 17.1 * cm / n_cols
        t = Table(_para_rows(scope_rows, S["body_small"]), colWidths=[col_w] * n_cols)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), ACCENT_BLUE),
            ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
            ("GRID",           (0, 0), (-1, -1), 0.3, MID_GREY),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",     (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
            ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

    flow = meta.get("data_flow_summary", "")
    if flow:
        story.append(Paragraph("Data Flow Architecture", S["subsection"]))
        story.append(Paragraph(flow, S["body"]))
        story.append(Spacer(1, 0.3 * cm))

    ext_deps = meta.get("external_deps", [])
    if len(ext_deps) > 1:
        story.append(Paragraph("External Dependencies", S["subsection"]))
        n_cols = len(ext_deps[0])
        col_w  = 17.1 * cm / n_cols
        dt = Table(_para_rows(ext_deps, S["body_small"]), colWidths=[col_w] * n_cols)
        dt.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), ACCENT_BLUE),
            ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
            ("GRID",           (0, 0), (-1, -1), 0.3, MID_GREY),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",     (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
            ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ]))
        story.append(dt)

    story.append(PageBreak())
    return story


# ─────────────────────────── Finding Card ─────────────────────────────────

def finding_card(f: dict) -> object:
    fid      = f.get("id", "VUL-???")
    title    = f.get("title", "Untitled Finding")
    sev      = f.get("severity", "INFO").upper()
    cvss     = f.get("cvss", "N/A")
    location = f.get("location", "Unknown")
    desc     = f.get("description", "")
    impact   = f.get("impact", "")
    evidence    = f.get("evidence", "")
    remed       = f.get("remediation", "")
    refs        = f.get("references", "")
    cvss_vector = f.get("cvss_vector", "")

    fc_hex = SEV_COLOR_HEX.get(sev, "#1A1A1A")
    bg     = SEV_BG.get(sev, LIGHT_GREY)

    elements = []

    # Header bar: ID | Title | CVSS (+ optional vector) | Severity
    cvss_cell_content = f"<b>CVSS: {cvss}</b>"
    if cvss_vector:
        cvss_cell_content += f'<br/><font name="Courier" size="6.5" color="#AAAAAA">{_esc(cvss_vector)}</font>'
    header_data = [[
        Paragraph(f"<b>{fid}</b>",
            ParagraphStyle("fh", fontSize=9, textColor=WHITE, fontName="Helvetica-Bold")),
        Paragraph(f"<b>{title}</b>",
            ParagraphStyle("ft", fontSize=10, textColor=WHITE, fontName="Helvetica-Bold")),
        Paragraph(cvss_cell_content,
            ParagraphStyle("fc", fontSize=9, textColor=WHITE,
                           fontName="Helvetica-Bold", alignment=TA_CENTER, leading=13)),
        Paragraph(f"<b>{sev}</b>",
            ParagraphStyle("fs", fontSize=9, textColor=colors.HexColor(fc_hex),
                           fontName="Helvetica-Bold", backColor=bg, alignment=TA_CENTER)),
    ]]
    ht = Table(header_data, colWidths=[1.6*cm, 10.4*cm, 2.2*cm, 2.9*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (2, 0), DARK_BG),
        ("BACKGROUND",    (3, 0), (3, 0), bg),
        ("GRID",          (0, 0), (-1, -1), 0, colors.transparent),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    elements.append(ht)

    def labeled_row(label, content, is_code=False, is_remed=False):
        # All finding text fields may contain raw code/HTML from real codebases —
        # always escape before handing to ReportLab's XML parser.
        if is_remed:
            cell = _remediation_para(content, S["body_small"])
        elif is_code:
            safe = _esc(content).replace("\n", "<br/>")
            cell = Paragraph(safe, S["code"])
        else:
            cell = Paragraph(_esc(content), S["body_small"])
        return [Paragraph(f"<b>{label}</b>", S["label"]), cell]

    detail_rows = [
        labeled_row("Location",    location),
        labeled_row("Description", desc),
        # Impact gets severity colour but content still needs escaping
        [Paragraph("<b>Impact</b>", S["label"]),
         Paragraph(f'<font color="{fc_hex}">{_esc(impact)}</font>', S["body_small"])],
        labeled_row("Evidence",    evidence, is_code=True),
        labeled_row("Remediation", remed, is_remed=True),
    ]
    if refs:
        detail_rows.append(labeled_row("References", refs))

    row_bgs = [WHITE if i % 2 == 0 else LIGHT_GREY for i in range(len(detail_rows))]
    dt = Table(detail_rows, colWidths=[2.5*cm, 14.6*cm])
    dt.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), row_bgs),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GREY),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("FONTSIZE",      (0, 0), (0, -1), 8),
        ("TEXTCOLOR",     (0, 0), (0, -1), colors.HexColor("#555555")),
    ]))
    elements.append(dt)
    elements.append(Spacer(1, 0.5 * cm))
    return KeepTogether(elements)


# ─────────────────────────── Findings Section ─────────────────────────────

def build_findings(findings: list) -> list:
    story = []
    story.append(Paragraph("Detailed Findings", S["section"]))
    story.append(hr(color=HIGHLIGHT, thickness=1.5))
    story.append(Spacer(1, 0.2 * cm))

    order  = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    by_sev = {s: [f for f in findings if f.get("severity","INFO").upper() == s]
              for s in order}

    for sev in order:
        group = by_sev[sev]
        if not group:
            continue
        sev_hex = SEV_COLOR_HEX[sev]
        story.append(Paragraph(
            f'<font color="{sev_hex}">■</font>  {sev} Severity',
            ParagraphStyle("sev_group", fontSize=11, fontName="Helvetica-Bold",
                           textColor=DARK_BG, spaceBefore=12, spaceAfter=6)
        ))
        story.append(hr(color=colors.HexColor(sev_hex), thickness=0.8))
        for f in group:
            story.append(finding_card(f))

    return story


# ─────────────────────────── Remediation Roadmap ──────────────────────────

def build_roadmap(findings: list) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Remediation Roadmap", S["section"]))
    story.append(hr(color=HIGHLIGHT, thickness=1.5))
    story.append(Paragraph(
        "Findings are prioritized by severity. Sprint assignments assume two-week "
        "sprints; adjust to your team's release cadence.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    sprint_map = {"CRITICAL": "Sprint 1", "HIGH": "Sprint 1",
                  "MEDIUM":   "Sprint 2", "LOW":  "Sprint 3", "INFO": "Sprint 3"}
    effort_map = {"CRITICAL": "High",     "HIGH": "Medium",
                  "MEDIUM":   "Medium",   "LOW":  "Low",     "INFO": "Low"}

    road_data = [["ID", "Severity", "CVSS", "Title", "Effort", "Target Sprint"]]
    for f in findings:
        sev = f.get("severity", "INFO").upper()
        road_data.append([
            f.get("id", ""),
            severity_badge(sev),
            f.get("cvss", "N/A"),
            Paragraph(f.get("title", ""), S["body_small"]),
            effort_map.get(sev, "Low"),
            sprint_map.get(sev, "Sprint 3"),
        ])

    col_widths = [1.5*cm, 2.2*cm, 1.4*cm, 7.5*cm, 1.8*cm, 2.7*cm]
    t = Table(road_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 8.5),
        ("ALIGN",          (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [WHITE if i % 2 == 0 else LIGHT_GREY for i in range(len(road_data))]),
        ("GRID",           (0, 0), (-1, -1), 0.3, MID_GREY),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",       (0, 1), (-1, -1), 8),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    return story


# ─────────────────────────── Page Template ────────────────────────────────

def make_on_page(meta: dict, watermark: str = None):
    proj  = meta.get("project_name", "Security Assessment")
    rdate = meta.get("report_date", str(date.today()))

    def on_page(canvas, doc):
        if doc.page <= 1:
            return
        w, h = A4
        canvas.saveState()

        # Header bar
        canvas.setFillColor(DARK_BG)
        canvas.rect(0, h - 0.7*cm, w, 0.7*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(WHITE)
        canvas.drawString(1.5*cm, h - 0.48*cm,
                          f"{proj} — Vulnerability Assessment Report")
        canvas.drawRightString(w - 1.5*cm, h - 0.48*cm,
                               f"CONFIDENTIAL  |  {rdate}")

        # Footer bar
        canvas.setFillColor(ACCENT_BLUE)
        canvas.rect(0, 0, w, 0.6*cm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.5*cm, 0.19*cm, "Security Audit Report")
        canvas.drawRightString(w - 1.5*cm, 0.19*cm, f"Page {doc.page}")

        canvas.setStrokeColor(HIGHLIGHT)
        canvas.setLineWidth(1.2)
        canvas.line(0, 0.62*cm, w, 0.62*cm)

        # Diagonal watermark across page body
        if watermark:
            canvas.saveState()
            canvas.translate(w / 2, h / 2)
            canvas.rotate(45)
            canvas.setFillColorRGB(0.55, 0.55, 0.55)
            canvas.setFillAlpha(0.18)
            canvas.setFont("Helvetica-Bold", 80)
            canvas.drawCentredString(0, 0, watermark.upper())
            canvas.restoreState()

        canvas.restoreState()

    return on_page


# ─────────────────────────── Main Builder ─────────────────────────────────

def build_report(findings_path: str, output_path: str, logo_path: str = None, watermark: str = None):
    with open(findings_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    meta     = {k: v for k, v in data.items() if k != "findings"}
    findings = data.get("findings", [])

    if not findings:
        print("WARNING: No findings in the JSON file. Report will have an empty findings section.")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.2*cm,  bottomMargin=1.2*cm,
        title=f"{meta.get('project_name', 'Security')} — Vulnerability Assessment Report",
        author="Security Audit",
        subject="Vulnerability Assessment Report",
    )

    story = []
    story.extend(build_cover())
    story.extend(build_executive_summary(meta, findings))
    story.extend(build_scope(meta))
    story.extend(build_findings(findings))
    story.extend(build_roadmap(findings))

    doc.build(
        story,
        onFirstPage=lambda c, d: draw_cover_canvas(c, d, meta, logo_path, watermark),
        onLaterPages=make_on_page(meta, watermark),
    )

    print(f"Report written → {output_path}")
    print(f"Findings: {len(findings)} total")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        n = sum(1 for f in findings if f.get("severity","").upper() == sev)
        if n:
            print(f"  {sev}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a professional PDF vulnerability assessment report.")
    parser.add_argument("--findings", required=True,
                        help="Path to the JSON findings file")
    parser.add_argument("--output",   required=True,
                        help="Output PDF path")
    parser.add_argument("--logo",      default=None,
                        help="Optional path to a logo image for the cover page (PNG/JPG)")
    parser.add_argument("--watermark", default=None,
                        help="Optional watermark text on all inner pages (e.g. DRAFT, CONFIDENTIAL)")
    args = parser.parse_args()

    if not os.path.isfile(args.findings):
        print(f"ERROR: Findings file not found: {args.findings}")
        sys.exit(1)

    build_report(args.findings, args.output, args.logo, args.watermark)
