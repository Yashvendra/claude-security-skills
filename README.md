# claude-skills-security

> AI-powered security audit skills for [Claude Code](https://claude.ai/claude-code) — from raw codebase to professional PDF report in one command.

```
"Run a security audit on this codebase"
```

That's all it takes. Claude Code runs a full 7-phase pipeline: discovers the architecture, performs ultra-granular function analysis, hunts 22 vulnerability categories, enriches findings with CVE/CWE research, and delivers a pentest-quality PDF report — plus an optional developer remediation guide.

---

## Skills

| Skill | Trigger | Output |
|---|---|---|
| **vuln-assessment** | *"security audit"*, *"find vulnerabilities"*, *"pentest this"* | PDF security report + optional developer guide |

---

## What Gets Produced

### Vulnerability Report PDF
Dark navy professional layout. Every finding has:
- CVSS 3.1 score + vector string
- Exact code evidence (line references)
- Concrete remediation with correct code pattern
- CWE + OWASP Top 10 mapping + CVE references

**Report sections** (industry-standard structure):
1. Cover + Executive Summary
2. Scope, Methodology & Architecture
3. Risk Dashboard (severity distribution + OWASP category bars)
4. Threat Model & Attack Surface
5. Detailed Findings (severity-grouped cards)
6. Attack Chain Analysis (multi-step exploit paths)
7. Compliance Mapping (OWASP / CWE / ISO 27001 / NIST CSF / PCI DSS)
8. Security Strengths (what not to change)

**Machine-readable exports** (optional):
- **CSV** — importable into Excel, Jira, or any SIEM
- **OCSF v1.2.0 JSON** — native ingestion for AWS Security Lake, Splunk, Chronicle, Elastic Security, Microsoft Sentinel

### Developer Remediation Guide PDF (optional)
Engineer-facing document — not analyst speak. Contains:
- Root-cause pattern analysis (why so many findings share the same anti-pattern)
- Highest-severity attack paths with PoC one-liners
- File-by-file before/after code fixes with explanations
- 3-sprint remediation roadmap with hour estimates
- Concrete test commands to verify each fix

---

## The Pipeline

```
Phase 1 ── Project Discovery
           Auto-detect language, framework, entry points, data stores, scope

Phase 2 ── Architectural Context Building          [audit-context-building]
           Module map · data flows · trust boundaries · auth gates · invariants

Phase 3 ── Ultra-Granular Function Analysis        [function-analyzer agent]
           Top 20 highest-risk functions: block-by-block, 5-Whys, 5-Hows

Phase 4 ── Vulnerability Hunting
           22-category checklist: OWASP Top 10 · API Security · CWE Top 25 ·
           JWT/OAuth · Cloud (AWS/GCP/Azure) · Supply Chain · CI/CD · IaC ·
           Container Security · Attack Chain second pass

Phase 5 ── CVE & Reference Research Enrichment    [research-lookup, optional]
           CWE numbers · OWASP categories · notable CVEs · NIST SP 800-53

Phase 6 ── PDF Report Generation
           generate_report_html.py → Chrome headless → professional A4 PDF

Phase 7 ── Developer Remediation Guide             [scientific-writing, optional]
           Markdown guide → generate_guide_html.py → styled A4 PDF
```

---

## Installation

### Requirements
- [Claude Code](https://claude.ai/claude-code) (CLI)
- Python 3.8+
- Google Chrome or Chromium (for PDF rendering — no other pip deps)

### One-liner

```bash
git clone https://github.com/<your-username>/claude-skills-security.git
cd claude-skills-security && ./install.sh
```

The installer will:
1. Copy `vuln-assessment` skill → `~/.claude/skills/`
2. Install the bundled `audit-context-building` dependency
3. Optionally install `claude-scientific-writer` (for Phase 5 + Phase 7)

Restart Claude Code after installation.

---

## Usage

Open any codebase in Claude Code and say any of:

```
"Run a security audit on this codebase"
"Check this code for vulnerabilities"
"Generate a vulnerability assessment report"
"Find security issues in src/"
"Pentest this before we ship"
"OWASP audit"
```

Claude will ask 2 quick questions (branch + whether you want the developer guide), then run the full pipeline autonomously.

### Multi-branch audits
```
"Audit the main and develop branches side by side"
```
Produces one PDF per branch, with findings diffed so you can see what new vulnerabilities were introduced.

### Scoped audits
```
"Check only the authentication module for security issues"
"Find all SQL injection vulnerabilities"
```

---

## Dependencies

| Dependency | Bundled | Purpose |
|---|---|---|
| `audit-context-building` | ✅ Bundled in `deps/` | Phase 2 architecture analysis + Phase 3 function analysis |
| `claude-scientific-writer` | ➡ Installed via `./install.sh` | Phase 5 CVE research + Phase 7 dev guide (optional) |
| Chrome / Chromium | System | PDF rendering (Phases 6 + 7) |
| Python 3.8+ | System | Report generation scripts |

Both optional dependencies have graceful fallbacks — the core vulnerability report is produced with or without them.

### Why `audit-context-building` is bundled
It's a small plugin (5 markdown files) from [Trail of Bits](https://github.com/trailofbits). Bundling it means `./install.sh` is genuinely self-contained. The original source lives at [trailofbits/audit-context-building](https://github.com/trailofbits).

### Why `claude-scientific-writer` is not bundled
It's a large plugin (30+ sub-skills, ~30MB). The install script fetches it via the Claude Code plugin registry with a single command.

---

## Project Structure

```
claude-skills-security/
├── vuln-assessment/
│   ├── SKILL.md                    ← skill definition (loaded by Claude Code)
│   ├── scripts/
│   │   ├── generate_report_html.py ← HTML→PDF report generator (no pip deps)
│   │   └── generate_guide_html.py  ← HTML→PDF dev guide generator
│   ├── references/
│   │   ├── vuln_checklist.md       ← 22-category vulnerability checklist
│   │   └── cvss_guide.md           ← CVSS 3.1 quick reference
│   ├── assets/                     ← fonts, manifest
│   └── evals/                      ← evaluation fixtures (vulnapp)
├── deps/
│   └── audit-context-building/     ← bundled Trail of Bits plugin
├── install.sh                      ← one-command setup
└── README.md
```

---

## Evals

The `vuln-assessment/evals/` directory contains a deliberately vulnerable Flask application (`vulnapp`) with 24 known findings across 5 critical, 13 high, 5 medium, and 1 low severity. Use it to validate the skill's detection rate:

```bash
# Run eval against the fixture codebase
cd vuln-assessment/evals/fixtures/vulnapp
# Then in Claude Code: "Run a security audit on this codebase"
```

Expected output: `vulnapp_Vulnerability_Report.pdf` + `_vuln_findings.json` with ≥20/24 findings.

---

## Output Examples

The `evals/fixtures/vulnapp/` directory contains real output from the skill:
- `vulnapp_Vulnerability_Report.pdf` — the full security report
- `vulnapp_Developer_Remediation_Guide.pdf` — the developer guide
- `_vuln_findings.json` — all 24 findings in structured JSON

---

## License

MIT
