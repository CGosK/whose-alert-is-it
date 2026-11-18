"""Fail if anything that would leak local or private details is tracked by git.

Usage: python3 scripts/check_clean.py            # files at HEAD
       python3 scripts/check_clean.py --history  # every blob in every commit
Identities (the hostname) are read at runtime, never written into the repo. Unreadable files fail.
"""
import re
import socket
import subprocess
import sys

HOST = socket.gethostname().split(".")[0]
PATTERNS = {
    "home path": re.compile(r"/Users/\w+|/home/(?!runner\b)\w+"),
    "temp path": re.compile(r"/private/tmp/|/var/folders/"),
    "username": re.compile(r"chrgraham", re.I),
    "hostname": re.compile(r"%s|MacBook-(Pro|Air)[\w-]*" % re.escape(HOST), re.I),
    "host logs": re.compile(r"DiagnosticReports/(?!<redacted>)[^\s\"\\]+|(?<!<redacted>)\.(diag|ips)\b"),
    "private link": re.compile(r"claude\.ai/(code/)?artifact/[\w-]+"),
    "email": re.compile(r"[\w.+-]+@(?!acme\.dev\b|example\.com\b|users\.noreply\.github\.com\b|anthropic\.com\b)[\w-]+\.[\w.]+"),
    "api key": re.compile(r"sk-ant-[\w-]{10,}|sk-[A-Za-z0-9]{20,}"),
    "usage or billing": re.compile(r"total_cost_usd|\"usage\"\s*:|costUSD|model_usage_since_last_result|costBasis|"
                                   r"\"(input|output|cacheRead(Input)?|cacheCreation(Input)?)Tokens\""),
}
ALLOWED = {"scripts/check_clean.py"}
# The scrubbers name the usage fields and host patterns they remove.
ALLOWED_HITS = {("harness/run.py", "usage or billing"), ("harness/run.py", "host logs"),
                ("scripts/rescrub_runs.py", "usage or billing"), ("scripts/rescrub_runs.py", "host logs")}


def scan(path, text):
    problems = 0
    for label, pattern in PATTERNS.items():
        hits = sorted(set(m.group(0) for m in pattern.finditer(text)))
        if hits and (path, label) not in ALLOWED_HITS:
            problems += 1
            print("%s: %s: %s" % (path, label, ", ".join(hits[:5])))
    return problems


def head_files():
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    for path in out.split("\0"):
        if path and path not in ALLOWED:
            try:
                with open(path, encoding="utf-8") as fh:
                    yield path, path, fh.read()
            except UnicodeDecodeError:
                yield path, path, None
            except OSError:
                continue


def history_blobs():
    out = subprocess.run(["git", "rev-list", "--objects", "--all"], capture_output=True, text=True, check=True).stdout
    seen = set()
    for line in out.splitlines():
        sha, _, path = line.partition(" ")
        if not path or path in ALLOWED or sha in seen:
            continue
        if subprocess.run(["git", "cat-file", "-t", sha], capture_output=True, text=True).stdout.strip() != "blob":
            continue
        seen.add(sha)
        data = subprocess.run(["git", "cat-file", "-p", sha], capture_output=True).stdout
        try:
            yield path, "%s@%s" % (path, sha[:8]), data.decode("utf-8")
        except UnicodeDecodeError:
            yield path, "%s@%s" % (path, sha[:8]), None


def main():
    history = "--history" in sys.argv
    problems = 0
    for path, label, text in (history_blobs() if history else head_files()):
        if text is None:
            problems += 1
            print("%s: unreadable (fails closed)" % label)
            continue
        for _ in range(scan(path, text)):
            problems += 1
        if problems and history:
            pass
    print("clean" if not problems else "%d problems" % problems)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
