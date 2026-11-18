#!/bin/bash
# Same scenario with Claude Code's system prompt replaced by a short neutral one (WAI_AGENT=minimal).
# Four arms, both models, 10 runs each. Isolated runs; rerunning resumes.
set -u
cd "$(dirname "$0")/.."
export WAI_AGENT=minimal
batch() {
  local dir="$1"; shift
  echo "=== $dir: $*"
  /usr/bin/python3 harness/run.py "runs/$dir" "$@" < /dev/null
  /usr/bin/python3 analysis/summarize.py "runs/$dir"
}
ARMS="security-nopolicy security-vague-slack security-policy security-claimneutral"
batch r3-minimal-opus claude-opus-5-5 10 $ARMS
batch r3-minimal-haiku claude-haiku-5-5 10 $ARMS
echo "minimal-prompt runs finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
