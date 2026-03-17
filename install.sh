#!/usr/bin/env bash
# install.sh — claude-skills-security
# Sets up vuln-assessment skill and its dependencies for Claude Code.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── 1. vuln-assessment skill ──────────────────────────────────────────────────
SKILLS_DIR="$CLAUDE_DIR/skills"
mkdir -p "$SKILLS_DIR"

if [ -d "$SKILLS_DIR/vuln-assessment" ]; then
  warn "vuln-assessment already exists at $SKILLS_DIR/vuln-assessment — skipping (delete it first to reinstall)"
else
  cp -r "$SCRIPT_DIR/vuln-assessment" "$SKILLS_DIR/vuln-assessment"
  info "Installed vuln-assessment → $SKILLS_DIR/vuln-assessment"
fi

# ── 2. audit-context-building (bundled dep) ───────────────────────────────────
PLUGIN_DIR="$CLAUDE_DIR/plugins/marketplaces/trailofbits/plugins"
mkdir -p "$PLUGIN_DIR"

if [ -d "$PLUGIN_DIR/audit-context-building" ]; then
  warn "audit-context-building already installed — skipping"
else
  cp -r "$SCRIPT_DIR/deps/audit-context-building" "$PLUGIN_DIR/audit-context-building"
  info "Installed audit-context-building → $PLUGIN_DIR/audit-context-building"
fi

# ── 3. claude-scientific-writer (optional, needed for Phase 5 + Phase 7) ──────
echo ""
echo "  claude-scientific-writer is an optional dependency used for:"
echo "    • Phase 5 — CVE/CWE reference enrichment (research-lookup)"
echo "    • Phase 7 — Developer Remediation Guide generation (scientific-writing)"
echo ""
echo "  Without it, both phases fall back to built-in knowledge / pandoc."
echo ""
read -r -p "  Install claude-scientific-writer now? [y/N] " install_sci
if [[ "${install_sci,,}" == "y" ]]; then
  if command -v claude &>/dev/null; then
    claude plugin install claude-scientific-writer 2>/dev/null && \
      info "Installed claude-scientific-writer via Claude Code" || \
      warn "Could not auto-install — run: claude plugin install claude-scientific-writer"
  else
    warn "claude CLI not found — install manually: claude plugin install claude-scientific-writer"
  fi
else
  info "Skipped claude-scientific-writer (you can install it later)"
fi

# ── 4. System dependencies ────────────────────────────────────────────────────
echo ""
info "Checking system dependencies..."

if ! command -v google-chrome &>/dev/null && ! command -v chromium &>/dev/null && ! command -v chromium-browser &>/dev/null; then
  warn "Chrome/Chromium not found — required for PDF generation."
  warn "Install: sudo apt-get install chromium   OR   brew install --cask google-chrome"
else
  info "Chrome/Chromium found"
fi

if ! command -v python3 &>/dev/null; then
  warn "python3 not found — required for PDF generation scripts"
else
  info "Python 3 found ($(python3 --version))"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  vuln-assessment installed. Restart Claude Code to activate.${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Usage: Open any codebase in Claude Code and say:"
echo "    'Run a security audit on this codebase'"
echo "    'Check this code for vulnerabilities'"
echo "    'Generate a vulnerability report'"
echo ""
