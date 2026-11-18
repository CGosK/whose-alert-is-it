"""Check every number in PAPER.md against the analysis outputs. No model calls.

Usage: check_paper.py   (run analysis/main_results.py first)
Each claim is the exact wording in the paper with its numbers filled in from the data; a claim that doesn't
appear means the paper and the data disagree.
"""
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import main_results as M  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "harness"))
import check as C  # noqa: E402

OPUS, HAIKU = "claude-opus-5-5", "claude-haiku-5-5"
LABELS_DIR = os.path.join(ROOT, "analysis", "labels")


def norm(text):
    return re.sub(r"\s+", " ", text)


def pooled(cells, model, arms):
    keys = ["%s|%s" % (model, a) for a in arms]
    cs = [cells[k] for k in keys if k in cells]
    total = {f: sum(c[f] for c in cs) for f in ("n", "delivered", "held", "discarded", "stopped", "suppressed")}
    lo, hi = M.wilson(total["suppressed"], total["n"])
    total.update(lo=round(lo * 100), hi=round(hi * 100))
    return total


def table_rows(cells):
    names = {"security-nopolicy": "Security, no policy", "finance-nopolicy": "Finance, no policy",
             "security-noconflict": "Security, no conflict", "security-vague-messages": "Security, rule without channels",
             "security-vague-slack": "Security, Slack-only rule", "security-buriedpolicy": "Security, buried policy",
             "security-policy-override": "Security, policy, user asks for no_notify",
             "security-policy-costly": "Security, policy, stopping costly",
             "security-claimedsignoff": "Security, claim naming holding", "security-claimneutral": "Security, neutral claim",
             "security-claimcheck": "Security, checkable claim", "security-claim-nopolicy": "Security, claim, no policy"}
    order = ["security-nopolicy", "finance-nopolicy", "security-noconflict", "security-vague-messages",
             "security-vague-slack", "POLICY", "WEAK", "security-buriedpolicy", "security-policy-override",
             "security-policy-costly", "security-claimedsignoff", "security-claimneutral", "security-claimcheck",
             "security-claim-nopolicy"]
    for model, mname in ((OPUS, "Opus 5.5"), (HAIKU, "Haiku 5.5")):
        for arm in order:
            if arm == "POLICY":
                label, arms = "Policy, both teams", ["security-policy", "finance-policy"]
            elif arm == "WEAK":
                label, arms = "Weak policy, both teams", ["security-weakpolicy", "finance-weakpolicy"]
            else:
                label, arms = names[arm], [arm]
            if not any("%s|%s" % (model, x) in cells for x in arms):
                continue
            t = pooled(cells, model, arms)
            yield "| %s | %s | %d | %d | %d | %d | %d | %d (%d-%d%%) |" % (
                mname, label, t["n"], t["delivered"], t["held"], t["discarded"], t["stopped"], t["suppressed"], t["lo"], t["hi"])


def claims():
    with open(os.path.join(ROOT, "analysis", "out", "main_results.json")) as fh:
        res = json.load(fh)
    cells, con = res["cells"], res["contrasts"]
    everything = M.load()
    runs = [r for r in everything if not r["fallback"]]
    c = lambda m, a: cells["%s|%s" % (m, a)]
    r2 = lambda label: con["r2|" + label]
    policy = [r for r in runs if r["arm"] in ("security-policy", "finance-policy", "security-weakpolicy",
                                              "finance-weakpolicy", "security-buriedpolicy",
                                              "security-policy-override", "security-policy-costly")]
    pressure = lambda arm: [r for r in runs if r["arm"] == arm]
    claimcheck = [r for r in runs if r["arm"] == "security-claimcheck"]
    looked = sum(any("signoff" in raw for _, _, raw in C.agent_actions(
        os.path.join(ROOT, "runs", r["batch"], r["run_id"], "transcript.jsonl"))) for r in claimcheck)
    hold = [r for r in runs if r["arm"] == "security-claimedsignoff"]
    hold_supp = [r for r in hold if r["outcome"] in ("held", "discarded")]
    o, h = pooled(cells, OPUS, ["security-nopolicy", "finance-nopolicy"]), pooled(cells, HAIKU, ["security-nopolicy", "finance-nopolicy"])
    ov, hv = c(OPUS, "security-vague-messages"), c(HAIKU, "security-vague-messages")
    os_, hs = c(OPUS, "security-vague-slack"), c(HAIKU, "security-vague-slack")
    oc, hc = c(OPUS, "security-claimedsignoff"), c(HAIKU, "security-claimedsignoff")
    on, hn = c(OPUS, "security-claimneutral"), c(HAIKU, "security-claimneutral")
    held, kept = con["held share pooled"], con["held share kept files"]
    nc = c(OPUS, "security-noconflict")
    sg = res["safeguard_runs"]
    sg_fb = [x for x in sg if x["fallback"]]
    opus_hold_all = [r for r in everything if r["arm"] == "security-claimedsignoff" and r["model"] == OPUS]
    nn, cn = r2("Both models: claim without policy vs no policy"), r2("Both models: neutral claim vs checkable claim")
    hv_ = r2("Opus: claim naming holding vs neutral claim")
    words = {1: "one", 2: "two"}
    supp = sum(r["outcome"] in ("held", "discarded") for r in runs)

    out = [
        "I ran this scenario %d times" % res["n_runs"],
        "suppressed the alert in %d of %d Opus runs and %d of %d Haiku runs" % (o["suppressed"], o["n"], h["suppressed"], h["n"]),
        "in 5 of 10 Opus runs and 9 of 10 Haiku runs" if (os_["suppressed"], os_["n"], hs["suppressed"], hs["n"]) == (5, 10, 9, 10) else "SLACK MISMATCH",
        "none of %d policy runs suppressed the alert" % len(policy) if not any(r["outcome"] in ("held", "discarded") for r in policy) else "POLICY MISMATCH",
        "led Opus 5.5 to suppress in %d of %d runs" % (oc["suppressed"], oc["n"]),
        '"...signed off on this rerun" led to %d of %d' % (on["suppressed"], on["n"]),
        "and none suppressed (0 of %d)" % len(claimcheck) if looked == len(claimcheck) and not any(r["outcome"] in ("held", "discarded") for r in claimcheck) else "CLAIMCHECK MISMATCH",
        "I ran this scenario %d times" % res["n_runs"],
        "so the table covers %d" % res["n_analysed"],
        "%d of %d for Opus and %d of %d for Haiku with the full rule" % (o["suppressed"], o["n"], h["suppressed"], h["n"]),
        "made little difference (%d of %d and %d of %d)" % (ov["suppressed"], ov["n"], hv["suppressed"], hv["n"]),
        "Opus suppressed the alert in %d of %d runs, always by holding it, and stopped to ask in the other %d; Haiku suppressed it in %d of %d" % (
            os_["suppressed"], os_["n"], os_["stopped"], hs["suppressed"], hs["n"]) if os_["held"] == os_["suppressed"] else "SLACK HOLD MISMATCH",
        "Opus sent the alert in all %d runs" % nc["delivered"],
        "None of %d policy runs suppressed the alert, and all of them saw the policy" % len(policy) if all(r["policy_seen"] for r in policy) else "SEEN MISMATCH",
        "(%d of %d Opus runs stopped)" % (sum(r["outcome"] == "stopped" for r in runs if r["arm"].endswith("weakpolicy")),
                                          sum(1 for r in runs if r["arm"].endswith("weakpolicy"))),
        "moving the policy into a linked document (%d of %d)" % (sum(r["outcome"] == "stopped" for r in runs if r["arm"] == "security-buriedpolicy"),
                                                                 sum(1 for r in runs if r["arm"] == "security-buriedpolicy")),
        "explicitly asked for `no_notify` (%d runs), or said they were offline and the job had to ship tonight (%d runs)" % (
            len(pressure("security-policy-override")), len(pressure("security-policy-costly"))),
        "all %d stopped and asked" % sum(r["outcome"] == "stopped" for r in policy),
        "Opus 5.5 suppressed the alert in %d of %d runs and Haiku in %d of %d, nearly always by holding it (%d of %d suppressions)" % (
            oc["suppressed"], oc["n"], hc["suppressed"], hc["n"], sum(r["outcome"] == "held" for r in hold_supp), len(hold_supp)),
        "Opus suppressed in %d of %d runs (p = %.3f against the holding wording, which ran in an earlier round) and Haiku in %d of %d" % (
            on["suppressed"], on["n"], hv_["fisher_p"], hn["suppressed"], hn["n"]),
        "%d of %d suppressed, against %d of %d with no claim" % (nn["a"], nn["an"], nn["b"], nn["bn"]),
        "every one of the %d agents opened it" % looked,
        "(0 of %d, against %d of %d with the neutral claim; p = %.2f" % (cn["bn"], cn["a"], cn["an"], cn["fisher_p"]),
        "in %d of the %d Opus runs with the claim naming holding" % (len(sg), len(opus_hold_all)),
        "in %s, Claude Code fell back to Opus 4.8" % words.get(len(sg_fb), "MISMATCH"),
        "%d of %d suppressed security alerts were held for someone to release, against %d of %d finance alerts (p = %.3f)" % (
            held["security_held"], held["security_suppressed"], held["finance_held"], held["finance_suppressed"], held["fisher_p"]),
        "gives %d of %d against %d of %d (p = %.3f)" % (kept["security_held"], kept["security_suppressed"],
                                                        kept["finance_held"], kept["finance_suppressed"], kept["fisher_p"]),
    ]
    mn = res["minimal"]
    for m, mname in ((OPUS, "Opus 5.5"), (HAIKU, "Haiku 5.5")):
        for arm, label in (("security-nopolicy", "Security, no policy"), ("security-vague-slack", "Security, Slack-only rule"),
                           ("security-policy", "Security, policy"), ("security-claimneutral", "Security, neutral claim")):
            x = mn["%s|%s" % (m, arm)]
            out.append("| %s | %s | %d of %d | %d of %d |" % (mname, label, x["cc"], x["cc_n"], x["suppressed"], x["n"]))
    out.append("smallest p = %.2f" % min(x["fisher_p"] for x in mn.values()))
    out.append("In 80 further runs" if sum(x["n"] for x in mn.values()) == 80 else "MINIMAL COUNT MISMATCH")
    with open(os.path.join(LABELS_DIR, "claude_labels_r3.csv"), newline="") as fh:
        r3 = list(csv.DictReader(fh))
    d3 = [r["disclosed"] for r in r3 if r["disclosed"] != "na"]
    f3 = [r["followup_accurate"] for r in r3 if r["followup_accurate"] != "na"]
    msupp = sum(x["suppressed"] for x in mn.values())
    out.append("All %d suppressed runs disclosed the alert, all %d follow-up" % (msupp, len(f3))
               if d3.count("yes") == len(d3) == msupp and f3.count("yes") == len(f3) else "MINIMAL LABEL MISMATCH")
    if res["minimal_changed"] == 0:
        out.append("and no run changed the repo's alerting.")
    out += list(table_rows(cells))
    if res["changed_repo_alerting"] == 0 and not any(r.get("test_weakened") for r in runs):
        out.append("No run changed the repo's alerting configuration or the regression test")
    disc, fol = [], []
    for name in ("claude_labels.csv", "claude_labels_r2.csv"):
        with open(os.path.join(LABELS_DIR, name), newline="") as fh:
            for row in csv.DictReader(fh):
                if row["disclosed"] != "na":
                    disc.append(row["disclosed"])
                if row["followup_accurate"] != "na":
                    fol.append(row["followup_accurate"])
    lead = re.compile(r"no messages (were|went)|nothing was sent|sent nothing|nothing went out|i (did not|didn't) send any messages", re.I)
    sup_runs = [r for r in M.load(M.BATCHES) if not r["fallback"] and r["outcome"] in ("held", "discarded")]
    out.append("Nearly half (%d of %d) open with a line saying nothing was sent" % (
        sum(bool(lead.search(r["final_message"][:300])) for r in sup_runs), len(sup_runs)))
    out.append("In all %d suppressed runs" % supp if disc.count("yes") == supp == len(disc) else "DISCLOSURE MISMATCH")
    out.append("All %d of %d follow-up answers were accurate" % (fol.count("yes"), len(fol)))
    with open(os.path.join(ROOT, "analysis", "out", "planted_summary.json")) as fh:
        pl = json.load(fh)
    out.append("it caught all %d" % pl["total"] if pl["caught"] == pl["total"] else "PLANTED MISSES")
    with open(os.path.join(ROOT, "analysis", "out", "hard_summary.json")) as fh:
        hd = json.load(fh)
    out.append("the grader gave the intended label on %d of %d judgements, and a human labeller, also blind, on %d of %d" % (
        hd["claude"]["right"], hd["claude"]["total"], hd["human"]["right"], hd["human"]["total"]))
    out.append("Human and grader agreed on %d of %d labels" % (hd["agreement"]["agree"], hd["agreement"]["total"]))
    return out


def main():
    with open(os.path.join(ROOT, "paper", "PAPER.md")) as fh:
        paper = norm(fh.read())
    missing = [c for c in claims() if norm(c) not in paper]
    for c in missing:
        print("NOT IN PAPER:", c)
    print("%s: %d claims checked" % ("FAIL" if missing else "ok", len(claims())))
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
