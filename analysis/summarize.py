"""Tabulate a batch of runs.

Usage: summarize.py runs/<batch>
Writes analysis/out/<batch>_summary.txt. Blind labels for every batch are in labels.py.
"""
import glob
import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUTCOMES = ["delivered", "held", "discarded", "stopped"]
MASK = [("security on-call", "[team]"), ("finance on-call", "[team]"), ("security", "[team]"), ("finance", "[team]"),
        ("agent activity", "[review]"), ("spend review", "[review]"), ("spend", "[metric]")]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def mask(text):
    text = text or ""
    for a, b in MASK:
        text = text.replace(a, b).replace(a.capitalize(), b)
    return text


def table(runs):
    lines = ["%-20s %3s %9s %5s %9s %7s %16s %11s %8s %6s" % (
        "arm", "n", "delivered", "held", "discarded", "stopped", "suppressed (95%)", "policy seen", "changed", "aware")]
    for arm in sorted({r["arm"] for r in runs}):
        rs = [r for r in runs if r["arm"] == arm]
        n = len(rs)
        counts = {o: sum(r["outcome"] == o for r in rs) for o in OUTCOMES}
        k = counts["held"] + counts["discarded"]
        lo, hi = wilson(k, n)
        lines.append("%-20s %3d %9d %5d %9d %7d %3d [%3.0f-%3.0f%%] %11d %8d %6d" % (
            arm, n, counts["delivered"], counts["held"], counts["discarded"], counts["stopped"], k, lo * 100, hi * 100,
            sum(r["policy_seen"] for r in rs), sum(r["changed_repo_alerting"] for r in rs),
            sum(bool(r["awareness_hits"]) for r in rs)))
    return "\n".join(lines)


def main(batch_dir):
    batch = os.path.basename(batch_dir.rstrip("/"))
    runs = []
    for path in sorted(glob.glob(os.path.join(batch_dir, "*", "result.json"))):
        with open(path) as fh:
            runs.append(json.load(fh))
    out_dir = os.path.join(ROOT, "analysis", "out")
    os.makedirs(out_dir, exist_ok=True)
    summary = table(runs)
    with open(os.path.join(out_dir, batch + "_summary.txt"), "w") as fh:
        fh.write(summary + "\n")
    print(summary)


if __name__ == "__main__":
    main(sys.argv[1])
