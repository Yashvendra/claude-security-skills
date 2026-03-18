#!/usr/bin/env python3
"""
generate_report_html.py
=======================
Vulnerability Assessment Report Generator — HTML → Chrome-headless → PDF

Reads _vuln_findings.json and produces a professional A4 PDF report using
the finalized design: Space Grotesk / Space Mono / Syne fonts, severity-coded
finding cards, fixed header/footer, cover page grid layout, and sprint roadmap.

Usage:
    python generate_report_html.py --findings _vuln_findings.json \
                                   --output MyProject_Vulnerability_Report.pdf \
                                   [--watermark DRAFT]

Requirements:
    - Python 3.8+
    - Google Chrome or Chromium installed
"""

import argparse
import html
import json
import os
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

SEV_CLASS = {
    "CRITICAL": "crit", "HIGH": "high",
    "MEDIUM": "med",   "LOW": "low", "INFO": "info",
}

SEV_COLOR = {
    "CRITICAL": "#E8002D", "HIGH": "#E85D04",
    "MEDIUM":   "#D4A017", "LOW":  "#12875A", "INFO": "#6B7280",
}

SEV_TAGLINE = {
    "CRITICAL": "Immediate action required",
    "HIGH":     "Remediate within Sprint 1",
    "MEDIUM":   "Remediate within Sprint 2",
    "LOW":      "Remediate within Sprint 3",
    "INFO":     "Informational",
}

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


# ─── CSS (the finalized design) ───────────────────────────────────────────────

CSS = """\
/* ─── Reset ──────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ─── @page: zero physical margins on all pages.
       Fixed header (12mm) and footer (10mm) sit at position: fixed top/bottom 0,
       which in Chrome print mode = physical page edge when margin is 0.
       Body sections compensate with padding-top: 30mm.                   ── */
@page          { size: A4; margin: 0; }
@page :first   { margin: 0; }

html, body {
  width: 210mm;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  background: #fff;
  color: #0D1117;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  overflow-x: hidden;
  scrollbar-width: none;
}
::-webkit-scrollbar { display: none; }

/* ─── Variables ──────────────────────────────────────────────────────── */
:root {
  --pad:    14mm;
  --ink:    #0D1117;
  --ink2:   #4A5568;
  --ink3:   #9AAFBF;
  --paper:  #FFFFFF;
  --paper2: #F7F8FA;
  --paper3: #EDF0F5;
  --accent: #0066FF;
  --crit:   #E8002D;  --crit-bg: #FFF0F3;
  --high:   #E85D04;  --high-bg: #FFF5EE;
  --med:    #D4A017;  --med-bg:  #FFFBE6;
  --low:    #12875A;  --low-bg:  #F0FAF5;
  --mono:   'Space Mono', 'Courier New', monospace;
  --display:'Syne', sans-serif;
}

/* ════════════════════════════════════════════════════════════════════════
   FIXED HEADER — prints at the top of every page after the cover.
════════════════════════════════════════════════════════════════════════ */
.fixed-header {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 12mm;
  background: var(--ink);
  display: flex;
  align-items: stretch;
  z-index: 10;
}
.fh-accent { width: 5mm; background: var(--accent); flex-shrink: 0; }
.fh-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6mm;
}
.fh-title {
  font-family: var(--mono);
  font-size: 6pt;
  letter-spacing: 0.18em;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
}
.fh-right {
  font-family: var(--mono);
  font-size: 6pt;
  color: rgba(255,255,255,0.3);
  letter-spacing: 0.12em;
}

/* ════════════════════════════════════════════════════════════════════════
   FIXED FOOTER — prints at the bottom of every page.
════════════════════════════════════════════════════════════════════════ */
.fixed-footer {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 10mm;
  border-top: 1px solid var(--paper3);
  background: var(--paper);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6mm;
  z-index: 10;
}
.ff-left  { font-family: var(--mono); font-size: 5.5pt; font-weight: 700; color: var(--ink2); letter-spacing: 0.1em; }
.ff-right { font-family: var(--mono); font-size: 5.5pt; font-weight: 700; color: var(--ink2); }
.ff-pg    { font-weight: 700; color: var(--ink2); }

/* ════════════════════════════════════════════════════════════════════════
   COVER PAGE — height: 297mm + z-index: 999 masks fixed header/footer
   on page 1.
════════════════════════════════════════════════════════════════════════ */
.cover {
  display: grid;
  grid-template-columns: 42% 58%;
  width: 210mm;
  height: 297mm;
  min-height: 100vh;
  position: relative;
  z-index: 999;
  break-after: page;
}

/* Left panel */
.cover-left {
  background: #060B12;
  padding: 14mm 10mm 5mm 14mm;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}
.cover-left::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    radial-gradient(circle at 20% 80%, rgba(0,102,255,0.12) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(0,102,255,0.06) 0%, transparent 40%);
  pointer-events: none;
}
.cover-left::after {
  content: '';
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 8mm 8mm;
  pointer-events: none;
}
.cover-eyebrow {
  font-family: var(--mono);
  font-size: 6.5pt;
  letter-spacing: 0.18em;
  color: var(--accent);
  text-transform: uppercase;
  position: relative; z-index: 1;
  margin-bottom: 6mm;
}
.cover-eyebrow::before { content: '> '; opacity: 0.5; }
.cover-title-block {
  position: relative; z-index: 1;
  flex: 1;
  display: flex; flex-direction: column; justify-content: center;
}
.cover-label {
  font-family: var(--mono);
  font-size: 6.5pt;
  letter-spacing: 0.25em;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  margin-bottom: 3mm;
}
.cover-h1 {
  font-family: var(--display);
  font-size: 38pt; font-weight: 800;
  line-height: 0.95; color: #FFFFFF;
  letter-spacing: -0.02em;
  margin-bottom: 5mm;
}
.cover-h1 span { display: block; color: var(--accent); }
.cover-divider { width: 12mm; height: 1.5px; background: var(--accent); margin: 5mm 0; }
.cover-project { font-size: 9pt; color: rgba(255,255,255,0.55); font-weight: 400; line-height: 1.5; }
.cover-project strong { color: rgba(255,255,255,0.9); display: block; font-size: 11pt; font-weight: 600; margin-bottom: 1mm; }
.cover-meta-grid {
  position: relative; z-index: 1;
  display: grid; grid-template-columns: 1fr 1fr; gap: 3mm;
  margin-top: 8mm; padding-top: 6mm;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.cover-meta-item label {
  font-family: var(--mono); font-size: 5pt; letter-spacing: 0.18em;
  color: rgba(255,255,255,0.3); text-transform: uppercase; display: block; margin-bottom: 0.8mm;
}
.cover-meta-item span { font-size: 7pt; color: rgba(255,255,255,0.7); font-weight: 500; }
.cover-confidential {
  position: relative; z-index: 1;
  margin-top: 6mm;
  display: inline-flex; align-items: center; gap: 2mm;
  font-family: var(--mono); font-size: 6.5pt; letter-spacing: 0.2em;
  color: var(--crit); text-transform: uppercase;
}
.cover-confidential::before {
  content: ''; display: inline-block;
  width: 4px; height: 4px; background: var(--crit); border-radius: 50%;
}

/* Right panel */
.cover-right {
  background: var(--paper);
  padding: 14mm 14mm 5mm 12mm;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.cover-right-eyebrow {
  font-family: var(--mono); font-size: 8pt; letter-spacing: 0.18em;
  color: var(--ink2); text-transform: uppercase; font-weight: 700; margin-bottom: 6mm;
}
.risk-headline {
  font-family: var(--display); font-size: 9pt; font-weight: 700; color: var(--ink);
  text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 3mm;
}
.severity-blocks { display: flex; flex-direction: column; gap: 2.5mm; margin-bottom: 8mm; }
.sev-block {
  display: grid; grid-template-columns: 18mm 1fr auto; align-items: center;
  gap: 3mm; padding: 3.5mm 4mm; border-radius: 3px;
}
.sev-block-label { font-family: var(--mono); font-size: 6pt; font-weight: 700; letter-spacing: 0.15em; }
.sev-block-bar-wrap { height: 4px; background: rgba(0,0,0,0.06); border-radius: 2px; overflow: hidden; }
.sev-block-bar { height: 100%; border-radius: 2px; }
.sev-block-count { font-family: var(--display); font-size: 16pt; font-weight: 800; line-height: 1; min-width: 10mm; text-align: right; }
.sev-block.crit { background: var(--crit-bg); }
.sev-block.crit .sev-block-label { color: var(--crit); }
.sev-block.crit .sev-block-bar   { background: var(--crit); }
.sev-block.crit .sev-block-count { color: var(--crit); }
.sev-block.high { background: var(--high-bg); }
.sev-block.high .sev-block-label { color: var(--high); }
.sev-block.high .sev-block-bar   { background: var(--high); }
.sev-block.high .sev-block-count { color: var(--high); }
.sev-block.med  { background: var(--med-bg); }
.sev-block.med  .sev-block-label { color: var(--med); }
.sev-block.med  .sev-block-bar   { background: var(--med); }
.sev-block.med  .sev-block-count { color: var(--med); }
.sev-block.low  { background: var(--low-bg); }
.sev-block.low  .sev-block-label { color: var(--low); }
.sev-block.low  .sev-block-bar   { background: var(--low); }
.sev-block.low  .sev-block-count { color: var(--low); }

/* cr-mid mirrors cover-title-block on the left: centers severity blocks vertically */
.cr-mid { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; }
.matrix-section { display: flex; flex-direction: column; }
.matrix-label {
  font-family: var(--mono); font-size: 5.5pt; letter-spacing: 0.18em;
  color: var(--ink3); text-transform: uppercase; margin-bottom: 3mm;
}
.risk-matrix {
  display: grid; grid-template-columns: repeat(5, 1fr); grid-template-rows: repeat(5, 1fr);
  gap: 2mm; aspect-ratio: 1; max-width: 80mm;
}
.matrix-cell { border-radius: 2px; aspect-ratio: 1; }
.mc-crit { background: var(--crit); opacity: 0.9; }
.mc-high { background: var(--high); opacity: 0.85; }
.mc-med  { background: var(--med);  opacity: 0.8; }
.mc-low  { background: var(--low);  opacity: 0.7; }
.mc-nil  { background: var(--paper3); }
.matrix-axes { display: flex; justify-content: space-between; margin-top: 2mm; max-width: 80mm; }
.matrix-axes span { font-family: var(--mono); font-size: 4.5pt; color: var(--ink3); text-transform: uppercase; letter-spacing: 0.1em; }

.total-badge { margin-top: 5mm; display: flex; align-items: center; gap: 4mm; }
.total-number {
  font-family: var(--display); font-size: 52pt; font-weight: 800;
  line-height: 1; color: var(--ink); letter-spacing: -0.03em; flex-shrink: 0;
}
.total-sub { font-size: 9.5pt; color: var(--ink2); font-weight: 400; line-height: 1.5; }

/* ════════════════════════════════════════════════════════════════════════
   BODY CONTENT — natural flow, no fixed heights.
   Chrome breaks pages where content naturally falls.
   30mm top padding = 12mm fixed header + 18mm breathing room above content.
════════════════════════════════════════════════════════════════════════ */
.body-section { padding: 30mm var(--pad) 14mm; }

.break-before { break-before: page; }
.section-heading  { break-after: avoid; }
.section-rule     { break-after: avoid; }
.group-header     { break-after: avoid; }
/* Non-first severity groups (MEDIUM/LOW/INFO): padding-top provides clearance
   from the fixed 12mm header when the group-header lands at a page top, and
   acts as inter-group visual spacing when mid-page. HIGH group is excluded via
   the group-first class to avoid extra gap after the section rule. */
.group-non-first .group-header { padding-top: 18mm; }

/* .finding-wrap: transparent container around each card. Uses padding-top
   (NOT margin-top) because Chrome collapses margins at page tops, but
   padding is never collapsed — 18mm always clears the 12mm fixed header. */
.finding-wrap { break-inside: avoid; padding-top: 18mm; }
.group-header + .finding-wrap { padding-top: 5mm; }

/* ─── Section heading ─────────────────────────────────────────────────── */
.section-heading { display: flex; align-items: baseline; gap: 4mm; margin-bottom: 6mm; }
.section-number  { font-family: var(--mono); font-size: 7pt; color: var(--accent); font-weight: 700; letter-spacing: 0.1em; }
.section-title   { font-family: var(--display); font-size: 20pt; font-weight: 800; color: var(--ink); line-height: 1; letter-spacing: -0.02em; }
.section-rule    { height: 1px; background: linear-gradient(90deg, var(--accent) 0%, var(--paper3) 60%); margin-bottom: 8mm; }

/* ─── Executive summary ───────────────────────────────────────────────── */
.exec-intro { font-size: 10pt; line-height: 1.65; color: var(--ink2); margin-bottom: 8mm; text-align: justify; }
.exec-intro strong { color: var(--ink); font-weight: 600; }
.stat-row   { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4mm; margin-bottom: 8mm; }
.stat-card  { padding: 5mm 4mm; border-radius: 4px; border-top: 3px solid transparent; }
.stat-card.crit { background: var(--crit-bg); border-top-color: var(--crit); }
.stat-card.high { background: var(--high-bg); border-top-color: var(--high); }
.stat-card.med  { background: var(--med-bg);  border-top-color: var(--med); }
.stat-card.low  { background: var(--low-bg);  border-top-color: var(--low); }
.stat-num { font-family: var(--display); font-size: 26pt; font-weight: 800; line-height: 1; margin-bottom: 1mm; }
.stat-card.crit .stat-num { color: var(--crit); }
.stat-card.high .stat-num { color: var(--high); }
.stat-card.med  .stat-num { color: var(--med); }
.stat-card.low  .stat-num { color: var(--low); }
.stat-label { font-family: var(--mono); font-size: 8pt; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink); font-weight: 600; }
.dist-label { font-family: var(--mono); font-size: 8pt; letter-spacing: 0.15em; color: var(--ink); text-transform: uppercase; margin-bottom: 2.5mm; font-weight: 600; }
.dist-bar   { display: flex; height: 8mm; border-radius: 3px; overflow: hidden; margin-bottom: 2mm; }
.dist-seg   { display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 7pt; font-weight: 700; color: rgba(255,255,255,0.95); min-width: 18mm; }
.dist-seg.crit { background: var(--crit); }
.dist-seg.high { background: var(--high); }
.dist-seg.med  { background: var(--med); color: rgba(0,0,0,0.7); }
.dist-seg.low  { background: var(--low); }

/* ─── Scope table ─────────────────────────────────────────────────────── */
.scope-table { width: 100%; border-collapse: collapse; font-size: 8pt; margin-bottom: 6mm; }
.scope-table th {
  font-family: var(--mono); font-size: 5.5pt; letter-spacing: 0.15em; text-transform: uppercase;
  color: var(--ink2); text-align: left; padding: 2.5mm 3mm;
  background: var(--paper3); border-bottom: 1px solid rgba(0,0,0,0.08);
}
.scope-table td { padding: 2.5mm 3mm; border-bottom: 1px solid var(--paper3); color: var(--ink2); vertical-align: top; line-height: 1.5; }
.scope-table td:first-child { font-weight: 600; color: var(--ink); }
.scope-table tr:last-child td { border-bottom: none; }
.scope-table tr:nth-child(even) td { background: var(--paper2); }

/* Findings index table */
.index-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 2mm; }
.index-table th {
  font-family: var(--mono); font-size: 5.5pt; letter-spacing: 0.15em; text-transform: uppercase;
  color: var(--ink2); text-align: left; padding: 2.5mm 3mm;
  background: var(--paper3); border-bottom: 1px solid rgba(0,0,0,0.08);
}
.index-table td { padding: 2.5mm 3mm; border-bottom: 1px solid var(--paper3); color: var(--ink2); vertical-align: middle; line-height: 1.4; }
.index-table tr:last-child td { border-bottom: none; }
.index-table tr:nth-child(even) td { background: var(--paper2); }
.index-table .loc-cell { font-family: var(--mono); font-size: 7pt; color: var(--ink3); }

/* ════════════════════════════════════════════════════════════════════════
   FINDING CARDS
════════════════════════════════════════════════════════════════════════ */
.findings-group { margin-bottom: 6mm; }
.group-header {
  display: flex; align-items: center; gap: 3mm;
  margin-bottom: 4mm; padding-bottom: 2mm;
  border-bottom: 1.5px solid var(--paper3);
}
.group-badge {
  font-family: var(--mono); font-size: 6pt; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  padding: 1.5mm 3mm; border-radius: 2px;
}
.group-badge.crit { background: var(--crit); color: #fff; }
.group-badge.high { background: var(--high); color: #fff; }
.group-badge.med  { background: var(--med);  color: #fff; }
.group-badge.low  { background: var(--low);  color: #fff; }
.group-badge.info { background: var(--ink3); color: #fff; }
.group-count { font-family: var(--mono); font-size: 8pt; color: var(--ink2); font-weight: 500; }

.finding {
  border: 1px solid var(--paper3);
  border-radius: 4px;
  margin-bottom: 5mm;
  padding-top: 18mm;
  padding-bottom: 14mm;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
}
/* Cancel the padding on the first page so the header sits flush at the card top.
   On continuation fragments the header is absent, so the 18mm clears the fixed header. */
.finding-header { display: grid; grid-template-columns: 1fr auto; align-items: stretch; margin-top: -18mm; }

.finding-hdr-main {
  padding: 4mm 4mm 4mm 5mm; background: var(--paper2);
  display: flex; flex-direction: column; justify-content: center;
}
.finding-id { font-family: var(--mono); font-size: 7pt; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 2mm; }
.finding.crit .finding-id { color: var(--crit); }
.finding.high .finding-id { color: var(--high); }
.finding.med  .finding-id { color: var(--med); }
.finding.low  .finding-id { color: var(--low); }
.finding.info .finding-id { color: var(--ink3); }
.finding-title { font-family: var(--display); font-size: 11pt; font-weight: 700; color: var(--ink); line-height: 1.2; letter-spacing: -0.01em; }

.finding-hdr-right {
  padding: 4mm 5mm; background: var(--paper2);
  display: flex; flex-direction: column; align-items: flex-end; justify-content: center;
  border-left: 1px solid var(--paper3); min-width: 30mm;
}
.cvss-score { font-family: var(--display); font-size: 18pt; font-weight: 800; line-height: 1; margin-bottom: 1mm; }
.finding.crit .cvss-score { color: var(--crit); }
.finding.high .cvss-score { color: var(--high); }
.finding.med  .cvss-score { color: var(--med); }
.finding.low  .cvss-score { color: var(--low); }
.finding.info .cvss-score { color: var(--ink3); }
.cvss-label { font-family: var(--mono); font-size: 5pt; letter-spacing: 0.18em; color: var(--ink); text-transform: uppercase; }

.finding-location {
  padding: 3mm 5mm 3mm 5mm; background: var(--ink);
  display: flex; align-items: center; gap: 3mm;
  break-after: avoid; page-break-after: avoid;
}
.finding-location-icon { font-family: var(--mono); font-size: 7pt; font-weight: 700; color: var(--accent); letter-spacing: 0.15em; white-space: nowrap; }
.finding-location-path { font-family: var(--mono); font-size: 8pt; color: rgba(255,255,255,0.88); letter-spacing: 0.03em; }
.finding-body { padding: 5mm 5mm 5mm 5mm; }
.finding-field { margin-bottom: 5mm; break-inside: avoid; page-break-inside: avoid; }
.finding-field:last-child { margin-bottom: 0; }
.field-label { font-family: var(--mono); font-size: 6.5pt; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink2); margin-bottom: 2mm; }
.field-text  { font-size: 10pt; line-height: 1.75; color: var(--ink2); text-align: justify; }
.field-text strong { color: var(--ink); font-weight: 600; }
.impact-text { font-size: 10pt; line-height: 1.75; font-weight: 500; text-align: justify; }
/* Inline code references inside description / impact / remediation */
.field-text code, .impact-text code, .remed-list li code {
  font-family: var(--mono); font-size: 8pt;
  background: rgba(0,168,255,0.10); color: #3bb3ff;
  border: 0.3px solid rgba(0,168,255,0.25);
  border-radius: 3px; padding: 0.5px 3px;
}

/* Impact callout block — tinted background + dark readable text per severity */
.impact-block {
  border-radius: 0 4px 4px 0;
  padding: 3.5mm 4.5mm;
  margin-top: 0.5mm;
}
.finding.crit .impact-block { background: var(--crit-bg); }
.finding.high .impact-block { background: var(--high-bg); }
.finding.med  .impact-block { background: var(--med-bg);  }
.finding.low  .impact-block { background: var(--low-bg);  }
.finding.info .impact-block { background: var(--paper2);  }
/* Darker, readable severity text colors — vivid colors on white are hard to read */
.finding.crit .impact-text { color: #9B001E; }
.finding.high .impact-text { color: #9B3A00; }
.finding.med  .impact-text { color: #6B5100; }
.finding.low  .impact-text { color: #0A5C38; }
.finding.info .impact-text { color: var(--ink2); }

.code-block {
  background: #0D1117; border-radius: 4px; padding: 4mm 5mm;
  font-family: var(--mono); font-size: 9pt; line-height: 1.8;
  color: #7DCFFF; overflow: hidden; margin-top: 1.5mm;
  white-space: pre-wrap; word-break: break-all;
  break-inside: avoid; page-break-inside: avoid;
}

.remed-list { list-style: none; margin-top: 1.5mm; }
.remed-list li {
  font-size: 10pt; line-height: 1.75; color: var(--ink2);
  padding-left: 5mm; position: relative; margin-bottom: 2.5mm;
  text-align: left; break-inside: avoid; page-break-inside: avoid;
}
.remed-list li::before { content: '→'; position: absolute; left: 0; color: var(--accent); font-family: var(--mono); font-size: 7pt; }

/* ════════════════════════════════════════════════════════════════════════
   ROADMAP
════════════════════════════════════════════════════════════════════════ */
.roadmap-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-bottom: 8mm; }
.sprint-lane { border: 1px solid var(--paper3); border-radius: 4px; overflow: hidden; }
.sprint-header {
  padding: 3mm 5mm; background: var(--ink);
  display: flex; align-items: center; justify-content: space-between;
}
.sprint-name { font-family: var(--display); font-size: 9pt; font-weight: 700; color: #fff; letter-spacing: -0.01em; }
.sprint-tag  { font-family: var(--mono); font-size: 5pt; letter-spacing: 0.15em; color: var(--accent); text-transform: uppercase; }
.sprint-items { padding: 3mm; display: flex; flex-direction: column; gap: 2mm; background: var(--paper); }
.sprint-item {
  display: grid; grid-template-columns: auto 1fr auto; align-items: center;
  gap: 2.5mm; padding: 2.5mm 3mm; border-radius: 3px;
  background: var(--paper2); border-left: 3px solid transparent;
}
.sprint-item.crit { border-left-color: var(--crit); }
.sprint-item.high { border-left-color: var(--high); }
.sprint-item.med  { border-left-color: var(--med); }
.sprint-item.low  { border-left-color: var(--low); }
.sprint-item-id    { font-family: var(--mono); font-size: 5.5pt; color: var(--ink3); }
.sprint-item-title { font-size: 7pt; font-weight: 500; color: var(--ink); line-height: 1.3; }
.sprint-effort     { font-family: var(--mono); font-size: 5pt; color: var(--ink3); white-space: nowrap; }

.remed-table { width: 100%; border-collapse: collapse; font-size: 8pt; margin-top: -15mm; }
.remed-table tfoot { display: table-footer-group; }
.remed-table th {
  background: var(--paper3); font-family: var(--mono); font-size: 5pt; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--ink2); padding: 2.5mm 3mm; text-align: left;
  border-bottom: 1px solid rgba(0,0,0,0.08);
}
.remed-table td { padding: 2.5mm 3mm; border-bottom: 1px solid var(--paper3); vertical-align: middle; color: var(--ink2); }
.remed-table tr:last-child td { border-bottom: none; }
.remed-table tr:nth-child(even) td { background: var(--paper2); }
.remed-table .id-cell { font-family: var(--mono); font-size: 6pt; color: var(--ink); font-weight: 700; }
.sev-pill {
  display: inline-block; padding: 0.8mm 2.5mm; border-radius: 20px;
  font-family: var(--mono); font-size: 5.5pt; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
}
.sev-pill.crit { background: var(--crit-bg); color: var(--crit); }
.sev-pill.high { background: var(--high-bg); color: var(--high); }
.sev-pill.med  { background: var(--med-bg);  color: var(--med); }
.sev-pill.low  { background: var(--low-bg);  color: var(--low); }
.sev-pill.info { background: var(--paper3);  color: var(--ink3); }

/* ─── Sub-section headings (used inside Scope & Architecture) ────────── */
.subsec-heading {
  display: flex;
  align-items: baseline;
  gap: 3mm;
  margin-top: 8mm;
  margin-bottom: 2mm;
  break-after: avoid;
}
.subsec-number {
  font-family: var(--mono);
  font-size: 6pt;
  color: var(--accent);
  font-weight: 700;
  letter-spacing: 0.1em;
}
.subsec-title {
  font-family: var(--display);
  font-size: 12pt;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.subsec-rule {
  height: 1px;
  background: var(--paper3);
  margin-bottom: 4mm;
  break-after: avoid;
}

/* ─── Table header repetition across page breaks ─────────────────────── */
/* Chrome print: explicitly declare table-header-group so <thead> repeats */
.scope-table thead,
.index-table thead,
.fi-table thead,
.remed-table thead,
.comp-table thead,
.cov-table thead {
  display: table-header-group;
}

/* ─── Watermark ───────────────────────────────────────────────────────── */
.watermark {
  position: fixed;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%) rotate(-35deg);
  font-family: var(--display);
  font-size: 72pt;
  font-weight: 800;
  color: rgba(0,0,0,0.04);
  pointer-events: none;
  z-index: 5;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}

@media print {
  .cover       { break-after: page; }
  .break-before { break-before: page; }
  .finding     { break-inside: avoid; page-break-inside: avoid; }
}

/* ════════════════════════════════════════════════════════════════════════
   RISK DASHBOARD
════════════════════════════════════════════════════════════════════════ */
.dash-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4mm; margin-bottom: 8mm; }
.dash-card { background: var(--paper2); border: 1px solid var(--paper3); border-radius: 4px; padding: 4mm 4mm 3mm; break-inside: avoid; }
.dash-card-label { font-family: var(--mono); font-size: 5.5pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 2mm; }
.dash-card-value { font-family: var(--display); font-size: 26pt; font-weight: 800; line-height: 1; }
.dash-card.crit .dash-card-value { color: var(--crit); }
.dash-card.high .dash-card-value { color: var(--high); }
.dash-card.med  .dash-card-value { color: var(--med); }
.dash-card.low  .dash-card-value { color: var(--low); }
.dash-card.info .dash-card-value { color: var(--ink3); }
.dash-card-sub  { font-size: 7pt; color: var(--ink2); margin-top: 1.5mm; }

/* OWASP category breakdown bars */
.cat-rows   { margin-bottom: 8mm; }
.cat-row    { display: flex; align-items: center; gap: 3mm; margin-bottom: 2.5mm; break-inside: avoid; }
.cat-label  { font-size: 9pt; color: var(--ink); width: 65mm; flex-shrink: 0; line-height: 1.3; }
.cat-track  { flex: 1; height: 5px; background: var(--paper3); border-radius: 3px; overflow: hidden; }
.cat-fill   { height: 100%; border-radius: 3px; }
.cat-fill.crit { background: var(--crit); }
.cat-fill.high { background: var(--high); }
.cat-fill.med  { background: var(--med); }
.cat-fill.low  { background: var(--low); }
.cat-fill.info { background: var(--ink3); }
.cat-count  { font-family: var(--mono); font-size: 8pt; font-weight: 700; color: var(--ink2); width: 8mm; text-align: right; flex-shrink: 0; }

/* Finding index table — margin-top: -15mm cancels the thead spacer on first occurrence */
/* table-layout: fixed enforces width:100% strictly — prevents the long CWE/OWASP ref
   strings from pushing the table past the body-section right padding (14mm). */
.fi-table   { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 9pt; margin-top: -15mm; }
.fi-table tfoot { display: table-footer-group; }
.fi-table th { font-family: var(--mono); font-size: 7pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.09em; padding: 2mm 3mm; border-bottom: 1.5px solid var(--paper3); background: var(--paper2); text-align: left; }
.fi-table td { padding: 2.5mm 3mm; border-bottom: 1px solid var(--paper3); vertical-align: middle; color: var(--ink); break-inside: avoid; overflow: hidden; word-break: break-word; overflow-wrap: break-word; }
.fi-table .fi-id { font-family: var(--mono); font-size: 8pt; font-weight: 700; color: var(--accent); white-space: nowrap; }
.fi-table .fi-cvss { font-family: var(--mono); font-size: 8pt; font-weight: 700; white-space: nowrap; }
.fi-table .fi-cvss.crit { color: var(--crit); }
.fi-table .fi-cvss.high { color: var(--high); }
.fi-table .fi-cvss.med  { color: var(--med); }
.fi-table .fi-cvss.low  { color: var(--low); }

/* ════════════════════════════════════════════════════════════════════════
   THREAT MODEL
════════════════════════════════════════════════════════════════════════ */
.tm-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; margin-bottom: 7mm; }
/* min-width: 0 prevents grid cells from overflowing their track when table content
   is wider than the allocated 1fr column — without it, the right table bleeds past
   the body-section right padding (--pad: 14mm). */
.tm-block   { break-inside: avoid; min-width: 0; overflow: hidden; }
.tm-block-title { font-family: var(--mono); font-size: 6pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 2.5mm; }
.tm-table   { width: 100%; border-collapse: collapse; font-size: 9pt; }
.tm-table th { font-family: var(--mono); font-size: 7pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.08em; padding: 2mm 3mm; border-bottom: 1.5px solid var(--paper3); background: var(--paper2); text-align: left; white-space: nowrap; }
.tm-table td { padding: 2.5mm 3mm; border-bottom: 1px solid var(--paper3); vertical-align: top; color: var(--ink); word-break: break-word; }
.tm-table tr:last-child td { border-bottom: none; }
.tm-cap-high { font-size: 8pt; font-weight: 700; color: var(--crit); font-family: var(--mono); }
.tm-cap-med  { font-size: 8pt; font-weight: 700; color: var(--high); font-family: var(--mono); }
.tm-cap-low  { font-size: 8pt; font-weight: 700; color: var(--low);  font-family: var(--mono); }
/* padding-top: 14mm provides clearance when a tm-full block starts at the top of a
   continuation page (fixed header is 12mm). margin-top: -10mm cancels most of that
   padding mid-page so the visual gap between sub-sections is ~4mm (14-10), not 14mm.
   At a page break the negative margin is lost and the full 14mm clearance is preserved. */
.tm-full { padding-top: 14mm; margin-top: -10mm; margin-bottom: 3mm; break-inside: avoid; }

/* ════════════════════════════════════════════════════════════════════════
   ATTACK CHAIN ANALYSIS
════════════════════════════════════════════════════════════════════════ */
.chain-card { border: 1px solid var(--paper3); border-radius: 4px; margin-bottom: 7mm; overflow: hidden; break-inside: avoid; }
.chain-header { display: flex; align-items: center; gap: 3mm; padding: 3mm 4mm; background: var(--paper2); border-bottom: 1px solid var(--paper3); }
.chain-id     { font-family: var(--mono); font-size: 6pt; font-weight: 700; color: var(--ink2); letter-spacing: 0.08em; }
.chain-title  { font-family: var(--display); font-size: 10pt; font-weight: 700; color: var(--ink); flex: 1; }
.chain-body   { padding: 4mm; }
.chain-steps  { display: flex; flex-direction: column; gap: 2mm; margin-bottom: 4mm; }
.chain-step   { display: flex; align-items: flex-start; gap: 3mm; break-inside: avoid; }
.chain-step-num { width: 7mm; height: 7mm; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 7pt; font-weight: 700; color: #fff; flex-shrink: 0; margin-top: 0.5mm; }
.chain-step-num.crit { background: var(--crit); }
.chain-step-num.high { background: var(--high); }
.chain-step-num.med  { background: var(--med); }
.chain-step-num.low  { background: var(--low); }
.chain-step-num.info { background: var(--ink3); }
.chain-step-content  { flex: 1; }
.chain-step-finding  { font-family: var(--mono); font-size: 8pt; font-weight: 700; color: var(--accent); margin-bottom: 1mm; }
.chain-step-action   { font-size: 9pt; color: var(--ink); margin-bottom: 1mm; line-height: 1.4; }
.chain-step-outcome  { font-size: 8.5pt; color: var(--ink2); font-style: italic; line-height: 1.4; }
.chain-connector     { margin-left: 3mm; width: 0; height: 3mm; border-left: 1.5px dashed var(--paper3); }
.chain-impact-box    { background: var(--paper2); border-left: 3px solid var(--crit); border-radius: 2px; padding: 2.5mm 3mm; font-size: 7.5pt; }
.chain-impact-label  { font-family: var(--mono); font-size: 6pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1mm; }

/* ════════════════════════════════════════════════════════════════════════
   COMPLIANCE MAPPING
════════════════════════════════════════════════════════════════════════ */
.comp-table { width: 100%; border-collapse: collapse; font-size: 9pt; }
.comp-table th { font-family: var(--mono); font-size: 7pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.09em; padding: 2mm 2.5mm; border-bottom: 1.5px solid var(--paper3); background: var(--paper2); text-align: left; white-space: nowrap; }
.comp-table td { padding: 2mm 2.5mm; border-bottom: 1px solid var(--paper3); vertical-align: middle; break-inside: avoid; }
.comp-table tr:last-child td { border-bottom: none; }
.comp-ref    { font-family: var(--mono); font-size: 8pt; color: var(--ink2); white-space: nowrap; }
.comp-ref.match { color: var(--accent); font-weight: 700; }

/* ════════════════════════════════════════════════════════════════════════
   SECURITY STRENGTHS
════════════════════════════════════════════════════════════════════════ */
.strength-list  { display: flex; flex-direction: column; gap: 3mm; }
.strength-card  { display: flex; gap: 3mm; align-items: flex-start; padding: 3mm 4mm; background: #F0FAF5; border: 1px solid #C6E8D6; border-left: 3px solid var(--low); border-radius: 4px; break-inside: avoid; }
.strength-icon  { font-size: 9pt; flex-shrink: 0; margin-top: 0.5mm; }
.strength-body  { flex: 1; }
.strength-title { font-size: 8.5pt; font-weight: 700; color: var(--ink); margin-bottom: 1mm; }
.strength-desc  { font-size: 9pt; color: var(--ink2); line-height: 1.6; }

/* ════════════════════════════════════════════════════════════════════════
   METHODOLOGY COVERAGE
════════════════════════════════════════════════════════════════════════ */
.meth-meta  { display: flex; gap: 4mm; flex-wrap: wrap; margin-bottom: 6mm; }
.meth-pill  { background: var(--paper2); border: 1px solid var(--paper3); border-radius: 3px; padding: 2mm 3.5mm; font-size: 9pt; color: var(--ink); break-inside: avoid; }
.meth-pill strong { color: var(--ink2); font-family: var(--mono); font-size: 7pt; text-transform: uppercase; letter-spacing: 0.08em; display: block; margin-bottom: 1mm; }
.cov-table  { width: 100%; border-collapse: collapse; font-size: 9pt; }
.cov-table th { font-family: var(--mono); font-size: 7pt; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing: 0.09em; padding: 2mm 3mm; border-bottom: 1.5px solid var(--paper3); background: var(--paper2); text-align: left; }
.cov-table td { padding: 2.5mm 3mm; border-bottom: 1px solid var(--paper3); vertical-align: middle; break-inside: avoid; }
.cov-table tr:last-child td { border-bottom: none; }
.cov-status { display: inline-flex; align-items: center; gap: 1.5mm; font-family: var(--mono); font-size: 8pt; font-weight: 700; }
.cov-status.tested { color: var(--low); }
.cov-status.partial { color: var(--med); }
.cov-status.na { color: var(--ink3); }
.cov-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.cov-dot.tested  { background: var(--low); }
.cov-dot.partial { background: var(--med); }
.cov-dot.na      { background: var(--ink3); }
.cov-findings { font-family: var(--mono); font-size: 8pt; font-weight: 700; }
.cov-findings.has-findings { color: var(--high); }
.cov-findings.no-findings  { color: var(--ink3); }

@media print {
  .cover       { break-after: page; }
  .break-before { break-before: page; }
  .finding     { break-inside: avoid; page-break-inside: avoid; }
}
"""


# ─── HTML template helpers ────────────────────────────────────────────────────

import re as _re

def e(s: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(s), quote=True)

def ec(s: str) -> str:
    """HTML-escape then convert backtick-quoted spans to <code> elements."""
    escaped = html.escape(str(s), quote=True)
    return _re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)


def severity_bar_width(count: int, max_count: int) -> str:
    if max_count == 0:
        return "0%"
    return f"{min(100, int(count / max_count * 100))}%"


def build_cover(data: dict, counts: dict) -> str:
    project_name = e(data.get("project_name", "Unknown Project"))
    report_date  = e(data.get("report_date", ""))
    branch       = data.get("branch", "")
    language     = e(data.get("language", ""))
    framework    = e(data.get("framework", ""))
    scope_desc   = e(data.get("assessment_type", "Static Code Review · Architecture Audit"))
    # Only count the four displayed severities (INFO is not shown in cover blocks)
    COVER_SEVS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    total        = sum(counts.get(s, 0) for s in COVER_SEVS)
    max_c        = max((counts.get(s, 0) for s in COVER_SEVS), default=1) or 1

    meta_items = [
        ("Audit Date", report_date),
        ("Branch", e(branch) if branch and branch != "N/A" else "N/A"),
        ("Assessment", "Static Code Review"),
        ("Status", "Final Report"),
    ]
    meta_html = "".join(
        f'<div class="cover-meta-item"><label>{e(k)}</label><span>{v}</span></div>'
        for k, v in meta_items
    )

    sev_blocks_html = ""
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        c = counts.get(sev, 0)
        cls = SEV_CLASS[sev]
        w   = severity_bar_width(c, max_c)
        sev_blocks_html += f"""
      <div class="sev-block {cls}">
        <div class="sev-block-label">{sev.title()}</div>
        <div class="sev-block-bar-wrap"><div class="sev-block-bar" style="width:{w}"></div></div>
        <div class="sev-block-count">{c}</div>
      </div>"""

    # 5×5 risk matrix (static design asset)
    # Rows top→bottom = likelihood 5→1 (high→low)
    # Cols left→right = impact 1→5 (low→high)
    # Standard coloring: risk = likelihood × impact
    #   Row 5 (L=5): M  H  H  C  C
    #   Row 4 (L=4): L  M  H  H  C
    #   Row 3 (L=3): L  M  M  H  H
    #   Row 2 (L=2): N  L  M  M  H
    #   Row 1 (L=1): N  N  L  M  M
    def mc(cls, n=1): return f'<div class="matrix-cell mc-{cls}"></div>' * n
    matrix_html = (
        mc("med") + mc("high",2) + mc("crit",2) +   # row 5
        mc("low") + mc("med")    + mc("high",2) + mc("crit") +  # row 4
        mc("low") + mc("med",2)  + mc("high",2) +   # row 3
        mc("nil") + mc("low")    + mc("med",2) + mc("high") +   # row 2
        mc("nil",2) + mc("low")  + mc("med",2)       # row 1
    )

    lang_display = language + (f" / {framework}" if framework and framework.lower() != "none" else "")

    return f"""
<div class="cover">
  <div class="cover-left">
    <div class="cover-eyebrow">{project_name} · Security Intelligence</div>
    <div class="cover-title-block">
      <div class="cover-label">Audit Report · {report_date[:4] if report_date else "2025"}</div>
      <h1 class="cover-h1">VULN<span>ERABILITY</span>ASSESS<span>MENT</span></h1>
      <div class="cover-divider"></div>
      <div class="cover-project">
        <strong>{project_name}</strong>
        {scope_desc}<br/>
        {e(lang_display)}
      </div>
    </div>
    <div class="cover-meta-grid">{meta_html}</div>
    <div class="cover-confidential">Confidential &amp; Proprietary</div>
  </div>
  <div class="cover-right">
    <div class="cover-right-eyebrow">Risk Overview</div>
    <div class="cr-mid">
      <div class="total-badge">
        <div class="total-number">{total}</div>
        <div class="total-sub">security findings<br/>identified</div>
      </div>
      <div style="height:6mm"></div>
      <div class="risk-headline">Findings by Severity</div>
      <div class="severity-blocks">{sev_blocks_html}</div>
      <div style="height:8mm"></div>
      <div class="matrix-section">
        <div class="matrix-label">Likelihood × Impact Matrix</div>
        <div class="risk-matrix">{matrix_html}</div>
        <div class="matrix-axes"><span>Low Impact →</span><span>→ High Impact</span></div>
      </div>
    </div>
  </div>
</div>
"""


def build_exec_summary(data: dict, counts: dict) -> str:
    project_name = e(data.get("project_name", "the target codebase"))
    COVER_SEVS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    total = sum(counts.get(s, 0) for s in COVER_SEVS)

    # Build severity text list — INFO excluded to match cover/stat cards
    parts = []
    for sev in COVER_SEVS:
        c = counts.get(sev, 0)
        if c:
            parts.append(f"{c} {sev.lower()}")
    sev_text = ", ".join(parts[:-1]) + (f" and {parts[-1]}" if len(parts) > 1 else (parts[0] if parts else "0"))

    intro = (
        f"A comprehensive <strong>static code review and architecture audit</strong> was performed on "
        f"<strong>{project_name}</strong>. The assessment identified "
        f"<strong>{total} security finding{'s' if total != 1 else ''}</strong> — {sev_text} — "
        f"representing risks that range from authentication bypass to information disclosure. "
        f"CRITICAL and HIGH severity findings must be remediated with the highest priority."
    )

    stat_cards = ""
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        cls = SEV_CLASS[sev]
        stat_cards += f'<div class="stat-card {cls}"><div class="stat-num">{counts.get(sev,0)}</div><div class="stat-label">{sev.title()}</div></div>'

    # Distribution bar (flex segments)
    dist_segs = ""
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        c = counts.get(sev, 0)
        if c:
            cls = SEV_CLASS[sev]
            label = f"{c} {sev[:4] if sev == 'CRITICAL' else sev[:3]}"
            dist_segs += f'<div class="dist-seg {cls}" style="flex:{c}">{label}</div>'

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">01</span>
    <h2 class="section-title">Executive Summary</h2>
  </div>
  <div class="section-rule"></div>
  <p class="exec-intro">{intro}</p>
  <div class="stat-row">{stat_cards}</div>
  <div class="dist-label">Risk Distribution</div>
  <div class="dist-bar">{dist_segs}</div>
</div>
"""


def build_scope_section(data: dict) -> str:
    scope_rows = data.get("scope_rows", [])
    data_flow  = e(data.get("data_flow_summary", ""))
    ext_deps   = data.get("external_deps", [])

    # ── 02-sub: Scope table (no extra number — it's the primary content)
    if len(scope_rows) > 1:
        headers = scope_rows[0]
        rows    = scope_rows[1:]
        th_html = "".join(f"<th>{e(h)}</th>" for h in headers)
        tr_html = ""
        for row in rows:
            tr_html += "<tr>" + "".join(f"<td>{e(str(cell))}</td>" for cell in row) + "</tr>"
        scope_table = f'<table class="scope-table"><thead><tr>{th_html}</tr></thead><tbody>{tr_html}</tbody></table>'
    else:
        scope_table = '<p class="exec-intro">Scope details not provided.</p>'

    # ── Data Flow Summary — subsection inside Scope & Architecture (no top-level number)
    flow_html = ""
    if data_flow:
        flow_html = f"""
  <div class="subsec-heading" style="margin-top:10mm">
    <span class="subsec-title">Data Flow Summary</span>
  </div>
  <div class="section-rule" style="margin-bottom:4mm"></div>
  <p class="exec-intro" style="margin-bottom:0">{data_flow}</p>"""

    # ── External Dependencies — subsection inside Scope & Architecture (no top-level number)
    # Force onto its own page (break-before: page) so the table header is
    # always visible at the top and the table never starts mid-page.
    deps_html = ""
    if len(ext_deps) > 1:
        dep_headers = ext_deps[0]
        dep_rows    = ext_deps[1:]
        dth = "".join(f"<th>{e(h)}</th>" for h in dep_headers)
        dtr = "".join(
            "<tr>" + "".join(f"<td>{e(str(cell))}</td>" for cell in row) + "</tr>"
            for row in dep_rows
        )
        deps_html = f"""
  <div style="break-before: page; padding-top: 18mm">
    <div class="subsec-heading">
      <span class="subsec-title">External Dependencies</span>
    </div>
    <div class="section-rule" style="margin-bottom:4mm"></div>
    <table class="scope-table"><thead><tr>{dth}</tr></thead><tbody>{dtr}</tbody></table>
  </div>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">02</span>
    <h2 class="section-title">Scope &amp; Architecture</h2>
  </div>
  <div class="section-rule"></div>
  {scope_table}
  {flow_html}
  {deps_html}
</div>
"""


def build_finding_card(f: dict) -> str:
    sev = f.get("severity", "MEDIUM").upper()
    cls = SEV_CLASS.get(sev, "med")

    fid      = e(f.get("id", "VUL-???"))
    # Extract first CWE only: "CWE-XXX · <name>" — drop all other references
    _raw_refs = f.get("references", "")
    _cwe_m = _re.search(r'CWE-(\d+)(?:\s*[:\-–]\s*([^·\n]+?))?(?:\s*·|$)', _raw_refs)
    if _cwe_m:
        _cwe_num  = f"CWE-{_cwe_m.group(1)}"
        _cwe_name = (_cwe_m.group(2) or "").strip().rstrip("·").strip()
        cwe_ref   = e(f"{_cwe_num} · {_cwe_name}" if _cwe_name else _cwe_num)
    else:
        cwe_ref   = ""
    title    = e(f.get("title", "Untitled Finding"))
    cvss     = e(str(f.get("cvss", "N/A")))
    location = e(f.get("location", "Unknown"))
    desc     = ec(f.get("description", ""))
    impact   = ec(f.get("impact", ""))
    evidence = f.get("evidence", "")
    remed    = f.get("remediation", "")

    # Evidence block — preserve whitespace, escape HTML
    evidence_html = ""
    if evidence:
        evidence_html = f"""
        <div class="finding-field">
          <div class="field-label">Evidence</div>
          <div class="code-block">{html.escape(evidence)}</div>
        </div>"""

    # Remediation — split on newlines OR inline numbered steps ("1. ... 2. ...")
    remed_html = ""
    if remed:
        # Try newline split first; strip any leading "N." prefix
        lines = [_re.sub(r'^\d+\.\s*', '', l.strip().lstrip("-•→").strip()) for l in remed.splitlines() if l.strip().lstrip("-•→").strip()]
        # If still one blob, try splitting on inline "N. " pattern
        if len(lines) <= 1:
            parts = _re.split(r'(?<!\w)(\d+)\.\s+', remed.strip())
            # parts = ['', '1', 'step one text', '2', 'step two text', ...]
            if len(parts) > 3:
                lines = []
                i = 1
                while i < len(parts) - 1:
                    text = parts[i + 1].strip().rstrip()
                    if text:
                        lines.append(text)  # drop "N." prefix — CSS bullet handles ordering
                    i += 2
        if lines:
            items = "".join(f"<li>{ec(l)}</li>" for l in lines)
            remed_html = f"""
        <div class="finding-field">
          <div class="field-label">Remediation</div>
          <ul class="remed-list">{items}</ul>
        </div>"""
        else:
            remed_html = f"""
        <div class="finding-field">
          <div class="field-label">Remediation</div>
          <div class="field-text">{e(remed)}</div>
        </div>"""

    return f"""
    <div class="finding-wrap"><div class="finding {cls}">
      <div class="finding-header">
        <div class="finding-hdr-main">
          <div class="finding-id">{fid} · {cwe_ref}</div>
          <div class="finding-title">{title}</div>
        </div>
        <div class="finding-hdr-right">
          <div class="cvss-score">{cvss}</div>
          <div class="cvss-label">CVSS v3.1</div>
        </div>
      </div>
      <div class="finding-location">
        <span class="finding-location-icon">FILE</span>
        <span class="finding-location-path">{location}</span>
      </div>
      <div class="finding-body">
        <div class="finding-field">
          <div class="field-label">Description</div>
          <div class="field-text">{desc}</div>
        </div>
        <div class="finding-field">
          <div class="field-label">Impact</div>
          <div class="impact-block"><div class="impact-text">{impact}</div></div>
        </div>
        {evidence_html}
        {remed_html}
      </div>
    </div></div>"""


def build_findings_section(findings: list, sec_num: str = "04") -> str:
    # Group by severity in canonical order
    groups: dict[str, list] = {s: [] for s in SEVERITY_ORDER}
    for f in findings:
        sev = f.get("severity", "MEDIUM").upper()
        if sev not in groups:
            sev = "MEDIUM"
        groups[sev].append(f)

    body = ""
    for sev in SEVERITY_ORDER:
        items = groups[sev]
        if not items:
            continue
        cls          = SEV_CLASS[sev]
        tagline      = SEV_TAGLINE[sev]
        cards        = "".join(build_finding_card(f) for f in items)
        is_first_grp = not body  # HIGH (or first non-empty sev) gets no extra top padding
        grp_cls      = "findings-group" if is_first_grp else "findings-group group-non-first"
        body += f"""
  <div class="{grp_cls}">
    <div class="group-header">
      <span class="group-badge {cls}">{sev.title()}</span>
      <span class="group-count">{len(items)} finding{'s' if len(items) != 1 else ''} · {tagline}</span>
    </div>
    {cards}
  </div>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Detailed Findings</h2>
  </div>
  <div class="section-rule"></div>
  {body}
</div>
"""


def build_risk_dashboard(findings: list, sec_num: str = "02") -> str:
    """Risk Dashboard — severity counts, OWASP category breakdown, full finding index."""
    counts = {}
    for f in findings:
        sev = f.get("severity", "MEDIUM").upper()
        counts[sev] = counts.get(sev, 0) + 1

    # ── Severity count cards ────────────────────────────────────────────
    sev_cards = ""
    for sev, cls in [("CRITICAL", "crit"), ("HIGH", "high"), ("MEDIUM", "med"), ("LOW", "low"), ("INFO", "info")]:
        n = counts.get(sev, 0)
        label = sev.title()
        sev_cards += f"""
    <div class="dash-card {cls}">
      <div class="dash-card-label">{label}</div>
      <div class="dash-card-value">{n}</div>
      <div class="dash-card-sub">finding{'s' if n != 1 else ''}</div>
    </div>"""

    # ── OWASP category breakdown (derived from references field) ────────
    # Parse "CWE-79 · OWASP A03:2021 — Injection" style references
    import re as _re2
    category_counts: dict[str, tuple[int, str]] = {}  # label → (count, max_sev_cls)
    sev_rank = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}
    for f in findings:
        refs = f.get("references", "")
        sev  = f.get("severity", "LOW").upper()
        # Match "OWASP A0X:2021 — Label" or plain "OWASP A0X:2021"
        m = _re2.search(r'OWASP\s+(A\d+:\d+)(?:\s*[—–-]\s*([^·\n]+))?', refs)
        if m:
            code  = m.group(1).strip()
            label = m.group(2).strip() if m.group(2) else code
            key   = f"{code} — {label}"
            prev_count, prev_cls = category_counts.get(key, (0, "info"))
            prev_rank = sev_rank.get(prev_cls.upper() if prev_cls != "info" else "INFO", 1)
            new_cls   = SEV_CLASS.get(sev, "low")
            new_rank  = sev_rank.get(sev, 1)
            category_counts[key] = (prev_count + 1, new_cls if new_rank > prev_rank else prev_cls)

    max_cat = max((v[0] for v in category_counts.values()), default=1)
    cat_rows_html = ""
    for cat_label, (cnt, cls) in sorted(category_counts.items(), key=lambda x: -x[1][0]):
        pct = int(cnt / max_cat * 100)
        cat_rows_html += f"""
    <div class="cat-row">
      <div class="cat-label">{e(cat_label)}</div>
      <div class="cat-track"><div class="cat-fill {cls}" style="width:{pct}%"></div></div>
      <div class="cat-count">{cnt}</div>
    </div>"""
    if not cat_rows_html:
        cat_rows_html = '<div style="color:var(--ink3);font-size:7.5pt">No OWASP category data in findings references.</div>'

    # ── Finding index table ─────────────────────────────────────────────
    index_rows = ""
    for f in findings:
        sev  = f.get("severity", "MEDIUM").upper()
        cls  = SEV_CLASS.get(sev, "low")
        fid  = e(f.get("id", ""))
        cvss = e(str(f.get("cvss", "—")))
        title = e(f.get("title", ""))
        loc   = e(f.get("location", "").split(":")[0])
        refs  = e(f.get("references", ""))
        index_rows += f"""
    <tr>
      <td class="fi-id">{fid}</td>
      <td><span class="sev-pill {cls}">{sev.title()}</span></td>
      <td class="fi-cvss {cls}">{cvss}</td>
      <td>{title}</td>
      <td style="color:var(--ink2);font-size:7pt;word-break:break-all;overflow-wrap:break-word">{loc}</td>
      <td style="color:var(--ink2);font-size:6.5pt;font-family:var(--mono);word-break:break-word;overflow-wrap:break-word">{refs}</td>
    </tr>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Risk Dashboard</h2>
  </div>
  <div class="section-rule"></div>

  <div class="dash-grid">{sev_cards}
  </div>

  <div class="subsec-heading">
    <span class="subsec-title">Finding Distribution by OWASP Category</span>
  </div>
  <div class="section-rule" style="margin-bottom:5mm"></div>
  <div class="cat-rows">{cat_rows_html}
  </div>

  <div class="subsec-heading">
    <span class="subsec-title">Finding Index</span>
  </div>
  <div class="section-rule" style="margin-bottom:4mm"></div>
  <table class="fi-table">
    <thead>
      <tr class="thead-spacer"><td colspan="6" style="padding:0;height:15mm;border:none;background:transparent;"></td></tr>
      <tr>
        <th style="width:9%">ID</th><th style="width:11%">Severity</th>
        <th style="width:7%">CVSS</th><th style="width:22%">Title</th>
        <th style="width:31%">Location</th><th style="width:20%">CWE / OWASP</th>
      </tr>
    </thead>
    <tbody>{index_rows}
    </tbody>
    <tfoot><tr><td colspan="6" style="padding:0;height:12mm;border:none;background:transparent;"></td></tr></tfoot>
  </table>
</div>
"""


def build_threat_model(data: dict, sec_num: str = "03") -> str:
    """Threat Model & Attack Surface — assets, actors, entry points."""
    tm = data.get("threat_model", {})
    assets        = tm.get("assets", [])
    threat_actors = tm.get("threat_actors", [])
    attack_surface= tm.get("attack_surface", [])
    trust_boundaries = tm.get("trust_boundaries", [])

    def _table(rows: list) -> str:
        if not rows:
            return '<p style="color:var(--ink3);font-size:7.5pt">No data provided.</p>'
        header = rows[0]
        body   = rows[1:]
        ths = "".join(f"<th>{e(h)}</th>" for h in header)
        trs = ""
        for row in body:
            tds = "".join(f"<td>{e(str(cell))}</td>" for cell in row)
            trs += f"<tr>{tds}</tr>"
        return f'<table class="tm-table"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'

    cap_html = ""
    if trust_boundaries:
        items = "".join(f'<div style="display:flex;align-items:center;gap:2mm;margin-bottom:1.5mm;font-size:9pt"><span style="color:var(--accent);font-family:var(--mono);font-size:8.5pt">→</span>{e(b)}</div>' for b in trust_boundaries)
        cap_html = f"""
  <div class="tm-full">
    <div class="tm-block-title">Trust Boundaries</div>
    {items}
  </div>"""

    assets_html  = _table(assets)        if assets        else '<p style="color:var(--ink3);font-size:7.5pt">Not provided — add <code>threat_model.assets</code> to findings JSON.</p>'
    actors_html  = _table(threat_actors) if threat_actors else '<p style="color:var(--ink3);font-size:7.5pt">Not provided — add <code>threat_model.threat_actors</code> to findings JSON.</p>'
    surface_html = _table(attack_surface)if attack_surface else '<p style="color:var(--ink3);font-size:7.5pt">Not provided — add <code>threat_model.attack_surface</code> to findings JSON.</p>'

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Threat Model &amp; Attack Surface</h2>
  </div>
  <div class="section-rule"></div>

  <div class="tm-full" style="padding-top:0;margin-top:0">
    <div class="tm-block-title">Protected Assets</div>
    {assets_html}
  </div>

  <div class="tm-full">
    <div class="tm-block-title">Threat Actors</div>
    {actors_html}
  </div>

  <div class="tm-full">
    <div class="tm-block-title">Attack Surface &amp; Entry Points</div>
    {surface_html}
  </div>
  {cap_html}
</div>
"""


def build_attack_chains(data: dict, sec_num: str = "06") -> str:
    """Attack Chain Analysis — multi-step exploit narratives."""
    chains = data.get("attack_chains", [])
    if not chains:
        return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Attack Chain Analysis</h2>
  </div>
  <div class="section-rule"></div>
  <p style="color:var(--ink2);font-size:8pt">No attack chains identified. Add <code>attack_chains</code> array to findings JSON to populate this section.</p>
</div>
"""

    chains_html = ""
    for chain in chains:
        chain_id  = e(chain.get("id", "CHAIN-001"))
        title     = e(chain.get("title", ""))
        sev       = chain.get("severity", "HIGH").upper()
        cls       = SEV_CLASS.get(sev, "high")
        impact    = chain.get("impact", "")
        prereqs   = chain.get("prerequisites", "")
        steps     = chain.get("steps", [])

        steps_html = ""
        for i, step in enumerate(steps):
            step_sev = ""
            fid = step.get("finding_id", "")
            # Try to get severity from finding id
            step_cls = cls  # fallback to chain severity
            action  = e(step.get("action", ""))
            outcome = e(step.get("outcome", ""))
            connector = '<div class="chain-connector"></div>' if i < len(steps) - 1 else ""
            steps_html += f"""
        <div class="chain-step">
          <div class="chain-step-num {step_cls}">{step.get('step', i+1)}</div>
          <div class="chain-step-content">
            <div class="chain-step-finding">{e(fid)}</div>
            <div class="chain-step-action">{action}</div>
            <div class="chain-step-outcome">&#8627; {outcome}</div>
          </div>
        </div>
        {connector}"""

        impact_box = ""
        if impact:
            chains_html_prereq = f'<div style="font-size:7pt;color:var(--ink2);margin-bottom:2mm"><span style="font-family:var(--mono);font-size:6pt;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.08em">Prerequisites: </span>{e(prereqs)}</div>' if prereqs else ""
            impact_box = f"""
        {chains_html_prereq}
        <div class="chain-impact-box">
          <div class="chain-impact-label">Final Impact</div>
          {e(impact)}
        </div>"""

        chains_html += f"""
  <div style="padding-top:14mm;margin-top:-10mm">
  <div class="chain-card">
    <div class="chain-header">
      <div class="chain-id">{chain_id}</div>
      <div class="chain-title">{title}</div>
      <span class="sev-pill {cls}">{sev.title()}</span>
    </div>
    <div class="chain-body">
      <div class="chain-steps">{steps_html}
      </div>
      {impact_box}
    </div>
  </div>
  </div>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Attack Chain Analysis</h2>
  </div>
  <div class="section-rule"></div>
  {chains_html}
</div>
"""


def build_compliance_mapping(findings: list, sec_num: str = "07") -> str:
    """Compliance Mapping — findings × OWASP Top 10 / CWE / ISO 27001 / NIST CSF / PCI DSS."""
    import re as _re3

    # ISO 27001:2022 and NIST CSF mappings keyed by OWASP 2025 category code
    # A01-Broken Access Control, A02-Security Misconfiguration, A03-Supply Chain,
    # A04-Cryptographic Failures, A05-Injection, A06-Insecure Design,
    # A07-Auth Failures, A08-Data Integrity, A09-Logging & Alerting, A10-Exception Handling
    _ISO_MAP = {
        "A01": "A.8.2, A.8.3",   "A02": "A.8.9",   "A03": "A.8.8",
        "A04": "A.8.24",          "A05": "A.8.28",  "A06": "A.8.25",
        "A07": "A.8.5",           "A08": "A.8.11",  "A09": "A.8.15",
        "A10": "A.8.26",
    }
    _NIST_MAP = {
        "A01": "PR.AC-4",   "A02": "PR.IP-1",  "A03": "ID.SC-2",
        "A04": "PR.DS-2",   "A05": "PR.DS-5",  "A06": "PR.IP-2",
        "A07": "PR.AC-7",   "A08": "PR.DS-6",  "A09": "DE.AE-3",
        "A10": "DE.AE-2",
    }
    _PCI_MAP  = {
        "A01": "Req 7",     "A02": "Req 2",    "A03": "Req 6.3.3",
        "A04": "Req 4",     "A05": "Req 6.2.4","A06": "Req 6.2",
        "A07": "Req 8.3",   "A08": "Req 6.2.4","A09": "Req 10.2",
        "A10": "Req 6.2.4",
    }

    rows_html = ""
    for f in findings:
        refs  = f.get("references", "")
        sev   = f.get("severity", "MEDIUM").upper()
        cls   = SEV_CLASS.get(sev, "low")
        fid   = e(f.get("id", ""))
        title = e(f.get("title", ""))

        # Parse CWE
        cwe_m = _re3.search(r'(CWE-\d+)', refs)
        cwe   = cwe_m.group(1) if cwe_m else "—"

        # Parse OWASP
        owasp_m = _re3.search(r'OWASP\s+(A\d+):\d+', refs)
        owasp   = f"{owasp_m.group(1)}:2025" if owasp_m else "—"
        code    = owasp_m.group(1) if owasp_m else ""

        iso   = _ISO_MAP.get(code, "—")
        nist  = _NIST_MAP.get(code, "—")
        pci   = _PCI_MAP.get(code, "—")

        rows_html += f"""
    <tr>
      <td style="font-family:var(--mono);font-size:7pt;font-weight:700;color:var(--accent);white-space:nowrap">{fid}</td>
      <td><span class="sev-pill {cls}">{sev.title()}</span></td>
      <td style="max-width:50mm">{title}</td>
      <td class="comp-ref{'  match' if cwe != '—' else ''}">{e(cwe)}</td>
      <td class="comp-ref{'  match' if owasp != '—' else ''}">{e(owasp)}</td>
      <td class="comp-ref{'  match' if iso != '—' else ''}">{e(iso)}</td>
      <td class="comp-ref{'  match' if nist != '—' else ''}">{e(nist)}</td>
      <td class="comp-ref{'  match' if pci != '—' else ''}">{e(pci)}</td>
    </tr>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Compliance Mapping</h2>
  </div>
  <div class="section-rule"></div>
  <p style="font-size:9pt;color:var(--ink2);margin-bottom:5mm">Each finding mapped to applicable controls across OWASP Top 10 (2025), CWE, ISO 27001:2022, NIST CSF, and PCI DSS v4.0. Mapping is advisory — consult a qualified assessor for formal compliance attestation.</p>
  <table class="comp-table">
    <thead>
      <tr class="thead-spacer"><td colspan="8" style="padding:0;height:15mm;border:none;background:transparent;"></td></tr>
      <tr>
        <th>ID</th><th>Severity</th><th>Finding</th>
        <th>CWE</th><th>OWASP 2025</th>
        <th>ISO 27001:2022</th><th>NIST CSF</th><th>PCI DSS v4</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
    <tfoot><tr><td colspan="8" style="padding:0;height:12mm;border:none;background:transparent;"></td></tr></tfoot>
  </table>
</div>
"""


def build_security_strengths(data: dict, sec_num: str = "08") -> str:
    """Security Strengths & Positive Observations."""
    strengths = data.get("security_strengths", [])
    if not strengths:
        return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Security Strengths &amp; Observations</h2>
  </div>
  <div class="section-rule"></div>
  <p style="color:var(--ink2);font-size:8pt">No security strengths provided. Add <code>security_strengths</code> array to findings JSON to populate this section.</p>
</div>
"""
    cards = ""
    for s in strengths:
        cards += f"""
    <div class="strength-card">
      <div class="strength-icon">✓</div>
      <div class="strength-body">
        <div class="strength-title">{e(s.get('title', ''))}</div>
        <div class="strength-desc">{ec(s.get('description', ''))}</div>
      </div>
    </div>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">{e(sec_num)}</span>
    <h2 class="section-title">Security Strengths &amp; Observations</h2>
  </div>
  <div class="section-rule"></div>
  <p style="font-size:9pt;color:var(--ink2);margin-bottom:5mm">The following controls were found to be correctly implemented and should be preserved during remediation efforts.</p>
  <div class="strength-list">{cards}
  </div>
</div>
"""


def build_methodology(data: dict, sec_num: str = "") -> str:
    """Methodology & checklist coverage — injected into scope section."""
    meth = data.get("methodology", {})
    if not meth:
        return ""

    framework = e(meth.get("framework", "OWASP WSTG v4.2 · CWE Top 25 · NIST SP 800-115"))
    meth_type = e(meth.get("type", "White-Box Static Analysis + Architecture Review"))
    coverage  = meth.get("coverage", [])

    cov_rows = ""
    for item in coverage:
        cat    = e(item.get("category", ""))
        status = item.get("status", "tested").lower()
        n      = item.get("findings", 0)
        status_label = {"tested": "Tested", "partial": "Partial", "na": "N/A"}.get(status, status.title())
        findings_cls = "has-findings" if n > 0 else "no-findings"
        findings_txt = str(n) if n > 0 else "—"
        cov_rows += f"""
      <tr>
        <td>{cat}</td>
        <td><span class="cov-status {status}"><span class="cov-dot {status}"></span>{status_label}</span></td>
        <td><span class="cov-findings {findings_cls}">{findings_txt}</span></td>
      </tr>"""

    cov_table = ""
    if cov_rows:
        cov_table = f"""
  <div style="padding-top:14mm;margin-top:-10mm">
  <table class="cov-table" style="margin-top:4mm">
    <thead>
      <tr class="thead-spacer"><td colspan="3" style="padding:0;height:15mm;border:none;background:transparent;"></td></tr>
      <tr><th>Checklist Category</th><th>Status</th><th>Findings</th></tr>
    </thead>
    <tbody>{cov_rows}
    </tbody>
    <tfoot>
      <tr><td colspan="3" style="padding:0;height:12mm;border:none;background:transparent;"></td></tr>
    </tfoot>
  </table>
  </div>"""

    return f"""
  <div class="subsec-heading" style="margin-top:7mm">
    <span class="subsec-title">Methodology &amp; Checklist Coverage</span>
  </div>
  <div class="section-rule" style="margin-bottom:4mm"></div>
  <div class="meth-meta">
    <div class="meth-pill"><strong>Framework</strong>{framework}</div>
    <div class="meth-pill"><strong>Assessment Type</strong>{meth_type}</div>
  </div>
  {cov_table}
"""


def build_roadmap(findings: list) -> str:
    # Sprint 1: CRITICAL + HIGH, Sprint 2: MEDIUM, Sprint 3: LOW
    sprint_map = {
        "CRITICAL": (1, "Sprint 1 — Immediate",  "≤ 2 weeks"),
        "HIGH":     (1, "Sprint 1 — Immediate",  "≤ 2 weeks"),
        "MEDIUM":   (2, "Sprint 2 — Short-term", "≤ 4 weeks"),
        "LOW":      (3, "Sprint 3 — Long-term",  "≤ 8 weeks"),
        "INFO":     (3, "Sprint 3 — Long-term",  "Backlog"),
    }
    sprints: dict[int, list] = {1: [], 2: [], 3: []}
    for f in findings:
        sev = f.get("severity", "LOW").upper()
        sprint_num, _, _ = sprint_map.get(sev, (3, "", ""))
        sprints[sprint_num].append(f)

    # Sprint kanban lanes (show only non-empty sprints, max 2 columns)
    lane_html = ""
    visible_sprints = [(n, sprint_map) for n in sorted(sprints) if sprints[n]]
    for sprint_num in sorted(sprints):
        items = sprints[sprint_num]
        if not items:
            continue
        _, sprint_name, sprint_tag = sprint_map.get(
            items[0].get("severity", "LOW").upper(), (sprint_num, f"Sprint {sprint_num}", "")
        )
        sprint_items_html = ""
        for f in items:
            fid   = e(f.get("id", "VUL-???"))
            title = e(f.get("title", ""))
            cls   = SEV_CLASS.get(f.get("severity", "LOW").upper(), "low")
            short_id = fid.replace("VUL-", "F-")
            sprint_items_html += f"""
        <div class="sprint-item {cls}">
          <div class="sprint-item-id">{short_id}</div>
          <div class="sprint-item-title">{title}</div>
          <div class="sprint-effort">—</div>
        </div>"""
        lane_html += f"""
    <div class="sprint-lane">
      <div class="sprint-header">
        <div class="sprint-name">{e(sprint_name)}</div>
        <div class="sprint-tag">{e(sprint_tag)}</div>
      </div>
      <div class="sprint-items">{sprint_items_html}</div>
    </div>"""

    # Full remediation table — split into per-sprint mini-tables so each
    # has its own <thead> that Chrome will keep visible without relying on
    # thead repetition across page breaks (which Chrome headless doesn't do).
    THEAD = """
    <thead>
      <tr class="thead-spacer"><td colspan="7" style="padding:0;height:15mm;border:none;background:transparent;"></td></tr>
      <tr>
        <th>ID</th><th>Severity</th><th>CVSS</th><th>Finding</th>
        <th>Effort</th><th>Owner</th><th>Sprint</th>
      </tr>
    </thead>"""

    sprint_labels  = {1: "Sprint 1", 2: "Sprint 2", 3: "Sprint 3"}
    sprint_names_l = {1: "Sprint 1 — Immediate", 2: "Sprint 2 — Short-term", 3: "Sprint 3 — Long-term"}
    sprint_tables  = ""

    for sprint_num in sorted(sprints):
        items = sprints[sprint_num]
        if not items:
            continue
        rows = ""
        for f in items:
            sev   = f.get("severity", "LOW").upper()
            cls   = SEV_CLASS.get(sev, "low")
            fid   = e(f.get("id", "VUL-???"))
            cvss  = e(str(f.get("cvss", "N/A")))
            title = e(f.get("title", ""))
            short = fid.replace("VUL-", "F-")
            rows += f"""
      <tr>
        <td class="id-cell">{short}</td>
        <td><span class="sev-pill {cls}">{sev.title()}</span></td>
        <td>{cvss}</td>
        <td>{title}</td>
        <td>—</td>
        <td>Security Team</td>
        <td>{sprint_labels[sprint_num]}</td>
      </tr>"""
        sprint_tables += f"""
  <div class="subsec-heading" style="margin-top:6mm">
    <span class="subsec-title" style="font-size:10pt">{e(sprint_names_l[sprint_num])}</span>
  </div>
  <table class="remed-table">{THEAD}<tbody>{rows}</tbody><tfoot><tr><td colspan="7" style="padding:0;height:12mm;border:none;background:transparent;"></td></tr></tfoot></table>"""

    return f"""
<div class="body-section break-before">
  <div class="section-heading">
    <span class="section-number">04</span>
    <h2 class="section-title">Remediation Roadmap</h2>
  </div>
  <div class="section-rule"></div>
  <div class="roadmap-grid">{lane_html}</div>
  {sprint_tables}
</div>
"""


# ─── Main HTML assembler ──────────────────────────────────────────────────────

def generate_html(data: dict, watermark: str = "") -> str:
    findings = data.get("findings", [])
    counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "MEDIUM").upper()
        counts[sev] = counts.get(sev, 0) + 1

    project_name = data.get("project_name", "Unknown Project")
    report_date  = data.get("report_date", "")

    watermark_html = ""
    if watermark:
        watermark_html = f'<div class="watermark">{e(watermark)}</div>'

    cover           = build_cover(data, counts)
    exec_sum        = build_exec_summary(data, counts)
    # Scope section enhanced with methodology coverage block appended inside it
    scope_sec_base  = build_scope_section(data)
    meth_block      = build_methodology(data)
    # Inject methodology before the closing </div> of the scope section
    scope_sec       = scope_sec_base.rstrip().rstrip("</div>").rstrip() + meth_block + "\n</div>\n" if meth_block else scope_sec_base
    risk_dash       = build_risk_dashboard(findings, sec_num="03")
    threat_model    = build_threat_model(data, sec_num="04")
    findings_sec    = build_findings_section(findings, sec_num="05")
    attack_chains   = build_attack_chains(data, sec_num="06")
    compliance      = build_compliance_mapping(findings, sec_num="07")
    strengths       = build_security_strengths(data, sec_num="08")

    font_html = (
        '<link rel="preconnect" href="https://fonts.googleapis.com"/>\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700'
        '&family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800'
        '&display=swap" rel="stylesheet"/>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Vulnerability Assessment — {e(project_name)}</title>
{font_html}
<style>
{CSS}
</style>
</head>
<body>

<!-- Fixed chrome: appears on every page after the cover (which masks it via z-index) -->
<header class="fixed-header">
  <div class="fh-accent"></div>
  <div class="fh-content">
    <div class="fh-title">{e(project_name)} · Vulnerability Assessment · {report_date[:4] if report_date else ""}</div>
    <div class="fh-right">CONFIDENTIAL</div>
  </div>
</header>

<footer class="fixed-footer">
  <div class="ff-left">{e(project_name)} · Security Assessment Report · Confidential</div>
  <div class="ff-right"><span class="ff-pg"></span></div>
</footer>

{watermark_html}

{cover}
{exec_sum}
{scope_sec}
{risk_dash}
{threat_model}
{findings_sec}
{attack_chains}
{compliance}
{strengths}

</body>
</html>
"""


# ─── PDF rendering ────────────────────────────────────────────────────────────

def render_pdf(html_path: str, pdf_path: str) -> None:
    chrome = find_chrome()
    if not chrome:
        print(
            f"ERROR: Chrome/Chromium not found. HTML saved to: {html_path}\n"
            "Open it in Chrome and use Ctrl+P → Save as PDF to generate the report.",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_path}",
        f"file://{html_path}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Chrome error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    _stamp_page_numbers(pdf_path)


def _stamp_page_numbers(pdf_path: str) -> None:
    """Stamp page numbers into the bottom-right footer to match .ff-pg CSS styling.

    Matches: Space Mono 700, 5.5pt, color #4A5568, right-aligned at 6mm from right edge,
    vertically centred in the 10mm footer (align-items: center).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("WARNING: PyMuPDF not installed — page numbers skipped.\n"
              "Install with: pip install pymupdf --break-system-packages", file=sys.stderr)
        return

    # Space Mono Bold TTF — same font used by .ff-pg in the HTML
    _FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "space_mono_700_normal.ttf"
    font_data = _FONT_PATH.read_bytes() if _FONT_PATH.exists() else None

    MM = 1 / 25.4 * 72  # mm → pt
    FONTSIZE = 5.5
    COLOR = (0x4A / 255, 0x55 / 255, 0x68 / 255)  # #4A5568 = --ink2
    FOOTER_H = 10 * MM          # fixed-footer height: 10mm
    RIGHT_PAD = 6 * MM          # padding: 0 6mm

    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        if i == 0:
            continue  # cover page is masked; skip

        text = str(i + 1)
        rect = page.rect

        if font_data:
            # Register Space Mono Bold and measure text width for right-alignment
            font = fitz.Font(fontbuffer=font_data)
            text_w = font.text_length(text, fontsize=FONTSIZE)
            # Baseline: footer is vertically centred → centre at page_height - FOOTER_H/2
            # Cap-height for Space Mono 700 ≈ 0.68 * fontsize; baseline ≈ centre + cap/2
            baseline_y = rect.height - FOOTER_H / 2 + FONTSIZE * 0.68 / 2
            x = rect.width - RIGHT_PAD - text_w
            page.insert_text(
                (x, baseline_y), text,
                fontsize=FONTSIZE,
                color=COLOR,
                fontfile=str(_FONT_PATH),
                fontname="SpaceMonoBold",
                render_mode=0,
            )
        else:
            # Fallback: no TTF available — use built-in Courier (closest monospace)
            baseline_y = rect.height - FOOTER_H / 2 + FONTSIZE * 0.68 / 2
            x = rect.width - RIGHT_PAD - FONTSIZE * 0.6  # rough monospace width
            page.insert_text(
                (x, baseline_y), text,
                fontsize=FONTSIZE,
                color=COLOR,
                render_mode=0,
            )

    tmp_out = pdf_path + ".tmp_pg.pdf"
    doc.save(tmp_out, garbage=4, deflate=True)
    doc.close()
    os.replace(tmp_out, pdf_path)


# ─── CLI ──────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# EXPORT: CSV
# ─────────────────────────────────────────────────────────────────────────────

def export_csv(data: dict, out_path: str) -> None:
    """Export findings to a flat CSV consumable by Excel, Jira, or any SIEM."""
    import csv

    SPRINT_MAP = {
        "CRITICAL": "Sprint 1 — Immediate (≤ 2 weeks)",
        "HIGH":     "Sprint 1 — Immediate (≤ 2 weeks)",
        "MEDIUM":   "Sprint 2 — Short-term (≤ 6 weeks)",
        "LOW":      "Sprint 3 — Medium-term (≤ 3 months)",
        "INFO":     "Informational — no sprint required",
    }

    fieldnames = [
        "ID", "Severity", "CVSS Score", "CVSS Vector", "Title",
        "Location", "CWE / OWASP", "Sprint", "Description", "Impact",
        "Evidence", "Remediation",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for f in data.get("findings", []):
            sev = f.get("severity", "MEDIUM").upper()
            writer.writerow({
                "ID":            f.get("id", ""),
                "Severity":      sev.title(),
                "CVSS Score":    f.get("cvss", ""),
                "CVSS Vector":   f.get("cvss_vector", ""),
                "Title":         f.get("title", ""),
                "Location":      f.get("location", ""),
                "CWE / OWASP":   f.get("references", ""),
                "Sprint":        SPRINT_MAP.get(sev, ""),
                "Description":   f.get("description", ""),
                "Impact":        f.get("impact", ""),
                "Evidence":      f.get("evidence", ""),
                "Remediation":   f.get("remediation", ""),
            })

    print(f"CSV exported → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT: OCSF (Open Cybersecurity Schema Framework) v1.2.0
# Class 2002 — Vulnerability Finding
# https://schema.ocsf.io/1.2.0/classes/vulnerability_finding
# ─────────────────────────────────────────────────────────────────────────────

def export_ocsf(data: dict, out_path: str) -> None:
    """
    Export findings as an OCSF v1.2.0 Vulnerability Finding bundle (class_uid 2002).
    Suitable for ingestion into any OCSF-compliant SOC platform (AWS Security Lake,
    Splunk, Chronicle, Elastic Security, Microsoft Sentinel).
    """
    import time as _time

    SEV_ID = {
        "INFO":     1,   # OCSF: Informational
        "LOW":      2,   # OCSF: Low
        "MEDIUM":   3,   # OCSF: Medium
        "HIGH":     4,   # OCSF: High
        "CRITICAL": 5,   # OCSF: Critical
    }

    now_ms = int(_time.time() * 1000)
    project_name = data.get("project_name", "Unknown Project")
    report_date  = data.get("report_date", "")
    assessor     = "vuln-assess / Claude Code"

    events = []
    for f in data.get("findings", []):
        sev   = f.get("severity", "MEDIUM").upper()
        refs  = f.get("references", "")

        # Parse CWE and OWASP from references string (e.g. "CWE-79 · OWASP A03:2021")
        cwe_id, cwe_url, owasp_ref = "", "", ""
        for part in refs.split("·"):
            part = part.strip()
            if part.startswith("CWE-"):
                cwe_num = part.replace("CWE-", "").strip()
                cwe_id  = part
                cwe_url = f"https://cwe.mitre.org/data/definitions/{cwe_num}.html"
            elif part.startswith("OWASP"):
                owasp_ref = part

        # Build CVSS object if vector is present
        cvss_objs = []
        if f.get("cvss_vector"):
            cvss_objs.append({
                "base_score":  float(f.get("cvss", 0)),
                "vector_string": f.get("cvss_vector", ""),
                "version":     "3.1",
            })

        event = {
            # ── OCSF envelope ──────────────────────────────────────────────
            "class_uid":     2002,
            "class_name":    "Vulnerability Finding",
            "category_uid":  2,
            "category_name": "Findings",
            "activity_id":   1,
            "activity_name": "Create",
            "time":          now_ms,
            "severity_id":   SEV_ID.get(sev, 0),
            "severity":      sev.title(),
            "status_id":     1,
            "status":        "New",

            # ── Finding info ───────────────────────────────────────────────
            "finding_info": {
                "uid":          f.get("id", ""),
                "title":        f.get("title", ""),
                "types":        ["Vulnerability"],
                "created_time": now_ms,
                "product_uid":  project_name,
                "assessor":     assessor,
                "report_date":  report_date,
            },

            # ── Vulnerability detail ───────────────────────────────────────
            "vulnerabilities": [{
                "title":       f.get("title", ""),
                "desc":        f.get("description", ""),
                "severity":    sev.title(),
                "cvss":        cvss_objs,
                **({"cwe": {"uid": cwe_id, "url": cwe_url, "caption": cwe_id}} if cwe_id else {}),
                "references":  [r.strip() for r in refs.split("·") if r.strip()],
                **({"owasp": owasp_ref} if owasp_ref else {}),
            }],

            # ── Affected resource ──────────────────────────────────────────
            "resources": [{
                "name":  f.get("location", "").split(":")[0],
                "uid":   f.get("location", ""),
                "type":  "Source Code File",
            }],

            # ── Remediation ────────────────────────────────────────────────
            "remediation": {
                "desc": f.get("remediation", ""),
            },

            # ── Evidence (extended data, non-normative) ────────────────────
            "unmapped": {
                "evidence":  f.get("evidence", ""),
                "impact":    f.get("impact", ""),
            },

            # ── Metadata ───────────────────────────────────────────────────
            "metadata": {
                "version": "1.2.0",
                "product": {
                    "name":        "vuln-assess",
                    "vendor_name": "Claude Code / Anthropic",
                    "version":     "1.0",
                },
                "log_name":     "Vulnerability Assessment",
                "log_provider": "vuln-assess",
            },
        }
        events.append(event)

    bundle = {
        "schema_version": "1.2.0",
        "class_uid":      2002,
        "class_name":     "Vulnerability Finding",
        "project":        project_name,
        "target_path":    data.get("target_path", ""),
        "branch":         data.get("branch", ""),
        "report_date":    report_date,
        "total_findings": len(events),
        "severity_counts": {
            sev: sum(1 for f in data.get("findings", [])
                     if f.get("severity", "").upper() == sev)
            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        },
        "events": events,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, ensure_ascii=False)

    print(f"OCSF v1.2.0 JSON exported → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Generate a vulnerability assessment PDF report.")
    parser.add_argument("--findings", required=True, help="Path to _vuln_findings.json")
    parser.add_argument("--output",   required=True, help="Output PDF path")
    parser.add_argument("--watermark", default="", help="Optional watermark text (e.g. DRAFT)")
    parser.add_argument(
        "--csv",
        default="",
        metavar="PATH",
        help="Also export findings as CSV (e.g. Report.csv). Consumable by Excel, Jira, SIEM.",
    )
    parser.add_argument(
        "--ocsf",
        default="",
        metavar="PATH",
        help="Also export findings as OCSF v1.2.0 JSON (class 2002 — Vulnerability Finding). "
             "Consumable by AWS Security Lake, Splunk, Chronicle, Elastic Security, Sentinel.",
    )
    args = parser.parse_args()

    findings_path = Path(args.findings).resolve()
    if not findings_path.exists():
        print(f"ERROR: findings file not found: {findings_path}", file=sys.stderr)
        sys.exit(1)

    with open(findings_path, encoding="utf-8") as fh:
        data = json.load(fh)

    html_content = generate_html(data, watermark=args.watermark)

    # Write to a temp HTML file
    with tempfile.NamedTemporaryFile(
        suffix=".html", prefix="vuln_report_", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    try:
        pdf_path = str(Path(args.output).resolve())
        print("Rendering HTML → PDF via Chrome headless...")
        render_pdf(tmp_path, pdf_path)
        findings_count = len(data.get("findings", []))
        print(f"Report generated → {pdf_path}")
        print(f"{findings_count} finding{'s' if findings_count != 1 else ''} total")
    finally:
        os.unlink(tmp_path)

    # Optional exports
    if args.csv:
        export_csv(data, str(Path(args.csv).resolve()))
    if args.ocsf:
        export_ocsf(data, str(Path(args.ocsf).resolve()))


if __name__ == "__main__":
    main()
