#!/bin/bash
# Final isolated batches: Opus without a policy (pilot 1 was never rerun with isolation), and 20 more
# claimed sign-off runs per model. Rerunning resumes.
set -u
cd "$(dirname "$0")/.."
batch() {
  local dir="$1"; shift
  echo "=== $dir: $*"
  /usr/bin/python3 harness/run.py "runs/$dir" "$@" < /dev/null
  /usr/bin/python3 analysis/summarize.py "runs/$dir"
}
batch opus-nopolicy-2 claude-opus-5-5 10 security-nopolicy finance-nopolicy
batch claim-opus claude-opus-5-5 20 security-claimedsignoff
batch claim-haiku claude-haiku-5-5 20 security-claimedsignoff
echo "final batches finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
