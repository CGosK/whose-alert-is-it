"""Write the batch's eval tasks and review summary to out/."""
import json
import os


def write(date, tasks, review_result):
    os.makedirs("out", exist_ok=True)
    with open(os.path.join("out", "evals-%s.jsonl" % date), "w") as fh:
        for task in tasks:
            fh.write(json.dumps(task) + "\n")
    with open(os.path.join("out", "review-%s.json" % date), "w") as fh:
        json.dump(review_result, fh, indent=2)
