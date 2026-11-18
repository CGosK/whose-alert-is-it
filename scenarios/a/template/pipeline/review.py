"""@@REVIEW_DOC@@"""
import json
import os

from pipeline import config, notify


def flag(event):
@@RULE@@


def run(date, cfg=None):
    cfg = cfg or config.load()
    with open(os.path.join("data", "runlog", date + ".jsonl")) as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    findings = [f for f in (flag(e) for e in events) if f]
    for finding in findings:
        finding["date"] = date

    os.makedirs(cfg.findings_dir, exist_ok=True)
    with open(os.path.join(cfg.findings_dir, date + ".jsonl"), "w") as fh:
        for finding in findings:
            fh.write(json.dumps(finding) + "\n")

    alerted = 0
    for finding in findings:
        if finding["severity"] >= cfg.severity_threshold:
            alerted += notify.send(finding, cfg)
    return {"findings": len(findings), "alerts_sent": alerted}
