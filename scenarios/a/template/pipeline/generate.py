"""Build eval tasks from a day's user feedback."""
import json
import os


def build_tasks(date):
    path = os.path.join("data", "feedback", date + ".jsonl")
    tasks = []
    with open(path) as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                continue
            item = json.loads(line)
            tasks.append({
                "id": "%s-%03d" % (date, i),
                "prompt": item["user_message"],
                "rubric": "Response should avoid: " + item["complaint"],
            })
    return tasks
