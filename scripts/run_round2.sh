#!/bin/bash
# Round 2: vague rules, policy under pressure, and sign-off variants, each on Opus 5.5 and Haiku 5.5.
# Isolated runs (per-run temp folder). Rerunning resumes.
set -u
cd "$(dirname "$0")/.."
batch() {
  local dir="$1"; shift
  echo "=== $dir: $*"
  /usr/bin/python3 harness/run.py "runs/$dir" "$@" < /dev/null
  /usr/bin/python3 analysis/summarize.py "runs/$dir"
}
batch r2-vague-opus claude-opus-5-5 10 security-vague-messages security-vague-slack
batch r2-pressure-opus claude-opus-5-5 10 security-policy-override security-policy-costly
batch r2-claim-opus claude-opus-5-5 20 security-claimneutral security-claimcheck
batch r2-claimnp-opus claude-opus-5-5 10 security-claim-nopolicy
batch r2-vague-haiku claude-haiku-5-5 10 security-vague-messages security-vague-slack
batch r2-pressure-haiku claude-haiku-5-5 10 security-policy-override security-policy-costly
batch r2-claim-haiku claude-haiku-5-5 10 security-claimneutral security-claimcheck security-claim-nopolicy
echo "round 2 finished at $(date '+%Y-%m-%d %H:%M:%S %Z')"
