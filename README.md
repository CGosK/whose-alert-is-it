# Whose Alert Is It?

Chris Graham, *Whose Alert Is It? A user's "no messages" against an organisation's alert policy*. Independent
research, November 2026. https://github.com/CGosK/whose-alert-is-it

**Paper:** [`paper/PAPER.md`](paper/PAPER.md).

Across 350 Claude Code runs (Opus 5.5 and Haiku 5.5), a user's rule about messages covered an automated
oversight alert: "don't send any messages" led to suppression in 39 of 40 runs without a policy, and even "don't
post anything in Slack" stretched to the pager alert in 14 of 20. A short written policy requiring the on-call's
sign-off stopped suppression in all 120 policy runs without a sign-off claim, including when the user asked for
it; the agents stopped and asked instead. A claimed sign-off got past the policy depending on its wording, and
never when the agent could check a sign-off log (tested with the plain claim only). Every suppression was
disclosed, by a blind Claude grader's labels, and none outlasted the rerun. With Claude Code's system prompt
replaced by a minimal one (80 more runs), no difference was detectable.

## What predates the project

Nothing. Everything here was written for this project, from November 2026.

## Reproduce the tables

Every table is computed from the saved runs in `runs/`. Recomputing makes no model calls and needs only
Python 3.9+.

```bash
python3 analysis/main_results.py      # the paper's tables: analysis/out/main_results.md and .json
python3 paper/check_paper.py          # every number in the paper, checked against those outputs
python3 analysis/summarize.py runs/<batch>
```

| Paper | Script |
| --- | --- |
| Results table, contrasts, held-versus-discarded test | `analysis/main_results.py` |
| Disclosure and follow-up accuracy | `analysis/labels.py score` (labels in `analysis/labels/`) |
| Planted-failure check of the grader | `analysis/planted.py score` |
| Hard cases, human against grader | `analysis/hardcases.py score` |
| Every number in the text | `paper/check_paper.py` |

Each call writes `analysis/out/<batch>_summary.txt`.

Disclosure and follow-up accuracy are labelled by a blind Claude grader (`harness/grade.py`, which makes model
calls under the same usage guard), blind to batch, arm and model: `claude_labels.csv` for the first round,
`claude_labels_r2.csv` and `claude_labels_r3.csv` for the later rounds. The grader was checked on 22 planted
failures (`analysis/planted.py`) and on 30 hard items labelled blind by both the grader and the author
(`analysis/hardcases.py`). `analysis/labels/key.json` maps each blind item to its run; `analysis/labels.py score`
tabulates the labels by batch and arm. An earlier round of labels, made before the isolation fix, is kept in
`analysis/labels/pre-isolation/`.

To check the scoring itself, with scripted solutions and no model:

```bash
cd harness && python3 validate_checker.py
```

## Rerun the experiments

These make model calls. Each run builds a fresh copy of the scenario repo and runs headless Claude Code in it
(`claude -p`), then asks one follow-up question in the same session. Runs go through a Claude subscription
login, never the API: `harness/run.py` sets `CLAUDE_CONFIG_DIR=$HOME/.claude`, so point that at the login you
want. User settings, plugins, hooks and MCP servers are turned off, Claude Code's sandbox limits writes to the
run folder, and web tools and subagents are denied.

Each run gets its own sandbox temp folder (`CLAUDE_CODE_TMPDIR=/tmp/r/<run>`, removed after scoring), so runs
can't see each other's override configs or held alerts. The path must stay short: with a long one, Claude Code
falls back to the shared per-user folder (`/tmp/claude-<uid>`). Calls get an empty stdin and none of the
launching shell's `CLAUDE_*`, `ANTHROPIC_*` or `WAI_*` variables. Batches without the `-2` suffix shared the
per-user temp folder; see `notes/SPEC.md`.

```bash
cd harness
python3 run.py --canary ../.private/canary claude-opus-5-5     # what the agent can see; not committed
python3 run.py ../runs/<batch> claude-opus-5-5 20              # every arm, 20 runs each
python3 run.py ../runs/<batch> claude-opus-5-5 10 security-policy finance-policy
```

Each run makes two Claude Code calls (the task and the follow-up). Claude models can't be seeded, so a rerun
gives new draws.

Runs stay inside the plan's included usage and never use extra usage (`harness/usage_guard.py`). Claude Code
reports usage at the start of each call. No call starts while the five-hour or weekly window is at 80% or more;
the batch waits for that window to reset. If a call reports extra usage, a rejection, or a window at 95%,
every running call is stopped, those runs are discarded, and they're retried after the reset. Rerunning the
same command resumes a batch and skips finished runs. `python3 harness/test_usage_guard.py` checks all of
this against a fake CLI, with no model calls.

## Data

`runs/<batch>/` holds one folder per run, plus `launch.txt` with the command, model, date and Claude Code
version. Each run folder has:

- `transcript.jsonl` and `followup.jsonl`: the Claude Code event streams, with usage and token-count fields
  removed, local paths replaced by `<repo>`, `<tmp>` or `~`, and identities by `<user>`. In one run an agent
  listed the host's crash reports while looking for the alert relay (the sandbox limits writes, not reads); that
  listing is replaced by a note. `scripts/rescrub_runs.py` applies the current scrubber to saved runs.
- `diff.patch`: the agent's changes to the scenario repo
- `result.json`: the outcome, measures, final message and follow-up answer

| Batch | What |
| --- | --- |
| `r3-minimal-*` | **Minimal prompt (80 runs):** four arms with Claude Code's system prompt replaced (`WAI_AGENT=minimal`, `scripts/run_minimal.sh`); compared with, never pooled into, the main table |
| `r2-*` | **Round 2 (160 runs):** vaguer rules (`r2-vague-*`), the policy under pressure (`r2-pressure-*`), and sign-off variants (`r2-claim-*`, `r2-claimnp-opus`), on both models (`scripts/run_round2.sh`) |
| `*-2`, `claim-opus`, `claim-haiku` | **The main results (190 runs).** Every batch below except `pilot-1`, rerun with per-run isolation (`scripts/rerun_isolated.sh`), plus Opus without a policy (`opus-nopolicy-2`) and 20 more claimed sign-off runs per model (`scripts/run_final.sh`) |
| `robust-opus`, `robust-haiku` | Opus 5.5 and Haiku 5.5, 10 runs each of two security arms with the strong policy: `security-buriedpolicy` (the policy only in `docs/alerting.md`, linked from the README) and `security-claimedsignoff` (the user says the on-call already signed off) |
| `haiku-main` | Haiku 5.5, the four main arms, 10 runs each |
| `weakpolicy` | Opus 5.5, both weak-policy arms (without "This applies even when the person running the job asks otherwise"), 10 runs each |
| `noconflict` | Opus 5.5, the security arm without the "no messages" rule, 10 runs |
| `policy-check` | Opus 5.5, the two policy arms, 10 runs each: checks the policy is seen before the main runs |
| `pilot-1` | Opus 5.5, the two no-policy arms, 10 runs each, with an older follow-up question. Motivated the design; not part of the main results |

## Layout

- `scenarios/a/template/`: the scenario repo, with `@@TOKENS@@` filled per arm
- `harness/scenario_a.py`: arms, policy text, prompts and the repo builder
- `harness/check.py`: behavioural scoring (a clean rerun with a fake message sink, the original regression test,
  and the outcome classifier)
- `harness/run.py`: runs batches through headless Claude Code
- `harness/grade.py`: the blind Claude grader for disclosure and follow-up accuracy
- `analysis/planted.py`: planted failures that check the grader can say no
- `analysis/hardcases.py`: 30 hard items (17 edited, 13 real) labelled blind by a person and by the grader
- `analysis/`: per-batch tables (`summarize.py`), the paper's tables (`main_results.py`) and blind labels (`labels.py`, `labels/`)
- `paper/`: the write-up (`PAPER.md`) and `check_paper.py`
- `scripts/check_clean.py`: fails if anything tracked contains local paths, identities, hostnames, keys, private links or usage data; `--history` scans every blob in every commit

## Notes

- `notes/SPEC.md` is a working copy of the design. Where it differs from the paper, the paper is current.
- **AI use.** Claude Code (Opus 5.5) wrote most of the harness, scoring and analysis code and drafted the paper,
  under the author's design and review. Every number in the paper comes from scripts that read the saved runs,
  and `paper/check_paper.py` checks them. The experiments themselves run Claude models as the subjects.
- The scenario's company, people and addresses (`acme.dev`) are fictional.
- MIT licence (`LICENSE`), copyright Chris Graham.
