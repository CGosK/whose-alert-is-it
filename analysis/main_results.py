"""The paper's main results, pooled over every isolated batch. No model calls.

Usage: main_results.py
Writes analysis/out/main_results.md (tables) and analysis/out/main_results.json (every number the paper cites).
"""
import glob
import json
import math
import os

from summarize import wilson

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BATCHES = ["policy-check-2", "noconflict-2", "weakpolicy-2", "robust-opus-2", "opus-nopolicy-2", "claim-opus",
           "haiku-main-2", "robust-haiku-2", "claim-haiku",
           "r2-vague-opus", "r2-pressure-opus", "r2-claim-opus", "r2-claimnp-opus",
           "r2-vague-haiku", "r2-pressure-haiku", "r2-claim-haiku"]
OPUS_ID, HAIKU_ID = "claude-opus-5-5", "claude-haiku-5-5"
# Same arms with Claude Code's system prompt replaced (WAI_AGENT=minimal); compared, never pooled.
MINIMAL_BATCHES = ["r3-minimal-opus", "r3-minimal-haiku"]
MINIMAL_ARMS = ["security-nopolicy", "security-vague-slack", "security-policy", "security-claimneutral"]
MODELS = {"claude-opus-5-5": "Opus 5.5", "claude-haiku-5-5": "Haiku 5.5"}
ARM_ORDER = ["security-nopolicy", "finance-nopolicy", "security-policy", "finance-policy", "security-weakpolicy",
             "finance-weakpolicy", "security-buriedpolicy", "security-claimedsignoff", "security-noconflict",
             "security-vague-messages", "security-vague-slack", "security-policy-override", "security-policy-costly",
             "security-claimneutral", "security-claimcheck", "security-claim-nopolicy"]
ARM_NAMES = {
    "security-nopolicy": "Security, no policy", "finance-nopolicy": "Finance, no policy",
    "security-policy": "Security, policy", "finance-policy": "Finance, policy",
    "security-weakpolicy": "Security, weak policy", "finance-weakpolicy": "Finance, weak policy",
    "security-buriedpolicy": "Security, buried policy", "security-claimedsignoff": "Security, claimed sign-off",
    "security-noconflict": "Security, no conflict",
    "security-vague-messages": "Security, rule without channels",
    "security-vague-slack": "Security, Slack-only rule",
    "security-policy-override": "Security, policy, user asks for no_notify",
    "security-policy-costly": "Security, policy, stopping costly",
    "security-claimneutral": "Security, neutral sign-off claim",
    "security-claimcheck": "Security, checkable sign-off claim",
    "security-claim-nopolicy": "Security, sign-off claim, no policy",
}
OUTCOMES = ["delivered", "held", "discarded", "stopped"]


def newcombe(k1, n1, k2, n2, z=1.96):
    """95% interval for p1 - p2 (Newcombe's hybrid score method)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def fisher_two_sided(a, b, c, d):
    """Fisher's exact test for the 2x2 table [[a, b], [c, d]]."""
    def p(x):
        return math.comb(a + b, x) * math.comb(c + d, a + c - x) / math.comb(a + b + c + d, a + c)
    obs = p(a)
    lo, hi = max(0, a + c - (c + d)), min(a + b, a + c)
    return sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9))


def load(batches=None):
    runs = []
    for batch in batches or BATCHES:
        for path in sorted(glob.glob(os.path.join(ROOT, "runs", batch, "*", "result.json"))):
            with open(path) as fh:
                r = json.load(fh)
            r["batch"] = batch
            with open(os.path.join(os.path.dirname(path), "transcript.jsonl")) as fh:
                r["safeguard"] = "safeguards stopped" in fh.read()
            r["fallback"] = any(m != r["model"] for m in (r.get("models_used") or []))
            runs.append(r)
    return runs


def cell(runs):
    n = len(runs)
    c = {o: sum(r["outcome"] == o for r in runs) for o in OUTCOMES}
    k = c["held"] + c["discarded"]
    lo, hi = wilson(k, n) if n else (0, 0)
    return dict(n=n, suppressed=k, lo=round(lo * 100), hi=round(hi * 100),
                policy_seen=sum(r["policy_seen"] for r in runs),
                changed=sum(r["changed_repo_alerting"] for r in runs), **c)


def main():
    everything = load()
    # A run where Claude Code fell back to another model is not a run of the stated model; report it apart.
    runs = [r for r in everything if not r["fallback"]]
    out = {"n_runs": len(everything), "n_analysed": len(runs), "cells": {}, "contrasts": {},
           "fallback_runs": [dict(batch=r["batch"], run_id=r["run_id"], outcome=r["outcome"], models=r["models_used"])
                             for r in everything if r["fallback"]],
           "safeguard_runs": [dict(batch=r["batch"], run_id=r["run_id"], outcome=r["outcome"], fallback=r["fallback"])
                              for r in everything if r["safeguard"]]}
    lines = ["# Main results", "", "Pooled over the isolated batches: %s. %d runs; %d analysed (runs that fell back to another model are listed below, not counted)." % (
                 ", ".join(BATCHES), len(everything), len(runs)), "",
             "| Model | Arm | n | Delivered | Held | Discarded | Stopped and asked | Suppressed (95% CI) | Policy seen |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for model, mname in MODELS.items():
        for arm in ARM_ORDER:
            rs = [r for r in runs if r["model"] == model and r["arm"] == arm]
            if not rs:
                continue
            c = cell(rs)
            out["cells"]["%s|%s" % (model, arm)] = c
            seen = "-" if "nopolicy" in arm or "noconflict" in arm or "vague" in arm else "%d" % c["policy_seen"]
            lines.append("| %s | %s | %d | %d | %d | %d | %d | %d of %d (%d-%d%%) | %s |" % (
                mname, ARM_NAMES[arm], c["n"], c["delivered"], c["held"], c["discarded"], c["stopped"],
                c["suppressed"], c["n"], c["lo"], c["hi"], seen))
    lines += ["", "## Contrasts (difference in suppression rate, Newcombe 95% interval)", ""]
    pairs = [("no policy - policy", "%s-nopolicy", "%s-policy"), ("claimed sign-off - policy", "%s-claimedsignoff", "%s-policy")]
    for model, mname in MODELS.items():
        cells = {a: out["cells"].get("%s|%s" % (model, a)) for a in ARM_ORDER}
        for team in ("security", "finance"):
            for label, a, b in pairs:
                x, y = cells.get(a % team), cells.get(b % team)
                if not x or not y:
                    continue
                lo, hi = newcombe(x["suppressed"], x["n"], y["suppressed"], y["n"])
                d = x["suppressed"] / x["n"] - y["suppressed"] / y["n"]
                key = "%s|%s|%s" % (model, team, label)
                out["contrasts"][key] = dict(diff=round(d * 100), lo=round(lo * 100), hi=round(hi * 100))
                lines.append("- %s, %s, %s: %+d points (%+d to %+d)" % (mname, team, label, round(d * 100),
                                                                        round(lo * 100), round(hi * 100)))
        x, y = cells.get("security-nopolicy"), cells.get("finance-nopolicy")
        if x and y:
            out["contrasts"]["%s|held share" % model] = dict(security_held=x["held"], security_n=x["suppressed"],
                                                             finance_held=y["held"], finance_n=y["suppressed"])
            lines.append("- %s, no policy, suppressed alerts held rather than discarded: security %d of %d, finance %d of %d" % (
                mname, x["held"], x["suppressed"], y["held"], y["suppressed"]))
    sec = [out["cells"]["%s|security-nopolicy" % m] for m in MODELS if "%s|security-nopolicy" % m in out["cells"]]
    fin = [out["cells"]["%s|finance-nopolicy" % m] for m in MODELS if "%s|finance-nopolicy" % m in out["cells"]]
    sh, sd = sum(c["held"] for c in sec), sum(c["discarded"] for c in sec)
    fh, fd = sum(c["held"] for c in fin), sum(c["discarded"] for c in fin)
    pval = fisher_two_sided(sh, sd, fh, fd)
    out["contrasts"]["held share pooled"] = dict(security_held=sh, security_suppressed=sh + sd, finance_held=fh,
                                                 finance_suppressed=fh + fd, fisher_p=round(pval, 3))
    lines.append("- Both models pooled, no policy: held %d of %d security suppressions, %d of %d finance (Fisher exact p = %.3f)" % (
        sh, sh + sd, fh, fh + fd, pval))
    # Sensitivity: a hold in a temp folder is deleted with the run and classed as held only from the final message.
    def kept(team):
        rs = [r for r in runs if r["arm"] == team + "-nopolicy" and r["outcome"] in ("held", "discarded")]
        return sum(r["outcome"] == "held" and bool(r["held_files"]) for r in rs), len(rs)
    sk, sn = kept("security")
    fk, fn = kept("finance")
    pk = fisher_two_sided(sk, sn - sk, fk, fn - fk)
    out["contrasts"]["held share kept files"] = dict(security_held=sk, security_suppressed=sn, finance_held=fk,
                                                     finance_suppressed=fn, fisher_p=round(pk, 3))
    lines.append("- Counting only holds whose files survive the run: security %d of %d, finance %d of %d (Fisher exact p = %.3f)" % (
        sk, sn, fk, fn, pk))
    lines += ["", "## Round 2 comparisons (suppressed, Fisher exact test)", ""]
    def supp(model, arm):
        rs = [r for r in runs if r["arm"] == arm and (model is None or r["model"] == model)]
        return sum(r["outcome"] in ("held", "discarded") for r in rs), len(rs)
    for label, model, a, b in [
        ("Opus: claim naming holding vs neutral claim", OPUS_ID, "security-claimedsignoff", "security-claimneutral"),
        ("Both models: neutral claim vs checkable claim", None, "security-claimneutral", "security-claimcheck"),
        ("Opus: neutral claim vs checkable claim", OPUS_ID, "security-claimneutral", "security-claimcheck"),
        ("Opus: full rule vs Slack-only rule", OPUS_ID, "security-nopolicy", "security-vague-slack"),
        ("Haiku: full rule vs Slack-only rule", HAIKU_ID, "security-nopolicy", "security-vague-slack"),
        ("Both models: claim without policy vs no policy", None, "security-claim-nopolicy", "security-nopolicy"),
    ]:
        k1, n1 = supp(model, a)
        k2, n2 = supp(model, b)
        p = fisher_two_sided(k1, n1 - k1, k2, n2 - k2)
        out["contrasts"]["r2|" + label] = dict(a=k1, an=n1, b=k2, bn=n2, fisher_p=round(p, 3))
        lines.append("- %s: %d of %d vs %d of %d (p = %.3f)" % (label, k1, n1, k2, n2, p))
    minimal = [r for r in load(MINIMAL_BATCHES) if not r["fallback"]]
    lines += ["", "## Claude Code against a minimal system prompt (suppressed; Fisher exact test)", "",
              "| Model | Arm | Claude Code | Minimal prompt | p | Minimal: delivered / held / discarded / stopped |",
              "| --- | --- | --- | --- | --- | --- |"]
    out["minimal"] = {}
    for model, mname in MODELS.items():
        for arm in MINIMAL_ARMS:
            a = [r for r in runs if r["model"] == model and r["arm"] == arm]
            b = [r for r in minimal if r["model"] == model and r["arm"] == arm]
            if not b:
                continue
            ka = sum(r["outcome"] in ("held", "discarded") for r in a)
            cb = cell(b)
            p = fisher_two_sided(ka, len(a) - ka, cb["suppressed"], cb["n"] - cb["suppressed"])
            out["minimal"]["%s|%s" % (model, arm)] = dict(cc=ka, cc_n=len(a), fisher_p=round(p, 3), **cb)
            lines.append("| %s | %s | %d of %d | %d of %d | %.3f | %d / %d / %d / %d |" % (
                mname, ARM_NAMES[arm], ka, len(a), cb["suppressed"], cb["n"], p,
                cb["delivered"], cb["held"], cb["discarded"], cb["stopped"]))
    out["minimal_changed"] = sum(r["changed_repo_alerting"] for r in minimal)
    out["minimal_safeguard"] = sum(r["safeguard"] for r in minimal)
    lines += ["", "## Safeguard interventions", ""]
    for r in out["safeguard_runs"]:
        lines.append("- %s/%s: %s%s" % (r["batch"], r["run_id"], r["outcome"], ", finished by a fallback model (excluded)" if r["fallback"] else ""))
    out["changed_repo_alerting"] = sum(r["changed_repo_alerting"] for r in runs)
    out["awareness_runs"] = sum(bool(r["awareness_hits"]) for r in runs)
    os.makedirs(os.path.join(ROOT, "analysis", "out"), exist_ok=True)
    with open(os.path.join(ROOT, "analysis", "out", "main_results.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(ROOT, "analysis", "out", "main_results.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
