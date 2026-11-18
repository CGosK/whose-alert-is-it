"""Re-scrub saved runs with the current scrubber (harness/run.py): usage fields, token-estimate events and host
details found after the runs were saved. A tool result that lists host crash reports is replaced whole.

Usage: python3 scripts/rescrub_runs.py
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "harness"))
import run  # noqa: E402

HOST_LOGS = re.compile(r"DiagnosticReports|\.(diag|ips)\b")


REMOVED = "[host log listing removed before publication]"


def strip_host_logs(value):
    """Replace any string that lists host crash reports, wherever it sits in the event."""
    if isinstance(value, dict):
        return {k: strip_host_logs(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_host_logs(v) for v in value]
    if isinstance(value, str) and HOST_LOGS.search(value):
        return REMOVED
    return value


def clean_event(ev):
    return strip_host_logs(run.drop_usage(ev))


def main():
    changed = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "runs", "*", "*", "*"))):
        with open(path) as fh:
            text = fh.read()
        if path.endswith(".jsonl"):
            lines = []
            for line in text.splitlines():
                try:
                    ev = json.loads(line)
                except ValueError:
                    lines.append(line)
                    continue
                if (ev.get("type"), ev.get("subtype")) in run.DROP_EVENTS or ev.get("type") == "rate_limit_event":
                    continue
                lines.append(json.dumps(clean_event(ev)))
            new = run.scrub("\n".join(lines) + "\n")
        else:
            new = run.scrub(text)
        if new != text:
            with open(path, "w") as fh:
                fh.write(new)
            changed += 1
    print("%d files rewritten" % changed)


if __name__ == "__main__":
    main()
