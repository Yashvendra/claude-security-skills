"""
Vulnerability Assessment Report Generator — v2 "Security Intelligence" Design

Dark professional theme:
  • Void-black / space-navy backgrounds on every page
  • Cyan (#00D4FF) accent for borders, headings, page chrome
  • Severity-stripe finding cards (coloured left rail per severity)
  • Visual risk distribution bar + stat boxes in executive summary
  • Cover page with live risk panel (severity counts, hero total)
  • CVSS vector string rendered below score when present

Usage:
    python generate_report_v2.py --findings findings.json --output Report.pdf \
                                 [--logo logo.png] [--watermark "DRAFT"]

JSON schema: identical to generate_report.py; cvss_vector per finding is optional.
"""

import argparse
import json
import os
import sys
from datetime import date
from collections import Counter
from html import escape as _he

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
except ImportError:
    print("ERROR: reportlab is not installed.  Run:  pip install reportlab")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
#  PALETTE  —  "Security Intelligence"
# ══════════════════════════════════════════════════════════════════════════

# Backgrounds
VOID        = colors.HexColor("#070C14")   # cover
BODY_BG     = colors.HexColor("#0B1421")   # body pages
HDR_BG      = colors.HexColor("#060C17")   # page header / footer bars
SURF_1      = colors.HexColor("#101E30")   # cards / table rows
SURF_2      = colors.HexColor("#152439")   # alternating rows
SURF_3      = colors.HexColor("#070F1C")   # code blocks

# Borders
BORDER      = colors.HexColor("#1C2E44")
BORDER_LT   = colors.HexColor("#243851")

# Cyan accent
CYAN        = colors.HexColor("#00D4FF")
CYAN_DIM    = colors.HexColor("#003346")

# Text
TEXT_1      = colors.HexColor("#DCE8F5")   # primary
TEXT_2      = colors.HexColor("#7B94AE")   # secondary / labels
TEXT_3      = colors.HexColor("#3D5268")   # muted
WHITE       = colors.white

# Severity — vivid, high-contrast on dark
SEV_COLOR = {
    "CRITICAL": colors.HexColor("#FF2D55"),
    "HIGH":     colors.HexColor("#FF6B35"),
    "MEDIUM":   colors.HexColor("#FFB800"),
    "LOW":      colors.HexColor("#00CF83"),
    "INFO":     colors.HexColor("#5B9BF9"),
}
SEV_BG = {
    "CRITICAL": colors.HexColor("#200008"),
    "HIGH":     colors.HexColor("#200E00"),
    "MEDIUM":   colors.HexColor("#201800"),
    "LOW":      colors.HexColor("#00200E"),
    "INFO":     colors.HexColor("#071425"),
}
SEV_HEX = {
    "CRITICAL": "#FF2D55",
    "HIGH":     "#FF6B35",
    "MEDIUM":   "#FFB800",
    "LOW":      "#00CF83",
    "INFO":     "#5B9BF9",
}
ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# Document content width (A4 21cm − 1.5cm × 2 margins)
CW = 18.0 * cm


# ══════════════════════════════════════════════════════════════════════════
#  PARAGRAPH STYLES
# ══════════════════════════════════════════════════════════════════════════

def _build_styles():
    S = {}
    S["section"] = ParagraphStyle(
        "v2_section", fontSize=15, textColor=WHITE,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=3, leading=19)
    S["subsection"] = ParagraphStyle(
        "v2_sub", fontSize=10.5, textColor=CYAN,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4, leading=14)
    S["body"] = ParagraphStyle(
        "v2_body", fontSize=9, textColor=TEXT_1,
        fontName="Helvetica", leading=14, alignment=TA_JUSTIFY, spaceAfter=5)
    S["body_sm"] = ParagraphStyle(
        "v2_body_sm", fontSize=8, textColor=TEXT_1,
        fontName="Helvetica", leading=12, spaceAfter=3)
    S["label"] = ParagraphStyle(
        "v2_label", fontSize=7.5, textColor=TEXT_2,
        fontName="Helvetica-Bold", leading=10)
    S["code"] = ParagraphStyle(
        "v2_code", fontSize=7, textColor=colors.HexColor("#7EC8E3"),
        fontName="Courier", leading=10.5, backColor=SURF_3,
        leftIndent=6, rightIndent=6, spaceBefore=2, spaceAfter=2, borderPad=4)
    S["muted"] = ParagraphStyle(
        "v2_muted", fontSize=7, textColor=TEXT_3,
        fontName="Helvetica", leading=10)
    return S

S = _build_styles()


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _esc(text: str) -> str:
    return _he(str(text), quote=False).replace("&lt;br/&gt;", "<br/>")

def _cyan_rule(before=6, after=6):
    return HRFlowable(width="100%", thickness=1.5,
                      color=CYAN, spaceBefore=before, spaceAfter=after)

def _dim_rule(before=3, after=3):
    return HRFlowable(width="100%", thickness=0.4,
                      color=BORDER, spaceBefore=before, spaceAfter=after)

def _severity_badge(sev: str) -> Paragraph:
    sev = sev.upper()
    fg  = SEV_HEX.get(sev, "#FFFFFF")
    return Paragraph(
        f'<font color="{fg}"><b> {sev} </b></font>',
        ParagraphStyle("v2_badge", fontSize=7.5,
                       fontName="Helvetica-Bold",
                       alignment=TA_CENTER, leading=10))

def _dark_tbl_style():
    """Standard dark-theme table style."""
    return TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  SURF_2),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  TEXT_2),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0),  8),
        ("ALIGN",          (0, 0), (-1, 0),  "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SURF_1, SURF_2]),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",       (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",      (0, 1), (-1, -1), TEXT_1),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
    ])

def _para_rows(rows, body_style, hdr_color=TEXT_2):
    """Wrap every string cell in a Paragraph for word-wrap support."""
    hdr_style = ParagraphStyle("_th", fontSize=8, fontName="Helvetica-Bold",
                               textColor=hdr_color, leading=11)
    result = []
    for r_idx, row in enumerate(rows):
        st = hdr_style if r_idx == 0 else body_style
        result.append([
            cell if not isinstance(cell, str) else Paragraph(cell, st)
            for cell in row
        ])
    return result


# ══════════════════════════════════════════════════════════════════════════
#  COVER PAGE  (all canvas-drawn)
# ══════════════════════════════════════════════════════════════════════════

def draw_cover(canvas, doc, meta: dict, logo_path=None, watermark=None):
    w, h = A4
    canvas.saveState()

    # ── Full void background ─────────────────────────────────────────────
    canvas.setFillColor(VOID)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # ── Subtle grid (bottom-right quadrant) ─────────────────────────────
    canvas.setStrokeColor(colors.HexColor("#0D1A28"))
    canvas.setLineWidth(0.3)
    gs = 26  # grid spacing (points)
    for gx in range(int(w * 0.46), int(w) + gs, gs):
        canvas.line(gx, 0, gx, int(h * 0.62))
    for gy in range(0, int(h * 0.62) + gs, gs):
        canvas.line(int(w * 0.46), gy, int(w), gy)

    # ── Top cyan bar ─────────────────────────────────────────────────────
    canvas.setFillColor(CYAN)
    canvas.rect(0, h - 0.48 * cm, w, 0.48 * cm, fill=1, stroke=0)

    # ── Left content panel ───────────────────────────────────────────────
    canvas.setFillColor(colors.HexColor("#0C1624"))
    canvas.roundRect(0.65*cm, h*0.11, w*0.57, h*0.77, 8, fill=1, stroke=0)

    # ── Logo ─────────────────────────────────────────────────────────────
    if logo_path and os.path.isfile(logo_path):
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            if ih > 0:
                aspect = iw / ih
                lh = 1.3 * cm
                lw = min(lh * aspect, 4.0 * cm)
                lx, ly = 1.3 * cm, h * 0.81
                canvas.setFillColor(WHITE)
                canvas.roundRect(lx - 0.25*cm, ly - 0.15*cm,
                                 lw + 0.5*cm, lh + 0.3*cm, 4, fill=1, stroke=0)
                canvas.drawImage(logo_path, lx, ly, lw, lh,
                                 mask="auto", preserveAspectRatio=True)
        except Exception:
            pass

    # ── "SECURITY AUDIT REPORT" label ───────────────────────────────────
    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(1.3*cm, h * 0.785, "SECURITY AUDIT REPORT")

    # Thin separator
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(1.3*cm, h*0.782 - 3, w*0.60, h*0.782 - 3)

    # ── Main title ───────────────────────────────────────────────────────
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 34)
    canvas.drawString(1.3*cm, h * 0.715, "VULNERABILITY")
    canvas.drawString(1.3*cm, h * 0.668, "ASSESSMENT")

    # Cyan underline accent
    canvas.setFillColor(CYAN)
    canvas.rect(1.3*cm, h * 0.655, 3.8*cm, 0.18*cm, fill=1, stroke=0)

    # ── Project name ─────────────────────────────────────────────────────
    proj = meta.get("project_name", "Security Assessment")
    if len(proj) > 38:
        proj = proj[:36] + "…"
    canvas.setFillColor(colors.HexColor("#8FB8D4"))
    canvas.setFont("Helvetica", 13)
    canvas.drawString(1.3*cm, h * 0.607, proj)

    # ── Metadata block ───────────────────────────────────────────────────
    branch = meta.get("branch", "")
    meta_rows = [
        ("Target",   meta.get("target_path", "—")),
        ("Language", meta.get("language", "—")),
        ("Type",     meta.get("assessment_type", "Static Code Review")),
        ("Date",     meta.get("report_date", str(date.today()))),
    ]
    if branch and branch.lower() not in ("", "n/a", "none"):
        meta_rows.insert(1, ("Branch", branch))

    my = h * 0.552
    for label, val in meta_rows:
        if len(val) > 52:
            val = val[:50] + "…"
        canvas.setFillColor(TEXT_2)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(1.3*cm, my, f"{label}:")
        canvas.setFillColor(TEXT_1)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(3.0*cm, my, val)
        my -= 0.46*cm

    # ── CONFIDENTIAL badge ───────────────────────────────────────────────
    canvas.setFillColor(colors.HexColor("#FF2D55"))
    canvas.roundRect(1.3*cm, h*0.135, 3.0*cm, 0.52*cm, 4, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawCentredString(1.3*cm + 1.5*cm, h*0.135 + 0.17*cm, "CONFIDENTIAL")

    # ── Right panel: Risk Summary ─────────────────────────────────────────
    findings = meta.get("_findings_list", [])
    counts   = Counter(f.get("severity", "INFO").upper() for f in findings)
    total    = len(findings)

    px = w * 0.635
    pw = w - px - 0.65*cm
    py = h * 0.185
    ph = h * 0.60

    # Panel background + border
    canvas.setFillColor(colors.HexColor("#090F1C"))
    canvas.roundRect(px, py, pw, ph, 10, fill=1, stroke=0)
    canvas.setStrokeColor(BORDER_LT)
    canvas.setLineWidth(0.6)
    canvas.roundRect(px, py, pw, ph, 10, fill=0, stroke=1)

    # Top cyan accent strip on panel
    canvas.setFillColor(CYAN)
    canvas.roundRect(px, py + ph - 0.45*cm, pw, 0.45*cm, 10, fill=1, stroke=0)
    # Cover bottom-rounded corners of the strip
    canvas.rect(px, py + ph - 0.45*cm, pw, 0.25*cm, fill=1, stroke=0)

    canvas.setFillColor(colors.HexColor("#000D18"))
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawCentredString(px + pw/2, py + ph - 0.32*cm, "RISK SUMMARY")

    # Hero: total findings
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 42)
    canvas.drawCentredString(px + pw/2, py + ph - 2.3*cm, str(total))
    canvas.setFillColor(TEXT_2)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(px + pw/2, py + ph - 2.85*cm,
                             "finding" + ("s" if total != 1 else ""))

    # Thin separator
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(px + 0.5*cm, py + ph - 3.2*cm, px + pw - 0.5*cm, py + ph - 3.2*cm)

    # Severity rows
    bh   = 0.88*cm   # box height
    bgap = 0.28*cm   # gap between boxes
    start_y = py + ph - 3.5*cm

    for i, sev in enumerate(ORDER):
        cnt   = counts[sev]
        by    = start_y - i * (bh + bgap)
        bx    = px + 0.45*cm
        bw    = pw - 0.9*cm
        sc    = SEV_COLOR[sev]
        sbg   = SEV_BG[sev]

        # Box background
        canvas.setFillColor(sbg)
        canvas.roundRect(bx, by, bw, bh, 4, fill=1, stroke=0)
        canvas.setStrokeColor(sc)
        canvas.setLineWidth(0.6)
        canvas.roundRect(bx, by, bw, bh, 4, fill=0, stroke=1)

        # Left severity stripe
        canvas.setFillColor(sc)
        canvas.roundRect(bx, by, 0.22*cm, bh, 4, fill=1, stroke=0)
        canvas.rect(bx + 0.1*cm, by, 0.12*cm, bh, fill=1, stroke=0)

        # Label
        canvas.setFillColor(sc)
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.drawString(bx + 0.42*cm, by + bh * 0.52, sev)

        # Count
        canvas.setFillColor(WHITE if cnt > 0 else TEXT_3)
        canvas.setFont("Helvetica-Bold", 17)
        canvas.drawRightString(bx + bw - 0.35*cm, by + bh * 0.22, str(cnt))

    # ── Watermark ────────────────────────────────────────────────────────
    if watermark:
        canvas.saveState()
        canvas.translate(w / 2, h / 2)
        canvas.rotate(45)
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        canvas.setFillAlpha(0.12)
        canvas.setFont("Helvetica-Bold", 80)
        canvas.drawCentredString(0, 0, watermark.upper())
        canvas.restoreState()

    canvas.restoreState()


def build_cover():
    return [PageBreak()]


# ══════════════════════════════════════════════════════════════════════════
#  PAGE TEMPLATE  (dark background + header/footer on every body page)
# ══════════════════════════════════════════════════════════════════════════

def make_on_page(meta: dict, watermark=None):
    proj  = meta.get("project_name", "Security Assessment")
    rdate = meta.get("report_date", str(date.today()))

    def on_page(canvas, doc):
        if doc.page <= 1:
            return
        w, h = A4
        canvas.saveState()

        # Full dark background
        canvas.setFillColor(BODY_BG)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)

        # Header bar
        canvas.setFillColor(HDR_BG)
        canvas.rect(0, h - 0.9*cm, w, 0.9*cm, fill=1, stroke=0)
        # Cyan left accent on header
        canvas.setFillColor(CYAN)
        canvas.rect(0, h - 0.9*cm, 0.38*cm, 0.9*cm, fill=1, stroke=0)

        canvas.setFillColor(TEXT_2)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(0.82*cm, h - 0.55*cm,
                          f"{proj}  ·  Vulnerability Assessment Report")
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - 0.65*cm, h - 0.55*cm,
                               f"CONFIDENTIAL  |  {rdate}")

        # Footer bar
        canvas.setFillColor(HDR_BG)
        canvas.rect(0, 0, w, 0.72*cm, fill=1, stroke=0)
        # Cyan right accent on footer
        canvas.setFillColor(CYAN)
        canvas.rect(w - 0.38*cm, 0, 0.38*cm, 0.72*cm, fill=1, stroke=0)

        canvas.setFillColor(TEXT_3)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(0.65*cm, 0.24*cm, "CONFIDENTIAL — Internal Use Only")
        canvas.setFillColor(CYAN)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawRightString(w - 0.72*cm, 0.24*cm, f"PAGE {doc.page}")

        # Separator lines
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.3)
        canvas.line(0, h - 0.9*cm, w, h - 0.9*cm)
        canvas.line(0, 0.72*cm, w, 0.72*cm)

        # Watermark
        if watermark:
            canvas.saveState()
            canvas.translate(w / 2, h / 2)
            canvas.rotate(45)
            canvas.setFillColorRGB(0.5, 0.5, 0.5)
            canvas.setFillAlpha(0.07)
            canvas.setFont("Helvetica-Bold", 80)
            canvas.drawCentredString(0, 0, watermark.upper())
            canvas.restoreState()

        canvas.restoreState()

    return on_page


# ══════════════════════════════════════════════════════════════════════════
#  EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════

def build_executive_summary(meta: dict, findings: list) -> list:
    story = []
    story.append(Paragraph("Executive Summary", S["section"]))
    story.append(_cyan_rule(before=2, after=8))

    # Intro
    proj  = meta.get("project_name", "the target system")
    lang  = meta.get("language", "")
    fw    = meta.get("framework", "")
    atype = meta.get("assessment_type", "Static Code Review + Architecture Audit")
    stack = lang + (f" / {fw}" if fw and fw.lower() not in ("", "none") else "")
    intro = (
        f"An in-depth {atype.lower()} was conducted on the <b>{proj}</b> codebase"
        + (f" ({stack})" if stack else "")
        + ". The assessment examined data flows, trust boundaries, authentication "
          "mechanisms, external integrations, and all code paths handling untrusted input."
    )
    story.append(Paragraph(intro, S["body"]))
    story.append(Spacer(1, 0.3*cm))

    counts = Counter(f.get("severity", "INFO").upper() for f in findings)
    total  = len(findings)

    # ── Severity stat boxes (one per severity level) ──────────────────────
    stat_cells = []
    for sev in ORDER:
        cnt    = counts[sev]
        fg_hex = SEV_HEX[sev]
        bg     = SEV_BG[sev]
        cell_p = Paragraph(
            f'<font color="{fg_hex}" size="7"><b>{sev}</b></font><br/>'
            f'<font color="#FFFFFF" size="22"><b>{cnt}</b></font>',
            ParagraphStyle("stat_v2", fontSize=7, alignment=TA_CENTER,
                           leading=28, spaceBefore=5, spaceAfter=5))
        stat_cells.append(cell_p)

    stat_t = Table([stat_cells], colWidths=[CW / 5] * 5)
    # Apply per-cell background (TableStyle ROWBACKGROUNDS won't respect individual bg here)
    style_cmds = [
        ("GRID",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",     (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
    ]
    for i, sev in enumerate(ORDER):
        style_cmds.append(("BACKGROUND", (i, 0), (i, 0), SEV_BG[sev]))
    stat_t.setStyle(TableStyle(style_cmds))
    story.append(stat_t)
    story.append(Spacer(1, 0.25*cm))

    # ── Risk distribution bar ─────────────────────────────────────────────
    if total > 0:
        bar_cells, bar_widths = [], []
        for sev in ORDER:
            cnt = counts[sev]
            if cnt == 0:
                continue
            bar_widths.append(max((cnt / total) * CW, 0.7*cm))
            bar_cells.append(Paragraph(
                f'<font color="#000000" size="7"><b>{cnt}</b></font>',
                ParagraphStyle("bar_v2", fontSize=7, alignment=TA_CENTER,
                               textColor=colors.black, leading=9)))

        # Normalise to exactly CW
        tw = sum(bar_widths)
        bar_widths = [bw * CW / tw for bw in bar_widths]

        bar_t = Table([bar_cells], colWidths=bar_widths)
        i_sev = 0
        for sev in ORDER:
            if counts[sev] == 0:
                continue
            bar_t.setStyle(TableStyle([
                ("BACKGROUND",    (i_sev, 0), (i_sev, 0), SEV_COLOR[sev]),
                ("TOPPADDING",    (i_sev, 0), (i_sev, 0), 4),
                ("BOTTOMPADDING", (i_sev, 0), (i_sev, 0), 4),
            ]))
            i_sev += 1
        story.append(bar_t)
        story.append(Spacer(1, 0.12*cm))

        # Legend
        legend = " · ".join(
            f'<font color="{SEV_HEX[s]}">{s}</font>'
            for s in ORDER if counts[s] > 0)
        story.append(Paragraph(legend, ParagraphStyle(
            "legend_v2", fontSize=7, textColor=TEXT_2,
            alignment=TA_CENTER, leading=10)))
        story.append(Spacer(1, 0.3*cm))

    # ── Summary sentence ─────────────────────────────────────────────────
    sev_parts = [f"<b>{counts[s]}</b> {s.lower()}" for s in ORDER if counts[s]]
    story.append(Paragraph(
        f"The assessment identified <b>{total} distinct security finding"
        f"{'s' if total != 1 else ''}</b> ({', '.join(sev_parts)}). "
        "CRITICAL and HIGH findings represent immediate risk and should be resolved "
        "before any production deployment or release. MEDIUM findings should be "
        "addressed in the current sprint.",
        S["body"]))
    story.append(Spacer(1, 0.3*cm))

    # ── Summary table ─────────────────────────────────────────────────────
    by_sev = {s: [f["title"] for f in findings if f.get("severity","").upper() == s]
              for s in ORDER}
    rows = [["Severity", "Count", "Representative Findings"]]
    for sev in ORDER:
        if not counts[sev]:
            continue
        titles   = by_sev[sev]
        rep_text = " · ".join(titles[:3]) + (" · …" if len(titles) > 3 else "")
        rows.append([_severity_badge(sev), str(counts[sev]),
                     Paragraph(rep_text, S["body_sm"])])

    t = Table(_para_rows(rows, S["body_sm"]), colWidths=[3.0*cm, 1.8*cm, 13.2*cm])
    t.setStyle(_dark_tbl_style())
    story.append(t)
    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════════════════
#  SCOPE & ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════

def build_scope(meta: dict) -> list:
    story = []
    story.append(Paragraph("Scope & Architecture", S["section"]))
    story.append(_cyan_rule(before=2, after=8))

    scope_rows = meta.get("scope_rows", [])
    if len(scope_rows) > 1:
        story.append(Paragraph("In-Scope Components", S["subsection"]))
        n = len(scope_rows[0])
        t = Table(_para_rows(scope_rows, S["body_sm"]),
                  colWidths=[CW / n] * n)
        t.setStyle(_dark_tbl_style())
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    flow = meta.get("data_flow_summary", "")
    if flow:
        story.append(Paragraph("Data Flow Overview", S["subsection"]))
        story.append(Paragraph(flow, S["body"]))
        story.append(Spacer(1, 0.3*cm))

    ext = meta.get("external_deps", [])
    if len(ext) > 1:
        story.append(Paragraph("External Dependencies", S["subsection"]))
        n = len(ext[0])
        t = Table(_para_rows(ext, S["body_sm"]), colWidths=[CW / n] * n)
        t.setStyle(_dark_tbl_style())
        story.append(t)

    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════════════════
#  FINDING CARD
#
#  Layout (all widths sum to CW = 18.0 cm):
#
#  ┌─────────────────────────────────────────────────────────────────────┐
#  │stripe│  ID badge  │  Title                    │  CVSS   │  SEV     │
#  │ 0.35 │  1.50      │  10.60                    │  2.20   │  3.35    │
#  ├─────────────────────────────────────────────────────────────────────┤
#  │stripe│  Label     │  Content value                                  │
#  │ 0.35 │  2.30      │  15.35                                          │
#  └─────────────────────────────────────────────────────────────────────┘
#
#  The stripe column (0.35 cm wide, severity colour) runs the full card
#  height — achieved by using the same first column in both sub-tables.
# ══════════════════════════════════════════════════════════════════════════

_STRIPE  = 0.35 * cm
_ID_W    = 1.50 * cm
_TITLE_W = 10.60 * cm
_CVSS_W  = 2.20 * cm
_SEV_W   = 3.35 * cm   # = CW - _STRIPE - _ID_W - _TITLE_W - _CVSS_W
_LABEL_W = 2.30 * cm
_VAL_W   = CW - _STRIPE - _LABEL_W   # 15.35 cm


def _stripe_para(bg_color) -> str:
    """Returns an empty string — the stripe colour is applied via TableStyle BACKGROUND."""
    return ""


def finding_card(f: dict):
    sev      = f.get("severity", "INFO").upper()
    fid      = f.get("id", "VUL-???")
    title    = f.get("title", "Untitled")
    cvss     = f.get("cvss", "N/A")
    cvss_vec = f.get("cvss_vector", "")
    location = f.get("location", "Unknown")
    desc     = f.get("description", "")
    impact   = f.get("impact", "")
    evidence = f.get("evidence", "")
    remed    = f.get("remediation", "")
    refs     = f.get("references", "")

    fg_hex = SEV_HEX.get(sev, "#FFFFFF")
    fg_col = SEV_COLOR.get(sev, WHITE)
    bg_col = SEV_BG.get(sev, SURF_1)

    # ── Header row ────────────────────────────────────────────────────────
    cvss_label = f"<b>CVSS {cvss}</b>"
    if cvss_vec:
        cvss_label += (f'<br/><font name="Courier" size="5.5"'
                       f' color="#446677">{_esc(cvss_vec)}</font>')

    hdr_data = [[
        _stripe_para(fg_col),
        Paragraph(f'<font color="{fg_hex}"><b>{fid}</b></font>',
            ParagraphStyle("_fid", fontSize=8.5, textColor=fg_col,
                           fontName="Helvetica-Bold",
                           alignment=TA_CENTER, leading=11)),
        Paragraph(f"<b>{_esc(title)}</b>",
            ParagraphStyle("_ftitle", fontSize=9.5, textColor=WHITE,
                           fontName="Helvetica-Bold", leading=13)),
        Paragraph(cvss_label,
            ParagraphStyle("_fcvss", fontSize=7.5, textColor=TEXT_2,
                           fontName="Helvetica-Bold", alignment=TA_CENTER,
                           leading=11)),
        Paragraph(f'<font color="{fg_hex}"><b>{sev}</b></font>',
            ParagraphStyle("_fsev", fontSize=8, textColor=fg_col,
                           fontName="Helvetica-Bold",
                           alignment=TA_CENTER, leading=11)),
    ]]

    hdr = Table(hdr_data, colWidths=[_STRIPE, _ID_W, _TITLE_W, _CVSS_W, _SEV_W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), fg_col),
        ("BACKGROUND",    (1, 0), (1, 0), bg_col),
        ("BACKGROUND",    (2, 0), (3, 0), SURF_1),
        ("BACKGROUND",    (4, 0), (4, 0), bg_col),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.5, fg_col),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("GRID",          (0, 0), (-1, -1), 0, colors.transparent),
    ]))

    # ── Detail rows ───────────────────────────────────────────────────────
    def _row(label, content, is_code=False):
        label_p = Paragraph(f"<b>{label}</b>", S["label"])
        if is_code:
            val_p = Paragraph(_esc(content).replace("\n", "<br/>"), S["code"])
        else:
            val_p = Paragraph(_esc(content), S["body_sm"])
        return [_stripe_para(fg_col), label_p, val_p]

    impact_p = Paragraph(
        f'<font color="{fg_hex}">{_esc(impact)}</font>', S["body_sm"])

    detail_rows = [
        _row("Location",    location),
        _row("Description", desc),
        [_stripe_para(fg_col), Paragraph("<b>Impact</b>", S["label"]), impact_p],
        _row("Evidence",    evidence, is_code=True),
        _row("Remediation", remed),
    ]
    if refs:
        detail_rows.append(_row("References", refs))

    row_bgs = [SURF_1 if i % 2 == 0 else SURF_2 for i in range(len(detail_rows))]

    dt = Table(detail_rows, colWidths=[_STRIPE, _LABEL_W, _VAL_W])
    style_cmds = [
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("FONTSIZE",      (1, 0), (1, -1), 7.5),
        ("TEXTCOLOR",     (1, 0), (1, -1), TEXT_2),
    ]
    for i, bg in enumerate(row_bgs):
        style_cmds.append(("BACKGROUND", (1, i), (2, i), bg))
        style_cmds.append(("BACKGROUND", (0, i), (0, i), fg_col))
    dt.setStyle(TableStyle(style_cmds))

    return KeepTogether([hdr, dt, Spacer(1, 0.55*cm)])


# ══════════════════════════════════════════════════════════════════════════
#  FINDINGS SECTION
# ══════════════════════════════════════════════════════════════════════════

def build_findings(findings: list) -> list:
    story = []
    story.append(Paragraph("Detailed Findings", S["section"]))
    story.append(_cyan_rule(before=2, after=8))
    story.append(Spacer(1, 0.15*cm))

    by_sev = {s: [f for f in findings if f.get("severity","INFO").upper() == s]
              for s in ORDER}

    for sev in ORDER:
        group = by_sev[sev]
        if not group:
            continue
        fg_hex = SEV_HEX[sev]
        story.append(Paragraph(
            f'<font color="{fg_hex}">■</font>  {sev} Severity',
            ParagraphStyle("sev_grp", fontSize=10, fontName="Helvetica-Bold",
                           textColor=WHITE, spaceBefore=10, spaceAfter=4)))
        story.append(HRFlowable(width="100%", thickness=0.8,
                                color=SEV_COLOR[sev], spaceBefore=0, spaceAfter=6))
        for f in group:
            story.append(finding_card(f))

    return story


# ══════════════════════════════════════════════════════════════════════════
#  REMEDIATION ROADMAP
# ══════════════════════════════════════════════════════════════════════════

def build_roadmap(findings: list) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Remediation Roadmap", S["section"]))
    story.append(_cyan_rule(before=2, after=8))
    story.append(Paragraph(
        "Findings are prioritised by severity. Sprint assignments assume two-week "
        "sprints — adjust to your team's release cadence.",
        S["body"]))
    story.append(Spacer(1, 0.3*cm))

    sprint_map = {"CRITICAL": "Sprint 1", "HIGH": "Sprint 1",
                  "MEDIUM":   "Sprint 2", "LOW":  "Sprint 3", "INFO": "Backlog"}
    effort_map = {"CRITICAL": "Critical", "HIGH": "High",
                  "MEDIUM":   "Medium",   "LOW":  "Low",     "INFO": "Low"}

    road_rows = [["ID", "Severity", "CVSS", "Title", "Effort", "Sprint"]]
    for f in findings:
        sev = f.get("severity", "INFO").upper()
        road_rows.append([
            f.get("id", ""),
            _severity_badge(sev),
            f.get("cvss", "N/A"),
            Paragraph(f.get("title", ""), S["body_sm"]),
            effort_map.get(sev, "Low"),
            sprint_map.get(sev, "Backlog"),
        ])

    t = Table(road_rows, colWidths=[1.5*cm, 2.4*cm, 1.4*cm, 8.0*cm, 1.8*cm, 2.9*cm])
    t.setStyle(_dark_tbl_style())
    story.append(t)
    return story


# ══════════════════════════════════════════════════════════════════════════
#  MAIN BUILDER
# ══════════════════════════════════════════════════════════════════════════

def build_report(findings_path: str, output_path: str,
                 logo_path: str = None, watermark: str = None):
    with open(findings_path, encoding="utf-8") as fh:
        data = json.load(fh)

    meta     = {k: v for k, v in data.items() if k != "findings"}
    findings = data.get("findings", [])

    # Stash findings list for the cover page risk panel
    meta["_findings_list"] = findings

    if not findings:
        print("WARNING: No findings found in JSON. Report will have an empty findings section.")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2.1*cm,  bottomMargin=1.6*cm,
        title=f"{meta.get('project_name','Security')} — Vulnerability Assessment Report",
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
        onFirstPage=lambda c, d: draw_cover(c, d, meta, logo_path, watermark),
        onLaterPages=make_on_page(meta, watermark),
    )

    counts = Counter(f.get("severity", "").upper() for f in findings)
    print(f"Report written → {output_path}")
    print(f"Findings: {len(findings)} total")
    for sev in ORDER:
        if counts[sev]:
            print(f"  {sev}: {counts[sev]}")


# ══════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a v2 'Security Intelligence' PDF vulnerability report.")
    parser.add_argument("--findings",  required=True,
                        help="Path to the JSON findings file")
    parser.add_argument("--output",    required=True,
                        help="Output PDF path")
    parser.add_argument("--logo",      default=None,
                        help="Optional logo image (PNG/JPG) for the cover page")
    parser.add_argument("--watermark", default=None,
                        help="Optional watermark text on all inner pages (e.g. DRAFT)")
    args = parser.parse_args()

    if not os.path.isfile(args.findings):
        print(f"ERROR: Findings file not found: {args.findings}")
        sys.exit(1)

    build_report(args.findings, args.output, args.logo, args.watermark)
