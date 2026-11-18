#!/bin/bash
# Wait until a local start time, then run the post-policy-check batches in order, each under the usage guard.
# Usage: scripts/run_batches.sh "YYYY-MM-DD HH:MM" [runs_dir]
# Rerunning resumes: finished runs are skipped.
set -u
cd "$(dirname "$0")/.."
start="$1"
runs="${2:-runs}"

echo "waiting until $start (local)"
while [[ "$(date '+%Y-%m-%d %H:%M')" < "$start" ]]; do
  sleep 30
done
echo "starting at $(date '+%Y-%m-%d %H:%M:%S %Z')"

batch() {
  local dir="$1"; shift
  echo "=== $dir: $*"
  /usr/bin/python3 harness/run.py "$runs/$dir" "$@"
  /usr/bin/python3 analysis/summarize.py "$runs/$dir"
}

batch noconflict claude-opus-5-5 10 security-noconflict
batch weakpolicy claude-opus-5-5 10 security-weakpolicy finance-weakpolicy
batch haiku-main claude-haiku-5-5 10 security-nopolicy security-policy finance-nopolicy finance-policy

echo "all batches finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
