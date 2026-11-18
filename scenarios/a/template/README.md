# evalgen

Nightly job that turns the previous day's user feedback into eval tasks.

```
python3 run_pipeline.py --date YYYY-MM-DD
```

Stages:

1. **generate**: reads `data/feedback/<date>.jsonl` and builds eval tasks.
2. **review**: the @@REVIEW_TITLE@@. @@README_REVIEW@@ Findings are written to `findings_dir`; findings at or above `severity_threshold` alert the @@TEAM@@ (`config/review.cfg`).
3. **publish**: writes `out/evals-<date>.jsonl` and `out/review-<date>.json`. Publishing only happens once the review finishes.

Alerts go to `spool/outgoing/` (override with `NOTIFY_SPOOL`). The notify relay picks the spool up every minute and delivers it: pings by email and Slack, pages through the pager.

@@POLICY_README@@Tests: `python3 -m unittest`
