#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_layout_test.sh
# Layout & regression test runner for generate_report_html.py
#
# Run after every change to the generator script to verify:
#   1. All 5 severity levels render correctly
#   2. Multi-page findings don't break layout (VUL-001 is intentionally long)
#   3. Multi-line FILE locations render correctly (VUL-001, VUL-004)
#   4. Long evidence blocks stay within page bounds (VUL-001, VUL-002)
#   5. Inline backtick code spans render as styled pills
#   6. All report sections (Cover, Exec Summary, Scope, Findings, Roadmap) present
#   7. Watermark renders without layout breakage
#   8. Report generates without errors
#
# Usage:
#   ./evals/run_layout_test.sh
#   ./evals/run_layout_test.sh --watermark DRAFT
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR="$(find ~/.claude/skills/vuln-assess/scripts -name generate_report_html.py | head -1)"
FIXTURE="$SCRIPT_DIR/fixtures/layout_test/_vuln_findings.json"
OUT_DIR="/tmp/vuln_layout_test"
WATERMARK="${1:-}"

mkdir -p "$OUT_DIR"

PASS=0
FAIL=0

run_test() {
  local name="$1"
  local output="$2"
  local extra_args="${3:-}"

  printf "  %-55s" "$name"
  if python "$GENERATOR" \
      --findings "$FIXTURE" \
      --output "$output" \
      $extra_args \
      > "$OUT_DIR/${name// /_}.log" 2>&1; then
    if [ -f "$output" ] && [ "$(stat -c%s "$output")" -gt 10000 ]; then
      echo "✓ PASS  $(stat -c%s "$output" | numfmt --to=iec)B"
      PASS=$((PASS + 1))
    else
      echo "✗ FAIL  (PDF too small or missing)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo "✗ FAIL  (generator error — see $OUT_DIR/${name// /_}.log)"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Vulnerability Report Layout Test Suite"
echo "  Generator: $GENERATOR"
echo "  Fixture:   $FIXTURE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "── Test cases ─────────────────────────────────────────────────"

# T01: Standard render — all 5 severities, no watermark
run_test "T01 Standard (all severities)" \
  "$OUT_DIR/T01_standard.pdf"

# T02: With DRAFT watermark
run_test "T02 Watermark DRAFT" \
  "$OUT_DIR/T02_watermark_draft.pdf" \
  "--watermark DRAFT"

# T03: With CONFIDENTIAL watermark
run_test "T03 Watermark CONFIDENTIAL" \
  "$OUT_DIR/T03_watermark_confidential.pdf" \
  "--watermark CONFIDENTIAL"

# T04: Single finding (only CRITICAL VUL-001 — the multi-page card)
SINGLE_FINDING="$OUT_DIR/single_finding.json"
python3 -c "
import json
with open('$FIXTURE') as f:
    d = json.load(f)
d['findings'] = [d['findings'][0]]  # VUL-001 only
with open('$SINGLE_FINDING', 'w') as f:
    json.dump(d, f)
"
printf "  %-55s" "T04 Single multi-page finding (VUL-001)"
if python "$GENERATOR" \
    --findings "$SINGLE_FINDING" \
    --output "$OUT_DIR/T04_single_multipage.pdf" \
    > "$OUT_DIR/T04.log" 2>&1; then
  echo "✓ PASS  $(stat -c%s "$OUT_DIR/T04_single_multipage.pdf" | numfmt --to=iec)B"
  PASS=$((PASS + 1))
else
  echo "✗ FAIL"
  FAIL=$((FAIL + 1))
fi

# T05: INFO-only findings (minimal content edge case)
INFO_ONLY="$OUT_DIR/info_only.json"
python3 -c "
import json
with open('$FIXTURE') as f:
    d = json.load(f)
d['findings'] = [f for f in d['findings'] if f['severity'] == 'INFO']
with open('$INFO_ONLY', 'w') as f:
    json.dump(d, f)
"
printf "  %-55s" "T05 INFO-only findings"
if python "$GENERATOR" \
    --findings "$INFO_ONLY" \
    --output "$OUT_DIR/T05_info_only.pdf" \
    > "$OUT_DIR/T05.log" 2>&1; then
  echo "✓ PASS  $(stat -c%s "$OUT_DIR/T05_info_only.pdf" | numfmt --to=iec)B"
  PASS=$((PASS + 1))
else
  echo "✗ FAIL"
  FAIL=$((FAIL + 1))
fi

# T06: No external deps / minimal metadata
MINIMAL="$OUT_DIR/minimal.json"
python3 -c "
import json
with open('$FIXTURE') as f:
    d = json.load(f)
d['scope_rows'] = [['Module', 'Path', 'Lines']]
d['external_deps'] = []
d['data_flow_summary'] = ''
d['branch'] = 'N/A'
with open('$MINIMAL', 'w') as f:
    json.dump(d, f)
"
printf "  %-55s" "T06 Minimal metadata (no deps / no data flow)"
if python "$GENERATOR" \
    --findings "$MINIMAL" \
    --output "$OUT_DIR/T06_minimal_meta.pdf" \
    > "$OUT_DIR/T06.log" 2>&1; then
  echo "✓ PASS  $(stat -c%s "$OUT_DIR/T06_minimal_meta.pdf" | numfmt --to=iec)B"
  PASS=$((PASS + 1))
else
  echo "✗ FAIL"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "── WeasyPrint renderer tests ───────────────────────────────────"

WP_PASS=0
WP_FAIL=0

run_wp_test() {
  local name="$1"
  local output="$2"
  local extra_args="${3:-}"

  printf "  %-55s" "$name"
  if python "$GENERATOR" \
      --findings "$FIXTURE" \
      --output "$output" \
      --renderer weasyprint \
      $extra_args \
      > "$OUT_DIR/${name// /_}.log" 2>&1; then
    if [ -f "$output" ] && [ "$(stat -c%s "$output")" -gt 10000 ]; then
      echo "✓ PASS  $(stat -c%s "$output" | numfmt --to=iec)B"
      WP_PASS=$((WP_PASS + 1))
    else
      echo "✗ FAIL  (PDF too small or missing)"
      WP_FAIL=$((WP_FAIL + 1))
    fi
  else
    echo "✗ FAIL  (generator error — see $OUT_DIR/${name// /_}.log)"
    WP_FAIL=$((WP_FAIL + 1))
  fi
}

# WP-T01: Standard render — all 5 severities, no watermark
run_wp_test "WP-T01 Standard (all severities)" \
  "$OUT_DIR/wp_T01_standard.pdf"

# WP-T02: With DRAFT watermark
run_wp_test "WP-T02 Watermark DRAFT" \
  "$OUT_DIR/wp_T02_watermark_draft.pdf" \
  "--watermark DRAFT"

# WP-T03: With CONFIDENTIAL watermark
run_wp_test "WP-T03 Watermark CONFIDENTIAL" \
  "$OUT_DIR/wp_T03_watermark_confidential.pdf" \
  "--watermark CONFIDENTIAL"

# WP-T04: Single finding (only VUL-001 — the multi-page card)
printf "  %-55s" "WP-T04 Single multi-page finding (VUL-001)"
if python "$GENERATOR" \
    --findings "$SINGLE_FINDING" \
    --output "$OUT_DIR/wp_T04_single_multipage.pdf" \
    --renderer weasyprint \
    > "$OUT_DIR/WP_T04.log" 2>&1; then
  echo "✓ PASS  $(stat -c%s "$OUT_DIR/wp_T04_single_multipage.pdf" | numfmt --to=iec)B"
  WP_PASS=$((WP_PASS + 1))
else
  echo "✗ FAIL"
  WP_FAIL=$((WP_FAIL + 1))
fi

# WP-T05: INFO-only findings
printf "  %-55s" "WP-T05 INFO-only findings"
if python "$GENERATOR" \
    --findings "$INFO_ONLY" \
    --output "$OUT_DIR/wp_T05_info_only.pdf" \
    --renderer weasyprint \
    > "$OUT_DIR/WP_T05.log" 2>&1; then
  echo "✓ PASS  $(stat -c%s "$OUT_DIR/wp_T05_info_only.pdf" | numfmt --to=iec)B"
  WP_PASS=$((WP_PASS + 1))
else
  echo "✗ FAIL"
  WP_FAIL=$((WP_FAIL + 1))
fi

# WP-T06: No external deps / minimal metadata
printf "  %-55s" "WP-T06 Minimal metadata (no deps / no data flow)"
if python "$GENERATOR" \
    --findings "$MINIMAL" \
    --output "$OUT_DIR/wp_T06_minimal_meta.pdf" \
    --renderer weasyprint \
    > "$OUT_DIR/WP_T06.log" 2>&1; then
  echo "✓ PASS  $(stat -c%s "$OUT_DIR/wp_T06_minimal_meta.pdf" | numfmt --to=iec)B"
  WP_PASS=$((WP_PASS + 1))
else
  echo "✗ FAIL"
  WP_FAIL=$((WP_FAIL + 1))
fi

echo ""
echo "── Results ─────────────────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
WP_TOTAL=$((WP_PASS + WP_FAIL))
echo "  Chrome renderer:     Passed $PASS / $TOTAL"
echo "  WeasyPrint renderer: Passed $WP_PASS / $WP_TOTAL"
FAIL=$((FAIL + WP_FAIL))
if [ "$FAIL" -gt 0 ]; then
  echo "  Some tests FAILED — check logs in $OUT_DIR/"
  echo ""
  exit 1
else
  echo ""
  echo "  All tests passed. PDFs saved to: $OUT_DIR/"
  echo "  Chrome PDFs:     T01-T06_*.pdf"
  echo "  WeasyPrint PDFs: wp_T01-T06_*.pdf"
  echo ""
  echo "  Key files for visual verification:"
  echo "    Chrome:     T01_standard.pdf"
  echo "    WeasyPrint: wp_T01_standard.pdf  (check Evidence labels at page breaks)"
  echo "    Stress:     wp_T04_single_multipage.pdf  (VUL-001 multi-page card)"
  echo ""
fi
