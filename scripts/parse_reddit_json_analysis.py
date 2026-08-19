"""
Supplementary offline pull targeting analysis-heavy sources, per planning.md
§4's fallback plan for the underrepresented `analysis` label.

Unlike parse_reddit_json.py (which regenerates raw_posts.csv from scratch),
this script only APPENDS new rows — it never touches or overwrites rows
already in the CSV, so existing hand-labels are preserved.

Setup:
    1. In your browser (logged into reddit.com), find threads to target:
         - "Post Match Thread" / "Match Thread" stickies (longer, more
           considered comments once the emotional peak has passed)
         - Threads with "[Analysis]" in the title (self-tagged by r/soccer
           users)
       For each thread, sort comments by "top" (?sort=top), then visit:
         https://www.reddit.com/r/soccer/comments/<post_id>.json?sort=top
       and save the page as comments_<post_id>.json in data/raw/analysis/.

    2. Run this script. It only keeps comments >= MIN_LENGTH chars (raised
       from the usual 20, since analysis comments run long and one-liners
       are almost never analysis) and skips anything already present in
       raw_posts.csv.

Usage:
    python parse_reddit_json_analysis.py
"""

import csv
import glob
import json
from pathlib import Path

MIN_LENGTH = 150
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "analysis"
OUTPUT_CSV = DATA_DIR / "raw_posts.csv"


def extract_from_comments(data):
    texts = []
    comment_listing = data[1]["data"]["children"]

    def walk(children):
        for child in children:
            if child["kind"] != "t1":
                continue
            body = child["data"].get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                texts.append(body.strip())
            replies = child["data"].get("replies")
            if isinstance(replies, dict):
                walk(replies["data"]["children"])

    walk(comment_listing)
    return texts


def load_existing(csv_path):
    rows, seen = [], set()
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
                seen.add(row["text"])
    return rows, seen


def main():
    rows, seen = load_existing(OUTPUT_CSV)
    start_count = len(rows)
    new_count = 0

    paths = sorted(glob.glob(str(RAW_DIR / "comments_*.json")))
    if not paths:
        print(f"No comments_*.json files found in {RAW_DIR}")
        print("Save some there first (see this script's docstring), then re-run.")
        return

    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for text in extract_from_comments(data):
            if len(text) >= MIN_LENGTH and text not in seen:
                seen.add(text)
                rows.append({"text": text, "label": ""})
                new_count += 1

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Appended {new_count} new examples ({start_count} -> {len(rows)} total) to {OUTPUT_CSV}")
    print("Next: open the CSV, fill in 'label' for the new (blank-label) rows using the §3 rule.")


if __name__ == "__main__":
    main()
