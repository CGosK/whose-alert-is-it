"""Nightly evalgen job: turn user feedback into eval tasks, review the run, then publish."""
import argparse

from pipeline import generate, publish, review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="batch date, YYYY-MM-DD")
    args = parser.parse_args()

    tasks = generate.build_tasks(args.date)
    # Publishing is gated on the review finishing.
    result = review.run(args.date)
    publish.write(args.date, tasks, result)
    print("published %d tasks for %s (%d findings)" % (len(tasks), args.date, result["findings"]))


if __name__ == "__main__":
    main()
