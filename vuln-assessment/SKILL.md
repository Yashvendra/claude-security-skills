---
name: vuln-assessment
description: >
  End-to-end vulnerability assessment pipeline that produces a professional PDF security
  report for any codebase. Use this skill whenever the user wants a security audit,
  vulnerability assessment, security report, wants to find vulnerabilities, needs a
  pentest-style code review, or asks for threat modeling. Trigger on phrases like:
  "security audit", "vulnerability assessment", "vuln report", "find vulnerabilities",
  "security scan", "audit this codebase", "security review", "what are the security
  issues", "run a security analysis", "check for vulnerabilities", "pentest prep",
  "threat model this", "OWASP audit", "CWE scan". Even if the user just says "check
  this code for issues" or "is this code secure?" — use this skill. It orchestrates
  deep architectural context building, ultra-granular function analysis, systematic
  OWASP/CWE/cloud vulnerability hunting, CVE research enrichment, and professional
  PDF report generation in one end-to-end pipeline.
---

# Vulnerability Assessment Report Skill

## What This Produces

A professional PDF vulnerability assessment report (dark navy theme, severity-coded
finding cards, CVSS scores, code evidence, remediation guidance, prioritized roadmap)
— the same quality as a manual pentest report, generated from a 6-phase pipeline.

**Output**: `<ProjectName>_Vulnerability_Report.pdf` saved in the target directory.

---

## Step 0 — Gather Inputs (ask the user)

Before starting, collect the minimum required information:

### 1. Target path
If not already specified, ask:
> "Which directory should I audit? (default: current working directory)"

### 2. Git branch selection (if it's a git repo)
Check if the target is a git repository:
```bash
git -C <target_path> rev-parse --is-inside-work-tree 2>/dev/null
```

If yes, list available branches and ask:
```bash
git -C <target_path> branch -a --format='%(refname:short)'
```

Then ask the user:
> "This is a git repository. Which branch(es) would you like to audit?
>
> Available branches:
> - `main` (current)
> - `develop`
> - `feature/auth-refactor`
> - ...
>
> Options:
> - **Single branch**: Enter a branch name (or press Enter to use current)
> - **Multiple branches**: Comma-separate names to get one report per branch
> - **Comparison**: Two branches to highlight new vulnerabilities introduced

If the user picks multiple branches or comparison mode, run the full 6-phase pipeline
independently for each branch (using git worktrees — see Branch Checkout below)
and generate a separate PDF per branch. Name them:
`<ProjectName>_<BranchName>_Vulnerability_Report.pdf`

### 3. Additional export formats (optional)
After asking about the watermark, ask:
> "Beyond the PDF, would you also like any of these machine-readable exports?
>
> - **CSV** — flat spreadsheet with all findings; import directly into Excel, Jira, or any SIEM
> - **OCSF JSON** — Open Cybersecurity Schema Framework v1.2.0 (class 2002 — Vulnerability Finding);
>   native ingestion format for AWS Security Lake, Splunk, Chronicle, Elastic Security, and Microsoft Sentinel
>
> Reply with one or more: `CSV`, `OCSF`, `both`, or press Enter to skip."

Save the user's answer and pass the appropriate flags to the report generator in Phase 6.
If the user selects OCSF, note that it produces a standards-compliant bundle containing one
event per finding, including CVSS vectors, CWE references, affected resource identifiers,
remediation guidance, and full OCSF envelope metadata — ready for SOC ingestion with no
post-processing required.

### 4. Developer Remediation Guide (optional)
Ask after question 5:
> "Would you also like a **Developer Remediation Guide** PDF alongside the security report?
>
> This is an engineer-facing document with root-cause pattern analysis, before/after
> code fixes, sprint roadmap, and file-by-file remediation instructions — written for
> developers, not security analysts.
>
> Reply `yes` or press Enter to skip."

Save the answer. If `yes`, Phase 7 will run after the PDF report is complete.

---

## Branch Checkout (for non-current branches)

To analyze a branch without disturbing the working tree, use git worktree:
```bash
git -C <target_path> worktree add /tmp/vuln-assess-<branch> <branch>
```
Analyze from `/tmp/vuln-assess-<branch>` instead of the original path.
After analysis is complete, clean up:
```bash
git -C <target_path> worktree remove /tmp/vuln-assess-<branch> --force
```

If worktree creation fails (e.g. branch has an unclean name), fall back to:
```bash
git -C <target_path> stash
git -C <target_path> checkout <branch>
# ... analyze ...
git -C <target_path> checkout -
git -C <target_path> stash pop
```

---

## Announce the plan

Before starting the pipeline, tell the user:
> "Starting vulnerability assessment for `<path>` on branch `<branch>`.
>
> **Phase 1** — Project Discovery
> **Phase 2** — Architectural Context Building
> **Phase 3** — Ultra-Granular Function Analysis
> **Phase 4** — Vulnerability Hunting (checklist sections A–V)
> **Phase 5** — CVE & Reference Research Enrichment
> **Phase 6** — PDF Report Generation
> _(if requested)_ **Phase 7** — Developer Remediation Guide PDF
>
> I'll update you after each phase completes."

---

## Phase 1 — Project Discovery

Auto-detect project shape before any deep analysis:

1. List directory structure (top 2 levels), count source lines per major module.
2. Detect: primary language(s), framework(s), entry points, config/dependency files.
3. Identify: public API surfaces, authentication boundaries, data stores, external services.
4. Auto-detect project name from: directory basename, `pyproject.toml`/`package.json`
   name field, or `git remote get-url origin` (use repo name, strip `.git`).
5. Determine scope: which modules get deep analysis. Exclude `tests/`, `migrations/`,
   `vendor/`, `node_modules/`, `dist/`, `.git/` unless they contain security-relevant code.

**Produce a scope summary before Phase 2:**
```
Project:     MyService
Language:    Python 3.12 / FastAPI
Branch:      main
Entry Points: src/main.py, src/worker.py
Data Stores: PostgreSQL, Redis, S3
External:    SQS, Stripe API, Auth0
Scope:       src/ (~4,200 lines)  ·  Excluding: tests/, migrations/
```

If the codebase is very large (>15k lines in scope), ask the user whether to do a
full audit or focus on specific high-risk modules.

### Scope Narrowing (user-specified focus)

If the user specifies a narrower scope — a particular file, module, or vulnerability class — honour it:

- **File/module scope**: Restrict Phase 1 discovery and Phase 3 function analysis to the named
  paths. In Phase 4, still work through all checklist categories, but only flag findings whose
  evidence lives in the named paths. State the restriction clearly in the scope summary:
  `Scope: src/auth/ only — user-specified`

- **Vulnerability class scope** (e.g. "check for XSS only", "focus on auth issues"):
  In Phase 4, explicitly work only the relevant checklist sections (e.g. for XSS → sections L, V).
  Skip other sections but note the restriction: `Checklist: sections L, V only (user-specified)`.
  Phase 3 function analysis should still be done — it almost always surfaces the relevant class
  more precisely than grep alone.

- **Combined scope**: Apply both restrictions together.

In all narrowed cases, note the restriction in the PDF's scope table and executive summary
so the reader understands this is a partial, not exhaustive, audit.

---

## Phase 2 — Architectural Context Building

> ⚠️ **Tool selection — common mistake:** `audit-context-building:audit-context` is a **Skill**,
> NOT an Agent. Invoking it via the Agent tool will fail with "Agent type not found".
> Use **only** the Skill tool: `skill: "audit-context-building:audit-context"`.
> (Note: `audit-context-building:function-analyzer` in Phase 3 IS an Agent — different tool.)

Use the **Skill tool** to invoke `audit-context-building:audit-context`.
Its job is **pure understanding** — no bug-hunting yet. Let it do a full pass.

If the skill is unavailable (not installed), perform this analysis inline by reading the
key source files identified in Phase 1 and building the context yourself.

What to extract and retain from Phase 2 (you will use this in Phases 3–4):

- **Module map**: what each file does and how they connect
- **Data flow**: untrusted input → where it flows → what it touches
- **Trust boundaries**: exactly where is input first validated vs. directly trusted
- **State variables**: mutable shared state, caches, connection pools — and who mutates them
- **Auth/authz gates**: where authentication is enforced, where it can be bypassed
- **External interactions**: every DB query, HTTP call, file read, subprocess, env var read
- **Invariants**: what must always be true for the system to be correct

Save this as `_audit_context.md` in the target directory and note the path.

**Why this phase matters**: Skipping to hunting without understanding the system
produces a shallow list of grep-matches. Understanding the architecture first means
you find the real issues — the ones that live at interaction boundaries and in
assumptions that span multiple functions.

---

## Phase 3 — Ultra-Granular Function Analysis

With the architectural map from Phase 2, identify the **20 highest-risk functions**:

**Priority criteria** (rank by how many of these apply):
- Directly consumes untrusted external input (HTTP handlers, queue consumers, file parsers)
- Constructs database queries or shell commands
- Enforces authentication or authorization
- Performs cryptographic operations
- Reads/writes files using user-controlled paths
- Manages sessions, tokens, or credentials
- Crosses a trust boundary (public → internal, user → admin, tenant A → tenant B)
- Has high cyclomatic complexity or deeply nested conditionals

For each priority function, use the **Agent tool** with
`subagent_type: "audit-context-building:function-analyzer"` if that agent type is available.
If unavailable, perform the analysis inline using the same framework:

- **Block-by-block**: what each block does, what it assumes, what invariant it maintains
- **First Principles**: what fundamental security property must hold here?
- **5 Whys on failure**: why could this break? → why would that happen? → (5 levels)
- **5 Hows on exploit**: how would an attacker reach this? → how would they craft input?
- **Data flow trace**: follow attacker-controlled data from entry to every sink

Document per-function findings in a scratch list — these become evidence for Phase 4.

---

## Phase 4 — Vulnerability Hunting

Read `references/vuln_checklist.md`. Work through **all 22 sections** systematically.
The checklist covers:
- **A–E**: Core injection, auth, authorization, crypto, misconfiguration
- **F–G**: Vulnerable components, data exposure & logging
- **H–I**: Architecture issues, cloud-specific (AWS/GCP/Azure)
- **J–K**: Supply chain, business logic
- **L**: XSS (Reflected/Stored/DOM), CSRF, CSP, Clickjacking, Open Redirect
- **M**: SSRF, cloud metadata SSRF, webhook abuse
- **N**: Insecure deserialization (pickle/yaml/XXE), unsafe archive/file parsing
- **O**: API security — Mass Assignment, shadow endpoints, rate limiting, upstream API trust
- **P**: Advanced auth — JWT algorithm attacks, OAuth2/OIDC, GraphQL-specific, WebSocket
- **Q**: Security observability — audit logging, alerting, incident response readiness
- **R**: Insecure design — fail-secure, prototype pollution, ReDoS, HTTP smuggling
- **S**: Container & Docker security — Dockerfile hardening, runtime privileges, Kubernetes RBAC
- **T**: CI/CD pipeline security — GitHub Actions injection, secret handling, artifact integrity
- **U**: Infrastructure as Code — Terraform/CloudFormation secrets, IAM permissions, network exposure
- **V**: Frontend framework specifics — React dangerouslySetInnerHTML, Next.js SSR leakage, Vue v-html, Angular bypassSecurityTrust*

For each category, check whether the codebase has that class of issue based on
your Phase 2–3 understanding. Mark categories as `present / not present / N/A` —
every category must be considered, not just the ones with obvious grep matches.

**Before working through checklist sections, initialize the findings file:**

Create `_vuln_findings.json` in the target directory with an empty findings array:
```json
{"findings": []}
```

**For every confirmed finding, immediately write it to `_vuln_findings.json`** (append to
the `findings` array using the Write tool), then show a single compact status line:
```
✓ VUL-001  CRITICAL  SQL Injection in login()  app.py:35  → written
```

Do **not** reproduce the full finding card as conversation text — the JSON is the
canonical record. All detail lives there; Phase 5 and Phase 6 read from it directly.

Each finding must include all fields when written:
```json
{
  "id": "VUL-NNN",
  "severity": "CRITICAL",
  "cvss": "9.8",
  "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
  "title": "Specific, actionable title — not generic",
  "location": "file.py:line_range",
  "description": "What the vulnerability is, why it exists, what makes it exploitable.",
  "impact": "Concrete attacker outcome — not 'could lead to data exposure'",
  "evidence": "Exact code snippet (4–15 lines) from the actual codebase.",
  "remediation": "Specific, actionable fix with correct code pattern as example.",
  "references": ""
}
```
The `references` field is left empty here and populated by Phase 5.

**Severity and title guidance (unchanged — quality must not regress):**
- Title: specific and actionable. Bad: `"SQL Injection"`. Good: `"Pervasive SQL Injection via Untrusted Queue Message Fields"`
- Impact: concrete. Bad: `"Could lead to data exposure"`. Good: `"Full database read/write; cross-tenant data exfiltration possible"`
- CVSS vector: always include the full string — see `references/cvss_guide.md`

**Severity calibration:**
- CRITICAL (9.0–10.0): Direct RCE, full DB exfiltration, auth bypass with no preconditions
- HIGH (7.0–8.9): Significant data exposure, privilege escalation, DoS, hardcoded secrets
- MEDIUM (4.0–6.9): Partial exposure, requires chaining, reliability/config issues
- LOW (0.1–3.9): Defense-in-depth gaps, minor info leakage, best-practice violations
- INFO (0.0): Observations with no direct security impact

**After the first pass, do a chained-attack second pass.** Individual findings are one thing,
but real attacks chain vulnerabilities together. Actively look for these combinations:

- **XSS → CSRF bypass**: A stored XSS in one part of the app can issue authenticated requests
  from the victim's session, bypassing CSRF tokens entirely — does any XSS finding enable this?
- **IDOR → Stored XSS**: If user A can write data into user B's record (IDOR), and that record
  is later rendered in user B's dashboard as HTML, the IDOR becomes a stored XSS delivery path.
- **Open Redirect → OAuth token theft**: An open redirect on the OAuth `redirect_uri` endpoint
  can be used to redirect authorization codes or access tokens to an attacker's server.
- **SSRF → Cloud metadata → credential exfil**: An SSRF that can reach `169.254.169.254` gives
  the attacker IAM role credentials, which then allows reading secrets, S3 buckets, or further
  lateral movement — escalate the SSRF's severity accordingly.
- **Weak session token → brute force → account takeover**: If `random` (not `secrets`) is used
  for session/reset tokens AND there's no rate limiting on the validation endpoint, the weakness
  is exploitable, not just theoretical.
- **Debug endpoint + hardcoded secret**: A debug/config endpoint that exposes environment
  variables combined with a hardcoded fallback secret creates a direct credential disclosure path.

For each chain you find, create a separate finding (or upgrade an existing finding's severity)
that explains the full attack path from initial access to final impact.

---

## Phase 5 — Research Enrichment

**Before invoking any skill, check whether the API keys are configured:**
```bash
bash -c '[ -n "$PARALLEL_API_KEY" ] || [ -n "$OPENROUTER_API_KEY" ] && echo "available" || echo "unavailable"'
```

- If **either key is set** → use the **Skill tool** to invoke `claude-scientific-writer:research-lookup`
  for every CRITICAL and HIGH finding (and optionally MEDIUM).
- If **neither key is set** → skip skill invocation entirely. Use your built-in CWE/OWASP/CVE
  knowledge directly. Do **not** load the skill — it cannot function without a key and loading it
  wastes context budget.

Tasks for each finding (via skill or built-in knowledge):

1. Verify the CWE number and get the official weakness description
2. Find the OWASP Top 10 2021 category that applies
3. Look up notable CVEs for this pattern (especially if a library is involved)
4. Get NIST SP 800-53 control references relevant to the remediation
5. Find language/framework-specific secure-coding guidance

For each enriched finding, **update its `references` field directly in `_vuln_findings.json`**
using the Write tool (read → patch → write). Do not reproduce finding text in conversation.
Show a compact status line per finding:
```
✓ VUL-001  references updated  →  CWE-89 · OWASP A03:2021 · CVE-2023-XXXXX
```
**Never guess CVE numbers** — if uncertain, write `CWE-XXX · OWASP A0X:2021` only.

---

## Phase 6 — PDF Report Generation

### Step 1 — Finalise `_vuln_findings.json` with project metadata

All findings were written to `_vuln_findings.json` incrementally during Phase 4 and
enriched with references during Phase 5. Step 1 adds the top-level metadata fields
by reading the file and prepending the project envelope:

```json
{
  "project_name": "<project name>",
  "target_path": "<absolute path>",
  "branch": "<branch name or 'N/A'>",
  "language": "<primary language and version>",
  "framework": "<framework or 'None'>",
  "assessment_type": "Static Code Review + Architecture Audit",
  "report_date": "<YYYY-MM-DD>",
  "scope_rows": [
    ["Module", "Path", "Lines (approx)"],
    ["<module name>", "<path>", "<line count>"]
  ],
  "data_flow_summary": "<2–3 sentence description of the main data flow>",
  "external_deps": [
    ["Store", "Library", "Usage", "Auth Method"],
    ["PostgreSQL", "psycopg2", "Primary data store", "Env credentials"]
  ],
  "findings": [ ... ]
}
```

Read the existing `findings` array from the file, wrap it with the metadata envelope
above, and write the complete structure back. Do not overwrite or re-derive findings
— use exactly what was written during Phase 4/5.

Note: `branch` is a top-level field — the generator will show it in the cover
page meta block if present.

### Step 1b — Populate new structured sections (from Phase 2–4 findings)

After writing findings, also populate these fields in `_vuln_findings.json`:

**`methodology`** — From Phase 4 checklist pass:
```json
"methodology": {
  "framework": "OWASP WSTG v4.2 · CWE Top 25 · NIST SP 800-115",
  "type": "White-Box Static Analysis + Architecture Review",
  "coverage": [
    {"category": "A01:2021 — Broken Access Control", "status": "tested", "findings": 2},
    {"category": "A02:2021 — Cryptographic Failures",  "status": "tested", "findings": 0},
    {"category": "A03:2021 — Injection",               "status": "tested", "findings": 1}
  ]
}
```
Status values: `"tested"` | `"partial"` | `"na"`. Count actual findings per category.

**`threat_model`** — From Phase 2 architecture context:
```json
"threat_model": {
  "assets": [
    ["Asset", "Classification", "Risk if Compromised"],
    ["User credentials", "Critical", "Account takeover"]
  ],
  "threat_actors": [
    ["Actor", "Motivation", "Capability", "Attack Vector"],
    ["External attacker", "Data theft", "High", "Public API"]
  ],
  "attack_surface": [
    ["Entry Point", "Method", "Auth Required", "Related Findings"],
    ["POST /login", "HTTP API", "None", "VUL-013"]
  ],
  "trust_boundaries": [
    "Browser → API Server (HTTPS + cookie)",
    "API Server → Database (internal network)"
  ]
}
```

**`attack_chains`** — From Phase 4 chained-attack second pass:
```json
"attack_chains": [
  {
    "id": "CHAIN-001",
    "title": "XSS → Session Theft → Privilege Escalation",
    "severity": "CRITICAL",
    "prerequisites": "Attacker can inject a WebSocket notification",
    "impact": "Full admin account takeover",
    "steps": [
      {"step": 1, "finding_id": "VUL-003", "action": "Inject XSS via notification", "outcome": "Script executes in victim browser"},
      {"step": 2, "finding_id": "VUL-007", "action": "Steal session from localStorage", "outcome": "Valid session obtained"},
      {"step": 3, "finding_id": "VUL-004", "action": "Forge User Policy object", "outcome": "Admin privileges gained"}
    ]
  }
]
```

**`security_strengths`** — From Phase 2 positive observations:
```json
"security_strengths": [
  {
    "title": "HTTP-Only Cookie Session Management",
    "description": "Sessions use HTTP-only cookies with withCredentials: true, preventing JS-based token theft."
  }
]
```

These fields are optional — if absent, the corresponding sections show a placeholder note.

### Step 2 — Generate the HTML report and render to PDF

Find the `generate_report_html.py` script:
```bash
find ~/.claude/skills -name "generate_report_html.py" 2>/dev/null | head -1
```

Run it (replace `<skill_scripts_dir>` with the path from above):
```bash
python <skill_scripts_dir>/generate_report_html.py \
  --findings _vuln_findings.json \
  --output "<ProjectName>_Vulnerability_Report.pdf" \
  [--csv "<ProjectName>_Vulnerability_Report.csv"] \
  [--ocsf "<ProjectName>_Vulnerability_Report.ocsf.json"]
```

- Include `--csv` only if the user requested CSV export in Step 0.
- Include `--ocsf` only if the user requested OCSF export in Step 0.

The `--csv` flag produces a flat CSV (ID, Severity, CVSS, Title, Location, Sprint, Description,
Impact, Evidence, Remediation) importable into Excel, Jira, or any SIEM.

The `--ocsf` flag produces an OCSF v1.2.0 Vulnerability Finding bundle (class_uid 2002) with one
event per finding, including full CVSS vectors, CWE references, OWASP mappings, affected resource
identifiers, and remediation guidance — ready for native ingestion into AWS Security Lake, Splunk,
Chronicle, Elastic Security, or Microsoft Sentinel with no post-processing required.

The script generates a styled HTML report and renders it to PDF using Chrome headless.
**No external Python dependencies required** — only Google Chrome or Chromium must be installed.

If Chrome is not found, the script will print the HTML path so you can open it manually
in Chrome and use Ctrl+P → Save as PDF.

**Design**: Space Grotesk / Space Mono / Syne fonts · dark navy cover grid · severity-coded
finding cards (CRITICAL=red, HIGH=orange, MEDIUM=amber, LOW=green) · fixed header/footer
on every page · sprint kanban roadmap · full A4 layout with 18mm breathing room below header.

### Step 3 — Confirm output and persist context

Tell the user:
> "Report generated → `<ProjectName>_Vulnerability_Report.pdf`
> **N findings**: X critical · Y high · Z medium · W low
>
> _(if CSV was requested)_ CSV export → `<ProjectName>_Vulnerability_Report.csv`
> _(if OCSF was requested)_ OCSF v1.2.0 JSON → `<ProjectName>_Vulnerability_Report.ocsf.json`
>   → Ingest directly into AWS Security Lake, Splunk, Chronicle, Elastic Security, or Microsoft Sentinel."

Then save a concise audit context to memory (`memory/MEMORY.md` or a dedicated
`memory/audit_<ProjectName>.md`). Use this exact format so future sessions can
instantly pick up the context:

```markdown
## Security Audit (<date>, branch: <branch>)
Report: <absolute path to PDF>
Findings JSON: <absolute path to _vuln_findings.json>

### Architecture Summary
- Stack: <language/framework>
- Auth: <auth mechanism summary>
- Data stores: <DB/cache/storage>
- Key invariants: <1–3 critical architectural facts to know>

### Findings Summary (<N> total: X CRITICAL · Y HIGH · Z MEDIUM · W LOW · V INFO)
| ID | Sev | Title | Location |
|----|-----|-------|----------|
| VUL-001 | HIGH | ... | file.py:42 |
...
```

Keep both `_vuln_findings.json` and `_audit_context.md` in the target directory — they
are durable artifacts. `_vuln_findings.json` is useful for re-running the report generator,
diffing findings across runs, and SOC ingestion. `_audit_context.md` contains the deep
architectural context (module map, data flows, trust boundaries, per-function analysis)
needed by downstream tooling — including Phase 7 if the developer guide was requested.

---

## Phase 7 — Developer Remediation Guide PDF (if requested)

**Run only if the user answered `yes` in Step 0 question 6.**

This phase produces a developer-facing PDF using the `claude-scientific-writer:scientific-writing`
skill — the same pipeline that authored the validated vulnapp guide. All content comes from the
two durable artifacts already in the target directory; no research-lookup is needed.

### Step 1 — Invoke the scientific-writing skill

Use the **Skill tool** to invoke `claude-scientific-writer:scientific-writing` with this prompt:

```
Write a high-quality developer security remediation guide for the <ProjectName> codebase.

Source files (both located at <target_path>):
  - _audit_context.md   — deep architectural context: module map, data flows,
                          trust boundaries, per-function analysis
  - _vuln_findings.json — all findings with CVSS scores, evidence, and remediation

Skip the research-lookup step — all content is provided in those two files.
Audience: software developers and engineering leads, not security analysts.

Output: save the guide as <target_path>/<ProjectName>_Developer_Remediation_Guide.md

The guide must be written in flowing prose (no bullet-point body sections).
Structure:
  For Engineering Leads: The One-Page Summary (callout box: TL;DR, sprint estimates)
  1. How the Codebase Got Here: Understanding the Root Causes
     (3–6 systemic anti-patterns from _audit_context.md that explain most findings)
  2. What an Attacker Can Do Right Now (No Login Required)
     (2–4 highest-severity zero-prerequisites attack paths with PoC one-liners)
  3. File-by-File Remediation Instructions
     (one subsection per file/finding cluster; BEFORE + AFTER code blocks; why it works)
  4. Architectural Recommendations
     (2–4 structural improvements; not sprint-required — context for later)
  5. Sprint-Ready Remediation Roadmap
     (Sprint 1: Critical, Sprint 2: High, Sprint 3: Medium/Low + deps; hours per sprint)
  6. Verifying the Fixes
     (one concrete test command per major fix type)
  7. What Not to Change
     (security_strengths from _vuln_findings.json — what to preserve)
  Appendix A: Complete Finding Reference Index
     (table: ID · Severity · Title · File:Line · Sprint · CVSS)
```

### Step 2 — Convert Markdown to PDF

First, try `generate_guide_html.py` (preferred — produces the styled navy/blue PDF matching the
report's visual identity):

```bash
GUIDE_SCRIPT="$(find /home -name generate_guide_html.py -path '*/vuln-assess/scripts/*' 2>/dev/null | head -1)"

if [ -n "$GUIDE_SCRIPT" ]; then
  python "$GUIDE_SCRIPT" \
    --guide   "<target_path>/<ProjectName>_Developer_Remediation_Guide.md" \
    --findings "<target_path>/_vuln_findings.json" \
    --output  "<target_path>/<ProjectName>_Developer_Remediation_Guide.pdf"
else
  # Fallback: pandoc → DOCX → LibreOffice PDF
  pandoc "<target_path>/<ProjectName>_Developer_Remediation_Guide.md" \
    -o "<target_path>/<ProjectName>_Developer_Remediation_Guide.docx" \
    --highlight-style=tango
  soffice --headless --convert-to pdf \
    --outdir "<target_path>" \
    "<target_path>/<ProjectName>_Developer_Remediation_Guide.docx" 2>/dev/null
  rm -f "<target_path>/<ProjectName>_Developer_Remediation_Guide.docx"
fi
```

### Step 3 — Confirm output

Add to the final confirmation message:
> Developer Remediation Guide → `<ProjectName>_Developer_Remediation_Guide.pdf`
> _(engineer-facing: root causes · before/after fixes · 3-sprint roadmap)_

---

## Quality Gates

Before running the report generator, verify against `_vuln_findings.json`:
- [ ] Every CRITICAL/HIGH finding has an exact `file.py:line` location
- [ ] Every finding has a real code snippet in `evidence` (not paraphrased)
- [ ] Every finding has a specific, actionable `remediation`
- [ ] CVSS scores are internally consistent with severity labels
- [ ] No hallucinated CVE numbers in `references` — CWE + OWASP if uncertain
- [ ] Every category in the checklist was considered (even if result is "not applicable")
- [ ] Architecture-level issues were checked (not just function-level grep matches)
- [ ] All `references` fields are non-empty (populated by Phase 5)

---

## Script Reference

`scripts/generate_report_html.py` — HTML → Chrome-headless PDF generator. **No pip dependencies.**

CLI: `python generate_report_html.py --findings <json> --output <pdf> [--watermark TEXT]`

Visual design: Space Grotesk + Space Mono + Syne fonts (Google Fonts) · dark navy (#0D1117)
cover with 42/58 grid split · severity-coded finding cards (crit/high/med/low color system) ·
fixed 12mm header + 10mm footer on every page · 30mm top padding gives 18mm of breathing
room below the header on body pages · `break-inside: avoid` + `padding-top` trick ensures
cards never split across page breaks.

**Report sections** (8 sections, gold-standard industry structure):
1. Cover · 2. Executive Summary · 3. Scope, Methodology & Architecture
4. Risk Dashboard (severity counts + OWASP category bars + finding index)
5. Threat Model & Attack Surface (assets / actors / entry points / trust boundaries)
6. Detailed Findings (grouped by severity, full cards with code evidence)
7. Attack Chain Analysis (multi-step exploit narratives, Cure53/NCC Group style)
8. Compliance Mapping (findings × OWASP / CWE / ISO 27001:2022 / NIST CSF / PCI DSS v4)
9. Security Strengths & Observations (positive controls — what not to change)

Chrome detection order: `google-chrome` → `google-chrome-stable` → `chromium` → `chromium-browser`.
If none found, script prints the HTML path for manual print-to-PDF.

`references/vuln_checklist.md` — 18-section checklist covering:
OWASP Web Top 10 · OWASP API Security Top 10 (2023) · CWE Top 25 ·
XSS/CSRF/SSRF/XXE/Deserialization · JWT/OAuth2/GraphQL · Cloud (AWS/GCP/Azure) ·
Architecture · Supply Chain · ReDoS · HTTP Smuggling · Security Observability

`references/cvss_guide.md` — CVSS 3.1 base score quick-reference for consistent scoring.
