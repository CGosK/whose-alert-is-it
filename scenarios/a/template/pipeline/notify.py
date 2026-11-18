"""Send review alerts to the @@TEAM@@.

Alerts are written to the outgoing spool. The notify relay picks up the spool every minute and
delivers each message: pings by email and Slack, pages through the pager.
"""
import json
import os
import time
import uuid


def _spool_dir():
    return os.environ.get("NOTIFY_SPOOL", os.path.join("spool", "outgoing"))


def send(finding, cfg):
    if cfg.no_notify:
        return 0
    os.makedirs(_spool_dir(), exist_ok=True)
    sent = 0
    for channel, recipients in (("ping", cfg.ping), ("page", cfg.page)):
        for to in recipients:
            message = {
                "channel": channel,
                "to": to,
                "subject": "[@@SUBJECT_TAG@@ sev%d] %s" % (finding["severity"], finding["summary"]),
                "finding": finding,
                "queued_at": time.time(),
            }
            with open(os.path.join(_spool_dir(), uuid.uuid4().hex + ".json"), "w") as fh:
                json.dump(message, fh)
            sent += 1
    return sent
