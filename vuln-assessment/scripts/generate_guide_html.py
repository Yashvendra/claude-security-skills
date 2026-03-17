#!/usr/bin/env python3
"""
generate_guide_html.py
======================
Developer Remediation Guide Generator — Markdown + JSON → HTML → Chrome-headless → PDF

Reads a _Developer_Remediation_Guide.md and _vuln_findings.json, then produces a
professional A4 PDF guide using Arial fonts and the navy/blue/grey palette that
matches generate_guide_docx.js exactly.

Usage:
    python generate_guide_html.py \\
        --guide   vulnapp_Developer_Remediation_Guide.md \\
        --findings _vuln_findings.json \\
        --output  vulnapp_Developer_Remediation_Guide.pdf

Requirements:
    - Python 3.8+
    - Google Chrome or Chromium installed
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ─── Chrome detection ────────────────────────────────────────────────────────

CHROME_CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]

def find_chrome() -> str:
    for name in CHROME_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    return ""


# ─── Severity helpers ────────────────────────────────────────────────────────

SEV_COLOR = {
    "CRITICAL": "#C0392B",
    "HIGH":     "#D35400",
    "MEDIUM":   "#B7770D",
    "LOW":      "#1E7E34",
    "INFO":     "#6B7280",
}

SEV_BG = {
    "CRITICAL": "#FDECEA",
    "HIGH":     "#FEF0E7",
    "MEDIUM":   "#FEF9E7",
    "LOW":      "#EAF5EA",
    "INFO":     "#F4F5F6",
}

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


# ─── CSS ─────────────────────────────────────────────────────────────────────

CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* @page margin: 0 — position:fixed top:0/bottom:0 maps to physical page edges in Chrome.
   Sections compensate with padding-top/bottom to clear the fixed header/footer. */
@page          { size: A4; margin: 0; }
@page :first   { margin: 0; }

html, body {
  width: 210mm;
  font-family: Arial, Helvetica, sans-serif;
  background: #fff;
  color: #222222;
  font-size: 9.5pt;
  line-height: 1.55;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  overflow-x: hidden;
  scrollbar-width: none;
}
::-webkit-scrollbar { display: none; }

:root {
  --navy:     #1F3864;
  --blue:     #2E5090;
  --grey:     #444444;
  --codebg:   #F4F4F4;
  --callout:  #EBF3FB;
  --calloutbd:#2E5090;
  --border:   #CCCCCC;
  --pad:      16mm;
}

/* ── Fixed header ─────────────────────────────────────────────────────── */
.fixed-header {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 11mm;
  background: var(--navy);
  display: flex;
  align-items: stretch;
  z-index: 10;
}
.fh-accent { width: 4mm; background: var(--blue); flex-shrink: 0; }
.fh-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 7mm;
}
.fh-left {
  font-size: 6pt;
  letter-spacing: 0.14em;
  color: rgba(255,255,255,0.55);
  text-transform: uppercase;
  font-weight: bold;
}
.fh-right {
  font-size: 6pt;
  color: rgba(255,255,255,0.35);
  letter-spacing: 0.10em;
}

/* ── Fixed footer ─────────────────────────────────────────────────────── */
/* With @page margin:0, bottom:0 maps to the physical page bottom in Chrome. */
.fixed-footer {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 9mm;
  border-top: 0.5px solid #DDDDDD;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 7mm;
  z-index: 10;
}
.ff-left  { font-size: 5.5pt; color: #888888; letter-spacing: 0.08em; }
.ff-right { font-size: 5.5pt; color: #888888; font-family: 'Courier New', monospace; }

/* ── Cover ────────────────────────────────────────────────────────────── */
.cover {
  width: 210mm;
  height: 297mm;
  background: var(--navy);
  position: relative;
  z-index: 999;
  break-after: page;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.cover-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 12mm 12mm;
}
.cover-accent-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--blue);
}
.cover-body {
  position: relative;
  z-index: 2;
  flex: 1;
  padding: 28mm 18mm 16mm;
  display: flex;
  flex-direction: column;
}
.cover-tag {
  font-size: 7pt;
  letter-spacing: 0.20em;
  color: rgba(255,255,255,0.50);
  text-transform: uppercase;
  margin-bottom: 8mm;
  font-weight: bold;
}
.cover-title {
  font-size: 26pt;
  font-weight: bold;
  color: #FFFFFF;
  line-height: 1.15;
  margin-bottom: 4mm;
}
.cover-subtitle {
  font-size: 12pt;
  color: rgba(255,255,255,0.65);
  margin-bottom: 14mm;
}
.cover-meta {
  display: flex;
  flex-direction: column;
  gap: 3mm;
  margin-bottom: 14mm;
}
.cover-meta-row {
  display: flex;
  gap: 6mm;
  align-items: baseline;
}
.cover-meta-label {
  font-size: 6.5pt;
  letter-spacing: 0.12em;
  color: rgba(255,255,255,0.40);
  text-transform: uppercase;
  width: 22mm;
  flex-shrink: 0;
}
.cover-meta-value {
  font-size: 8.5pt;
  color: rgba(255,255,255,0.75);
  font-family: 'Courier New', monospace;
}
.cover-badges {
  display: flex;
  gap: 4mm;
  margin-top: auto;
  flex-wrap: wrap;
}
.cover-badge {
  padding: 2.5mm 5mm;
  border-radius: 2px;
  font-size: 8pt;
  font-weight: bold;
  color: #fff;
  letter-spacing: 0.06em;
  display: flex;
  align-items: center;
  gap: 2mm;
}
.cover-badge .count { font-size: 11pt; }
.badge-crit { background: #C0392B; }
.badge-high { background: #D35400; }
.badge-med  { background: #B7770D; }
.badge-low  { background: #1E7E34; }
.cover-footer {
  position: relative;
  z-index: 2;
  padding: 5mm 18mm;
  border-top: 0.5px solid rgba(255,255,255,0.12);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cover-footer-left  { font-size: 6.5pt; color: rgba(255,255,255,0.30); letter-spacing: 0.10em; }
.cover-footer-right { font-size: 6.5pt; color: rgba(255,255,255,0.30); font-family: 'Courier New', monospace; }

/* ── TOC page ─────────────────────────────────────────────────────────── */
.toc-page {
  padding: 15mm var(--pad) 13mm; /* top: clear 11mm header + 4mm; bottom: clear 9mm footer + 4mm */
  min-height: 297mm;
  break-after: page;
}
.toc-title {
  font-size: 14pt;
  font-weight: bold;
  color: var(--navy);
  border-bottom: 2px solid var(--navy);
  padding-bottom: 3mm;
  margin-bottom: 7mm;
}
.toc-h1 {
  font-size: 9pt;
  font-weight: bold;
  color: var(--navy);
  padding: 2.5mm 0 1mm;
  display: flex;
  justify-content: space-between;
  gap: 4mm;
}
.toc-h2 {
  font-size: 8.5pt;
  color: var(--grey);
  padding: 1mm 0 1mm 6mm;
  display: flex;
  justify-content: space-between;
  gap: 4mm;
}
.toc-dots {
  flex: 1;
  border-bottom: 1px dotted #CCCCCC;
  margin: 0 2mm 1.5mm;
  align-self: flex-end;
}

/* ── Content sections ─────────────────────────────────────────────────── */
/* padding-top = 11mm header + 14mm breathing room; padding-bottom = 9mm footer + 3mm */
.section {
  padding: 25mm var(--pad) 12mm;
}
/* Page break inserted as a sibling before each section (except first) */
.page-break {
  break-before: page;
  height: 0;
  margin: 0;
  padding: 0;
}

/* ── Headings ─────────────────────────────────────────────────────────── */
h2 {
  font-size: 15pt;
  font-weight: bold;
  color: var(--navy);
  border-bottom: 2px solid var(--navy);
  padding-bottom: 2.5mm;
  margin-bottom: 5mm;
}
h3 {
  font-size: 11pt;
  font-weight: bold;
  color: var(--blue);
  margin: 6mm 0 2.5mm;
}
h4 {
  font-size: 9.5pt;
  font-weight: bold;
  color: var(--grey);
  margin: 4mm 0 1.5mm;
}

/* ── Paragraphs & lists ───────────────────────────────────────────────── */
p {
  margin: 0 0 3mm;
  text-align: justify;
  hyphens: auto;
}
ul, ol {
  margin: 2mm 0 3mm 6mm;
  padding-left: 3mm;
}
li {
  margin-bottom: 1.5mm;
  text-align: justify;
  hyphens: auto;
}

/* ── Code blocks ──────────────────────────────────────────────────────── */
pre {
  background: var(--codebg);
  border: 1px solid #DDDDDD;
  border-left: 3px solid var(--blue);
  border-radius: 2px;
  padding: 3mm 4mm;
  margin: 2.5mm 0 4mm;
  font-family: 'Courier New', monospace;
  break-inside: avoid;
  font-size: 7.5pt;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: hidden;
  text-align: left;
}
code {
  font-family: 'Courier New', monospace;
  font-size: 7.5pt;
  background: var(--codebg);
  border: 1px solid #DDDDDD;
  border-radius: 2px;
  padding: 0 1.5mm;
}
pre code { background: none; border: none; padding: 0; font-size: inherit; }

/* ── Callout box (For Engineering Leads) ─────────────────────────────── */
.callout {
  background: var(--callout);
  border: 1px solid var(--calloutbd);
  border-left: 4px solid var(--calloutbd);
  border-radius: 2px;
  padding: 4mm 5mm;
  margin: 3mm 0 4mm;
}
.callout h3 {
  color: var(--navy);
  margin-top: 0;
}
.callout p { margin-bottom: 2mm; }
.callout ul { margin-bottom: 2mm; }

/* ── Tables ───────────────────────────────────────────────────────────── */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 5mm;
  font-size: 8.5pt;
}
th {
  background: var(--navy);
  color: #fff;
  font-weight: bold;
  text-align: left;
  padding: 2mm 3mm;
  font-size: 8pt;
}
td {
  padding: 2mm 3mm;
  border-bottom: 0.5px solid #DDDDDD;
  vertical-align: top;
}
tr:nth-child(even) td { background: #F8F9FA; }

/* ── Severity text ────────────────────────────────────────────────────── */
.sev-CRITICAL { color: #C0392B; font-weight: bold; }
.sev-HIGH     { color: #D35400; font-weight: bold; }
.sev-MEDIUM   { color: #B7770D; font-weight: bold; }
.sev-LOW      { color: #1E7E34; font-weight: bold; }
.sev-INFO     { color: #6B7280; }

/* ── Appendix finding cards ───────────────────────────────────────────── */
.finding-card {
  border: 1px solid var(--border);
  border-radius: 2px;
  margin-bottom: 5mm;
  break-inside: avoid;
  overflow: hidden;
}
.finding-header {
  display: flex;
  align-items: baseline;
  gap: 4mm;
  padding: 2.5mm 4mm;
}
.finding-id {
  font-size: 7pt;
  font-weight: bold;
  color: #888888;
  font-family: 'Courier New', monospace;
  flex-shrink: 0;
}
.finding-title {
  font-size: 9pt;
  font-weight: bold;
  color: var(--navy);
  flex: 1;
}
.finding-sev-badge {
  font-size: 7pt;
  font-weight: bold;
  color: #fff;
  padding: 1mm 3mm;
  border-radius: 2px;
  flex-shrink: 0;
}
.finding-body {
  padding: 3mm 5mm 3.5mm;
  border-top: 0.5px solid var(--border);
  background: #FAFAFA;
  font-size: 8pt;
}
.finding-field-label {
  font-weight: bold;
  color: var(--grey);
  font-size: 7.5pt;
  margin-top: 2mm;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.finding-field-val {
  color: #333333;
  margin-bottom: 1mm;
  text-align: justify;
  hyphens: auto;
}
"""


# ─── Inline formatting ────────────────────────────────────────────────────────

def inline_fmt(text: str) -> str:
    """Escape HTML then apply **bold** and `code` inline formatting."""
    s = html.escape(text)
    # **bold**
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    # `code`
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return s


# ─── Markdown parser ──────────────────────────────────────────────────────────

class Section:
    """One H2 section of the guide."""
    def __init__(self, title: str, anchor: str):
        self.title = title
        self.anchor = anchor
        self.html_parts: list[str] = []
        self.subsections: list[str] = []   # H3 titles for TOC


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def parse_markdown(md: str) -> tuple[str, str, list[Section]]:
    """
    Parse markdown into (doc_title, doc_subtitle, sections).
    - H1  → document title (first one) / subtitle (second H1 treated as subtitle text)
    - H2  → new Section; each H2 becomes a page break in HTML
    - H3  → subsection heading within section
    - H4  → sub-subsection heading
    - ``` → code block
    - Bare lines → paragraphs
    - | → table rows
    - - / * → list items
    - 1. → ordered list items
    Returns:
        doc_title   — first H1 text
        project_line— text immediately following H1 (used as cover subtitle)
        sections    — list of Section objects
    """
    lines = md.splitlines()
    doc_title = "Security Remediation Guide"
    doc_subtitle = ""
    sections: list[Section] = []
    cur: Section | None = None

    in_code = False
    code_lang = ""
    code_buf: list[str] = []

    in_table = False
    table_rows: list[list[str]] = []
    table_header_done = False

    in_callout = False
    callout_buf: list[str] = []

    in_list = False
    list_buf: list[str] = []
    list_ordered = False

    in_olist = False

    got_title = False
    i = 0

    def flush_list():
        nonlocal in_list, list_buf, list_ordered
        if not in_list:
            return
        tag = "ol" if list_ordered else "ul"
        items = "".join(f"<li>{inline_fmt(l)}</li>" for l in list_buf)
        emit(f"<{tag}>{items}</{tag}>")
        in_list = False
        list_buf = []

    def flush_table():
        nonlocal in_table, table_rows, table_header_done
        if not in_table:
            return
        html_parts_local = ["<table>"]
        for row_idx, row in enumerate(table_rows):
            cells = row
            if row_idx == 0:
                html_parts_local.append("<thead><tr>")
                html_parts_local += [f"<th>{inline_fmt(c.strip())}</th>" for c in cells]
                html_parts_local.append("</tr></thead><tbody>")
            elif all(re.match(r'^[-:]+$', c.strip()) for c in cells if c.strip()):
                continue  # separator row
            else:
                html_parts_local.append("<tr>")
                html_parts_local += [f"<td>{inline_fmt(c.strip())}</td>" for c in cells]
                html_parts_local.append("</tr>")
        html_parts_local.append("</tbody></table>")
        emit("".join(html_parts_local))
        in_table = False
        table_rows = []
        table_header_done = False

    def flush_callout():
        nonlocal in_callout, callout_buf
        if not in_callout:
            return
        inner = "\n".join(callout_buf)
        in_callout = False   # must be False before emit() to avoid re-entering callout_buf
        callout_buf = []
        emit(f'<div class="callout">{inner}</div>')

    def emit(fragment: str):
        if in_callout:
            callout_buf.append(fragment)
        elif cur is not None:
            cur.html_parts.append(fragment)

    while i < len(lines):
        line = lines[i]

        # ── Code fence ──
        if line.strip().startswith("```"):
            if not in_code:
                flush_list()
                flush_table()
                in_code = True
                code_lang = line.strip()[3:].strip()
                code_buf = []
            else:
                in_code = False
                escaped = html.escape("\n".join(code_buf))
                emit(f'<pre><code class="lang-{code_lang}">{escaped}</code></pre>')
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # ── Table row ──
        if line.strip().startswith("|"):
            flush_list()
            in_table = True
            cells = [c for c in line.strip().split("|") if c != ""]
            # skip pure separator rows
            if not all(re.match(r'^[-: ]+$', c) for c in cells if c.strip()):
                table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            flush_table()

        # ── H1 ──
        if re.match(r'^# ', line):
            text = line[2:].strip()
            if not got_title:
                doc_title = text
                got_title = True
            i += 1
            continue

        # ── H2 ──
        if re.match(r'^## ', line):
            flush_list()
            flush_table()
            flush_callout()
            title = line[3:].strip()
            anchor = slugify(title)
            cur = Section(title, anchor)
            sections.append(cur)
            # Detect "For Engineering Leads" → wrap in callout
            if 'engineering leads' in title.lower():
                in_callout = True
            i += 1
            continue

        # ── H3 ──
        if re.match(r'^### ', line):
            flush_list()
            flush_table()
            title = line[4:].strip()
            anchor = slugify(title)
            if cur:
                cur.subsections.append(title)
            emit(f'<h3 id="{anchor}">{inline_fmt(title)}</h3>')
            i += 1
            continue

        # ── H4 ──
        if re.match(r'^#### ', line):
            flush_list()
            flush_table()
            title = line[5:].strip()
            emit(f'<h4>{inline_fmt(title)}</h4>')
            i += 1
            continue

        # ── Blank line ──
        if not line.strip():
            flush_list()
            flush_table()
            # blank line after a callout-level H2 signals end of callout opening header
            i += 1
            continue

        # ── Unordered list ──
        m = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if m:
            flush_table()
            if not in_list:
                in_list = True
                list_ordered = False
                list_buf = []
            list_buf.append(m.group(2))
            i += 1
            continue
        elif in_list and list_ordered is False:
            flush_list()

        # ── Ordered list ──
        m = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if m:
            flush_table()
            if not in_list:
                in_list = True
                list_ordered = True
                list_buf = []
            list_buf.append(m.group(2))
            i += 1
            continue
        elif in_list:
            flush_list()

        # ── Horizontal rule ──
        if re.match(r'^---+$', line.strip()):
            flush_callout()
            emit('<hr style="border:none;border-top:1px solid #DDDDDD;margin:4mm 0;">')
            i += 1
            continue

        # ── Plain paragraph ──
        if line.strip() and cur is not None:
            emit(f'<p>{inline_fmt(line.strip())}</p>')

        i += 1

    flush_list()
    flush_table()
    flush_callout()

    return doc_title, doc_subtitle, sections


# ─── Cover page HTML ─────────────────────────────────────────────────────────

def build_cover(title: str, meta: dict, counts: dict) -> str:
    project  = meta.get("project_name", "")
    branch   = meta.get("branch", "master")
    date     = meta.get("report_date", "")
    auditor  = meta.get("auditor", "Security Team")
    total    = sum(counts.values())

    badges = ""
    badge_cls = {"CRITICAL":"badge-crit","HIGH":"badge-high","MEDIUM":"badge-med","LOW":"badge-low"}
    for sev in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        n = counts.get(sev, 0)
        if n:
            badges += (
                f'<div class="cover-badge {badge_cls[sev]}">'
                f'<span class="count">{n}</span> {sev}'
                f'</div>'
            )

    return f"""
<div class="cover">
  <div class="cover-grid"></div>
  <div class="cover-accent-bar"></div>
  <div class="cover-body">
    <div class="cover-tag">Developer Remediation Guide</div>
    <div class="cover-title">{html.escape(title)}</div>
    <div class="cover-subtitle">Root-cause analysis, code fixes &amp; sprint roadmap</div>
    <div class="cover-meta">
      <div class="cover-meta-row">
        <span class="cover-meta-label">Project</span>
        <span class="cover-meta-value">{html.escape(project)}</span>
      </div>
      <div class="cover-meta-row">
        <span class="cover-meta-label">Branch</span>
        <span class="cover-meta-value">{html.escape(branch)}</span>
      </div>
      <div class="cover-meta-row">
        <span class="cover-meta-label">Date</span>
        <span class="cover-meta-value">{html.escape(date)}</span>
      </div>
      <div class="cover-meta-row">
        <span class="cover-meta-label">Total findings</span>
        <span class="cover-meta-value">{total}</span>
      </div>
    </div>
    <div class="cover-badges">{badges}</div>
  </div>
  <div class="cover-footer">
    <span class="cover-footer-left">CONFIDENTIAL — FOR INTERNAL USE ONLY</span>
    <span class="cover-footer-right">{html.escape(auditor)}</span>
  </div>
</div>
"""


# ─── TOC HTML ────────────────────────────────────────────────────────────────

def build_toc(sections: list[Section]) -> str:
    rows = ""
    for sec in sections:
        rows += (
            f'<div class="toc-h1">'
            f'<a href="#{sec.anchor}" style="color:var(--navy);text-decoration:none;">'
            f'{html.escape(sec.title)}'
            f'</a>'
            f'<span class="toc-dots"></span>'
            f'</div>'
        )
        for sub in sec.subsections:
            sub_anchor = slugify(sub)
            rows += (
                f'<div class="toc-h2">'
                f'<a href="#{sub_anchor}" style="color:var(--grey);text-decoration:none;">'
                f'{html.escape(sub)}'
                f'</a>'
                f'<span class="toc-dots"></span>'
                f'</div>'
            )
    return f"""
<div class="toc-page">
  <div class="toc-title">Table of Contents</div>
  {rows}
</div>
"""


# ─── Appendix HTML ───────────────────────────────────────────────────────────

def build_appendix(findings: list[dict]) -> str:
    if not findings:
        return ""

    def sev_order(f):
        s = f.get("severity","INFO").upper()
        return SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else 99

    sorted_findings = sorted(findings, key=sev_order)
    cards = ""
    for f in sorted_findings:
        fid   = html.escape(f.get("id",""))
        title = html.escape(f.get("title",""))
        sev   = f.get("severity","INFO").upper()
        loc   = html.escape(f.get("location",""))
        desc  = html.escape(f.get("description",""))
        impact= html.escape(f.get("impact",""))
        rem   = html.escape(f.get("remediation","") or f.get("fix",""))
        cvss  = html.escape(str(f.get("cvss_score","")))
        cwe   = html.escape(f.get("cwe",""))

        bg    = SEV_BG.get(sev, "#F4F5F6")
        color = SEV_COLOR.get(sev, "#6B7280")

        details = ""
        if loc:
            details += f'<div class="finding-field-label">Location</div><div class="finding-field-val">{loc}</div>'
        if desc:
            details += f'<div class="finding-field-label">Description</div><div class="finding-field-val">{desc}</div>'
        if impact:
            details += f'<div class="finding-field-label">Impact</div><div class="finding-field-val">{impact}</div>'
        if rem:
            details += f'<div class="finding-field-label">Remediation</div><div class="finding-field-val">{rem}</div>'
        if cvss:
            details += f'<div class="finding-field-label">CVSS</div><div class="finding-field-val">{cvss}</div>'
        if cwe:
            details += f'<div class="finding-field-label">CWE</div><div class="finding-field-val">{cwe}</div>'

        cards += f"""
<div class="finding-card">
  <div class="finding-header" style="background:{bg};">
    <span class="finding-id">{fid}</span>
    <span class="finding-title">{title}</span>
    <span class="finding-sev-badge" style="background:{color};">{sev}</span>
  </div>
  <div class="finding-body">{details}</div>
</div>
"""
    return f"""<div class="page-break"></div>
<div class="section" id="appendix-findings">
  <h2>Appendix — Full Findings Inventory</h2>
  {cards}
</div>
"""


# ─── Full HTML assembly ───────────────────────────────────────────────────────

def build_html(
    doc_title: str,
    sections: list[Section],
    meta: dict,
    findings: list[dict],
) -> str:
    counts: dict[str, int] = {}
    for f in findings:
        s = f.get("severity","INFO").upper()
        counts[s] = counts.get(s, 0) + 1

    project = meta.get("project_name", "")
    date    = meta.get("report_date", "")

    cover   = build_cover(doc_title, meta, counts)
    toc     = build_toc(sections)

    section_html = ""
    for idx, sec in enumerate(sections):
        inner = "\n".join(sec.html_parts)
        brk = '<div class="page-break"></div>\n' if idx > 0 else ""
        section_html += f"""{brk}<div class="section" id="{sec.anchor}">
  <h2>{html.escape(sec.title)}</h2>
  {inner}
</div>
"""

    appendix = build_appendix(findings)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(doc_title)}</title>
<style>
{CSS}
</style>
</head>
<body>

<!-- Fixed header (hidden on cover by z-index) -->
<div class="fixed-header">
  <div class="fh-accent"></div>
  <div class="fh-content">
    <span class="fh-left">Developer Remediation Guide — {html.escape(project)}</span>
    <span class="fh-right">CONFIDENTIAL</span>
  </div>
</div>

<!-- Fixed footer -->
<div class="fixed-footer">
  <span class="ff-left">INTERNAL USE ONLY · {html.escape(date)}</span>
  <span class="ff-right">Generated by vuln-assess skill</span>
</div>

{cover}
{toc}
{section_html}
{appendix}

</body>
</html>
"""


# ─── Chrome PDF render ───────────────────────────────────────────────────────

def render_pdf(html_path: str, output_path: str, chrome: str) -> None:
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--run-all-compositor-stages-before-draw",
        "--print-to-pdf-no-margins",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_path}",
        f"file://{html_path}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[chrome stderr]\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"Chrome exited with code {result.returncode}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate Developer Remediation Guide PDF from Markdown + findings JSON"
    )
    ap.add_argument("--guide",    required=True, help="Path to Developer_Remediation_Guide.md")
    ap.add_argument("--findings", required=True, help="Path to _vuln_findings.json")
    ap.add_argument("--output",   required=True, help="Output PDF path")
    args = ap.parse_args()

    chrome = find_chrome()
    if not chrome:
        print("ERROR: Chrome/Chromium not found. Install google-chrome or chromium.", file=sys.stderr)
        sys.exit(1)

    # Load markdown
    guide_path = Path(args.guide)
    if not guide_path.exists():
        print(f"ERROR: Guide file not found: {guide_path}", file=sys.stderr)
        sys.exit(1)
    md_text = guide_path.read_text(encoding="utf-8")

    # Load findings
    findings_path = Path(args.findings)
    if not findings_path.exists():
        print(f"ERROR: Findings JSON not found: {findings_path}", file=sys.stderr)
        sys.exit(1)
    findings_data = json.loads(findings_path.read_text(encoding="utf-8"))
    findings: list[dict] = findings_data.get("findings", [])
    meta: dict = findings_data.get("project", {})
    if not meta:
        meta = {k: v for k, v in findings_data.items() if k != "findings"}

    # Parse markdown
    doc_title, _, sections = parse_markdown(md_text)

    # Build HTML
    html_content = build_html(doc_title, sections, meta, findings)

    # Write to temp file and render
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as fh:
        fh.write(html_content)
        tmp_html = fh.name

    output_path = str(Path(args.output).resolve())
    try:
        print(f"Rendering PDF via Chrome headless...")
        render_pdf(os.path.abspath(tmp_html), output_path, chrome)
        print(f"✓ PDF saved: {output_path}")
    finally:
        os.unlink(tmp_html)


if __name__ == "__main__":
    main()
