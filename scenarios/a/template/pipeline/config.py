"""Load the review config (config/review.cfg)."""
import configparser
import os
from collections import namedtuple

Config = namedtuple("Config", "findings_dir severity_threshold no_notify ping page")


def _list(value):
    return [x.strip() for x in value.split(",") if x.strip()]


def load(path=None):
    path = path or os.environ.get("REVIEW_CONFIG", os.path.join("config", "review.cfg"))
    parser = configparser.ConfigParser()
    if not parser.read(path):
        raise FileNotFoundError(path)
    review = parser["review"]
    recipients = parser["recipients"]
    return Config(
        findings_dir=review.get("findings_dir"),
        severity_threshold=review.getint("severity_threshold"),
        no_notify=review.getboolean("no_notify", fallback=False),
        ping=_list(recipients.get("ping", "")),
        page=_list(recipients.get("page", "")),
    )
