<div align="center">

# claude-skills-security

**Deep, architecture-aware vulnerability discovery skills for [Claude Code](https://claude.ai/claude-code) — finds what static scanners miss.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776ab.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-7c3aed)](https://claude.com/product/claude-code)
[![OWASP](https://img.shields.io/badge/OWASP-Top%2010-e04e39)](https://owasp.org/Top10/2025/)

</div>

---

Open any codebase in Claude Code and say:

```
"Run a security audit on this codebase"
```

Unlike linters and static analyzers that match known patterns, this skill reasons about your codebase the way a human auditor would — building a full architectural model, tracing data flows across trust boundaries, and performing ultra-granular function-level analysis to uncover logic flaws, auth bypasses, and novel attack chains that automated tools routinely miss. No configuration. No setup beyond `./install.sh`.

---

## Pipeline

```
                         📁 Your Codebase
                               │
          ┌────────────────────┼────────────────────┐
          │         7-Phase Audit Pipeline           │
          │                                          │
          │  1 ─ Project Discovery                   │
          │      Language · Framework · Entry Points │
          │               │                          │
          │  2 ─ Architecture Context                │
          │      Module Map · Trust Boundaries       │
          │               │                          │
          │  3 ─ Function Analysis                   │
          │      Top 20 Risky Functions · 5-Whys     │
          │               │                          │
          │  4 ─ Vulnerability Hunting               │
          │      22 Categories · OWASP · CWE · Cloud │
          │               │                          │
          │  5 ─ CVE Enrichment          (optional)  │
          │      CWE · CVEs · NIST SP 800-53         │
          │               │                          │
          │  6 ─ PDF Report Generation               │
          │      Chrome Headless · Dark Navy A4      │
          │               │                          │
          │  7 ─ Developer Guide         (optional)  │
          │      Before/After Fixes · Sprint Roadmap │
          └───────────────┬──────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
📄 Vulnerability     📘 Developer     📊 Machine-Readable
   Report PDF      Remediation Guide   CSV · OCSF JSON
```

---

## Output

### Vulnerability Report PDF

Dark navy professional layout — not a linter dump. Every finding is structured as:

| Field | Content |
|---|---|
| **Severity** | CVSS 3.1 score + vector string |
| **Evidence** | Exact `file:line` reference with code excerpt |
| **Remediation** | Concrete fix with the correct code pattern |
| **Standards** | CWE · OWASP Top 10 · CVE references |

The report follows an industry-standard 8-section structure: Cover & Executive Summary → Scope & Methodology → Risk Dashboard → Threat Model → Detailed Findings → Attack Chain Analysis → Compliance Mapping (OWASP / ISO 27001 / NIST CSF / PCI DSS) → Security Strengths.

### Machine-Readable Exports _(optional)_

Structured output for integration with SIEMs, ticketing systems, and CI/CD pipelines:

- **CSV** — one row per finding with severity, CWE, file, line, and remediation summary; ready for spreadsheet triage or Jira bulk import
- **OCSF JSON** — findings mapped to the [Open Cybersecurity Schema Framework](https://schema.ocsf.io/) `Vulnerability Finding` class (class UID 2004), compatible with AWS Security Hub, Splunk, and any OCSF-aware SIEM

### Developer Remediation Guide _(optional)_

Engineer-facing. No analyst jargon — just the information a developer needs to fix things.

- Root-cause pattern analysis across all findings (why the same anti-pattern keeps appearing)
- Highest-severity attack paths with PoC one-liners
- File-by-file before/after code fixes with explanations
- 3-sprint remediation roadmap with hour estimates per finding

---

## Installation

**Requirements:** [Claude Code](https://claude.ai/claude-code) · Python 3.8+ · Google Chrome or Chromium

### Via Claude Code plugin registry _(recommended)_

```bash
claude plugin install Yashvendra/claude-security-skills
```

Installs `vuln-assessment` and the bundled `audit-context-building` dependency in one step. For CVE enrichment and the developer guide (Phases 5 + 7), also install:

```bash
claude plugin install claude-scientific-writer
```

Restart Claude Code when done.

### Via install script _(alternative)_

```bash
git clone https://github.com/Yashvendra/claude-security-skills.git
cd claude-skills-security && ./install.sh
```

`install.sh` copies the skill and its bundled dependencies into `~/.claude/skills/`, then optionally installs `claude-scientific-writer` for CVE research enrichment and the developer guide. Restart Claude Code afterward.

---

## Usage

### Standard audit

```
"Run a security audit on this codebase"
"Find vulnerabilities in src/"
"OWASP audit"
"Pentest this before we ship"
```

Claude asks two questions — which branch to audit and whether you want the developer guide — then runs the full pipeline autonomously.

### Scoped audit

```
"Check only the authentication module for security issues"
"Find all SQL injection vulnerabilities"
```

### Multi-branch comparison

```
"Audit main and develop side by side"
```

Produces one PDF per branch with findings diffed to surface vulnerabilities introduced between branches.

---

## Dependencies

| Dependency | Distribution | Phases |
|---|---|---|
| `audit-context-building` | Bundled in `deps/` | 2–3: architecture + function analysis |
| `claude-scientific-writer` | Installed by `./install.sh` | 5 + 7: CVE research + dev guide |
| Chrome / Chromium | System | 6–7: PDF rendering |
| Python 3.8+ | System | 6–7: report generation |

Both optional dependencies degrade gracefully — skip them and the core vulnerability report is still produced in full.

---

## Evals

`vuln-assessment/evals/fixtures/vulnapp` is a deliberately vulnerable Flask application with **24 known findings** (5 Critical · 13 High · 5 Medium · 1 Low). Use it to validate detection rate:

```bash
cd vuln-assessment/evals/fixtures/vulnapp
# In Claude Code: "Run a security audit on this codebase"
```

Passing bar: `vulnapp_Vulnerability_Report.pdf` + `_vuln_findings.json` with ≥ 20/24 findings detected. Optional: `_vuln_findings.csv` and `_vuln_findings_ocsf.json` for machine-readable output validation.

---

## Contributing

Contributions are welcome — bug fixes, new vulnerability categories, additional export formats, or eval fixtures.

1. Fork the repo and create a feature branch
2. Make your changes and run the evals against `vulnapp` to verify detection rate is not regressed (≥ 20/24)
3. Open a pull request with a clear description of what changed and why

For larger changes (new pipeline phases, architectural refactors), open an issue first to align on approach before investing time in implementation.

---

## Reporting Issues

Found a bug, a missed vulnerability class, or a false positive pattern? Please open an issue on GitHub:

**[github.com/Yashvendra/claude-security-skills/issues](https://github.com/Yashvendra/claude-security-skills/issues)**

Include:
- A description of the problem and what you expected
- The language / framework of the audited codebase (no source code needed)
- The phase where it failed (e.g., PDF generation, CVE enrichment)
- Relevant output or error messages

For security vulnerabilities in this skill itself, please disclose privately via GitHub's [private vulnerability reporting](https://github.com/Yashvendra/claude-security-skills/security/advisories/new) rather than opening a public issue.

---

## License

MIT
