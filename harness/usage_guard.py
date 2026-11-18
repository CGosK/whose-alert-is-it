"""Keep runs inside the plan's included usage, never extra usage (credits).

Claude Code reports usage in a rate_limit_event at the start of each call: utilization per window
(five_hour, seven_day), when each window resets, and whether the call is using overage. The guard:

- before a call starts, waits while any window is at LAUNCH_AT or more, until that window resets.
  Usage is only reported at the start of a call, so this headroom is what covers calls already running;
- during a call, if a call is using overage, is rejected, or a window reaches STOP_AT, kills every
  running call at once and blocks new ones until the reset. Runs that were cut off are retried then.

The last reading is saved, so a restarted batch also waits. Every reading is appended to usage.log
beside the state file, to show what a run costs.
"""
import datetime
import json
import os
import signal
import threading
import time

LAUNCH_AT = float(os.environ.get("WAI_LAUNCH_AT", "0.80"))
STOP_AT = float(os.environ.get("WAI_STOP_AT", "0.95"))
MARGIN = float(os.environ.get("WAI_RESUME_MARGIN", "120"))
UNKNOWN_RESET_WAIT = 15 * 60
OK_STATUSES = {"allowed", "allowed_warning"}


class CallKilled(Exception):
    """A call was stopped to avoid extra usage; the run should be discarded and retried."""


def _when(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


class UsageGuard:
    def __init__(self, state_path, log=print):
        self.state_path = state_path
        self.log = log
        self.lock = threading.Lock()
        self.procs = set()
        self.killed = set()
        self.windows = {}
        self.blocked_until = 0.0
        self._load()

    def _load(self):
        try:
            with open(self.state_path) as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            return
        now = time.time()
        self.windows = {k: tuple(v) for k, v in state.get("windows", {}).items() if v[1] > now}
        self.blocked_until = state.get("blocked_until", 0.0)

    def _save(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w") as fh:
            json.dump({"windows": self.windows, "blocked_until": self.blocked_until,
                       "saved": time.time()}, fh, indent=2)

    def register(self, proc):
        with self.lock:
            self.procs.add(proc)

    def unregister(self, proc):
        with self.lock:
            self.procs.discard(proc)

    def was_killed(self, proc):
        with self.lock:
            return proc.pid in self.killed

    def observe(self, info):
        """Take one rate_limit_info. Returns True if it stopped the running calls."""
        now = time.time()
        with self.lock:
            for name, w in (info.get("unifiedWindows") or {}).items():
                self.windows[name] = (float(w.get("utilization") or 0.0), float(w.get("resetsAt") or 0))
            reasons, resets = [], []
            if info.get("isUsingOverage"):
                reasons.append("a call is using extra usage")
                resets.append(info.get("resetsAt") or 0)
            if info.get("status") and info["status"] not in OK_STATUSES:
                reasons.append("status %s" % info["status"])
                resets.append(info.get("resetsAt") or 0)
            for name, (util, reset) in self.windows.items():
                if util >= STOP_AT and reset > now:
                    reasons.append("%s window at %.0f%%" % (name, util * 100))
                    resets.append(reset)
            procs = []
            if reasons:
                until = max(resets) + MARGIN
                if until <= now:
                    until = now + UNKNOWN_RESET_WAIT
                self.blocked_until = max(self.blocked_until, until)
                procs = list(self.procs)
                self.killed.update(p.pid for p in procs)
            self._save()
            with open(os.path.join(os.path.dirname(self.state_path), "usage.log"), "a") as fh:
                fh.write("%s %s overage=%s status=%s\n" % (
                    _when(now), " ".join("%s=%.2f" % (k, v[0]) for k, v in sorted(self.windows.items())),
                    bool(info.get("isUsingOverage")), info.get("status")))
        if reasons:
            self.log("USAGE GUARD: %s. Stopping %d running call(s); resuming after %s." % (
                "; ".join(reasons), len(procs), _when(self.blocked_until)))
            for proc in procs:
                _kill(proc)
        return bool(reasons)

    def wait_until_clear(self):
        """Block until no window is near its limit and any pause has passed."""
        announced = None
        while True:
            now = time.time()
            with self.lock:
                until = self.blocked_until
                for name, (util, reset) in self.windows.items():
                    if util >= LAUNCH_AT and reset > now:
                        until = max(until, reset + MARGIN)
            if until <= now:
                return
            if announced != until:
                self.log("USAGE GUARD: paused until %s, when plan usage resets." % _when(until))
                announced = until
            time.sleep(min(until - now, 300))


def _kill(proc):
    """Stop a call and everything it started (its shell commands run in its process group)."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        proc.wait(timeout=10)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
