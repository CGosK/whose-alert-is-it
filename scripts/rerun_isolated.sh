#!/bin/bash
# Rerun every batch in the main results with per-run isolation (commit 5266555), into new folders.
# Earlier batches are kept as they are. Rerunning this script resumes: finished runs are skipped.
set -u
cd "$(dirname "$0")/.."
batch() {
  local dir="$1"; shift
  echo "=== $dir: $*"
  /usr/bin/python3 harness/run.py "runs/$dir" "$@" < /dev/null
  /usr/bin/python3 analysis/summarize.py "runs/$dir"
}
batch policy-check-2 claude-opus-5-5 10 security-policy finance-policy
batch noconflict-2 claude-opus-5-5 10 security-noconflict
batch weakpolicy-2 claude-opus-5-5 10 security-weakpolicy finance-weakpolicy
batch robust-opus-2 claude-opus-5-5 10 security-buriedpolicy security-claimedsignoff
batch haiku-main-2 claude-haiku-5-5 10 security-nopolicy security-policy finance-nopolicy finance-policy
batch robust-haiku-2 claude-haiku-5-5 10 security-buriedpolicy security-claimedsignoff
echo "all reruns finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
