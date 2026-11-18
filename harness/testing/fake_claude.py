#!/usr/bin/python3
"""Stand-in for the claude CLI in tests: emits a scripted rate_limit_event, then a result.

FAKE_PLAN is a JSON list of modes, used one per call in order (the last repeats); FAKE_COUNTER is a file
holding the next index. Modes: "ok" (20% used), "hot" (window at 96%), "overage" (using extra usage,
then hangs until killed). Resets are FAKE_RESET_IN seconds away.
"""
import fcntl
import json
import os
import sys
import time

if "--version" in sys.argv:
    print("0.0.0 (fake)")
    sys.exit(0)

with open(os.environ["FAKE_COUNTER"], "a+") as fh:
    fcntl.flock(fh, fcntl.LOCK_EX)
    fh.seek(0)
    index = int(fh.read() or 0)
    fh.seek(0)
    fh.truncate()
    fh.write(str(index + 1))

plan = json.loads(os.environ["FAKE_PLAN"])
mode = plan[min(index, len(plan) - 1)]
reset = time.time() + float(os.environ.get("FAKE_RESET_IN", "3"))
util = {"ok": 0.2, "hot": 0.96, "overage": 1.0}[mode]
info = {"status": "allowed" if mode != "overage" else "allowed", "resetsAt": reset, "rateLimitType": "five_hour",
        "isUsingOverage": mode == "overage",
        "unifiedWindows": {"five_hour": {"utilization": util, "resetsAt": reset, "status": "allowed"}}}

print(json.dumps({"type": "system", "subtype": "init"}), flush=True)
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": info}), flush=True)
if mode == "overage":
    time.sleep(120)
print(json.dumps({"type": "result", "result": "I stopped before rerunning.", "num_turns": 1}), flush=True)
