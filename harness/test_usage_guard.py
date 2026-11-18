"""End-to-end test of the usage guard with a fake claude CLI. No model calls.

Usage: python3 test_usage_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = os.path.join(HERE, "testing", "fake_claude.py")


def run_batch(plan, state=None, reset_in=3, runs=2):
    tmp = tempfile.mkdtemp(prefix="guard-")
    counter = os.path.join(tmp, "counter")
    state_path = os.path.join(tmp, "usage_state.json")
    if state:
        with open(state_path, "w") as fh:
            json.dump(state, fh)
    env = dict(os.environ, WAI_CLAUDE_BIN=FAKE, FAKE_PLAN=json.dumps(plan), FAKE_COUNTER=counter,
               FAKE_RESET_IN=str(reset_in), WAI_USAGE_STATE=state_path, WAI_RESUME_MARGIN="1",
               WAI_WORK_ROOT=os.path.join(tmp, "work"), WAI_PARALLEL="2")
    start = time.time()
    proc = subprocess.run([sys.executable, os.path.join(HERE, "run.py"), os.path.join(tmp, "batch"),
                           "fake-model", str(runs), "security-policy"],
                          env=env, capture_output=True, text=True, timeout=180)
    elapsed = time.time() - start
    done = sorted(os.listdir(os.path.join(tmp, "batch")))
    with open(counter) as fh:
        calls = int(fh.read())
    return proc, elapsed, done, calls


def check(name, ok, detail=""):
    print("%-4s %s %s" % ("ok" if ok else "FAIL", name, detail))
    return ok


if __name__ == "__main__":
    results = []

    # Both first calls report extra usage: both are killed, discarded, and retried after the reset.
    proc, elapsed, done, calls = run_batch(["overage", "overage", "ok"])
    out = proc.stdout
    results.append(check("overage stops running calls", "a call is using extra usage" in out, out[-300:] if "using extra" not in out else ""))
    results.append(check("cut-off runs are discarded", out.count("discarded; it will be retried") == 2))
    results.append(check("batch waits for the reset", elapsed >= 3, "%.1fs" % elapsed))
    results.append(check("every run finishes after the reset", done == ["launch.txt", "security-policy-01", "security-policy-02"], str(done)))
    procs = subprocess.run(["ps", "-ax", "-o", "command"], capture_output=True, text=True).stdout.splitlines()
    results.append(check("no killed call left running", not [p for p in procs if p.startswith("/usr/bin/python3 " + FAKE)]))
    results.append(check("each killed call was retried once", calls == 6, "%d calls" % calls))

    # A window at 96% stops the batch the same way, even without overage.
    proc, elapsed, done, calls = run_batch(["hot", "ok"], runs=1)
    results.append(check("near-limit window pauses the batch", "five_hour window at 96%" in proc.stdout and elapsed >= 3, "%.1fs" % elapsed))

    # A saved reading at 90% blocks the first call until that window resets.
    state = {"windows": {"five_hour": [0.90, time.time() + 3]}, "blocked_until": 0}
    proc, elapsed, done, calls = run_batch(["ok"], state=state, runs=1)
    results.append(check("saved reading near the limit delays the start", "paused until" in proc.stdout and elapsed >= 3 and calls == 2,
                         "%.1fs, %d calls" % (elapsed, calls)))

    # Normal usage: no pause, no retries (2 runs x task + follow-up = 4 calls).
    proc, elapsed, done, calls = run_batch(["ok"])
    results.append(check("normal usage runs straight through", "USAGE GUARD" not in proc.stdout and calls == 4, "%d calls" % calls))

    sys.exit(0 if all(results) else 1)
