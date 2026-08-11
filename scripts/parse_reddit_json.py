"""
Combines locally-saved Reddit JSON pages into data/raw_posts.csv for annotation.

Setup:
    1. In your browser (logged into reddit.com), visit:
         https://www.reddit.com/r/soccer/top.json?limit=100&t=year
       Save the page as posts_1.json in data/raw/.
       To get more posts, note the "after" value near the bottom of the
       JSON, revisit with &after=<value>, and save as posts_2.json, etc.

    2. For individual threads, visit:
         https://www.reddit.com/r/soccer/comments/<post_id>.json
       and save each as comments_<post_id>.json (same data/raw/ folder).
       Comments carry most of the actual discourse
       (analysis/hot takes/reactions) — post titles alone are often just
       video/photo captions.

Usage:
    python parse_reddit_json.py
"""

import csv
import glob
import json
from pathlib import Path

MIN_LENGTH = 20
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_CSV = DATA_DIR / "raw_posts.csv"


def extract_from_listing(data):
    texts = []
    for child in data["data"]["children"]:
        post = child["data"]
        text = post.get("title", "")
        if post.get("selftext"):
            text += " " + post["selftext"]
        texts.append(text.strip())
    return texts


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


def main():
    rows = []
    seen = set()

    for path in sorted(glob.glob(str(RAW_DIR / "posts_*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for text in extract_from_listing(data):
            if len(text) >= MIN_LENGTH and text not in seen:
                seen.add(text)
                rows.append({"text": text, "label": ""})

    for path in sorted(glob.glob(str(RAW_DIR / "comments_*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for text in extract_from_comments(data):
            if len(text) >= MIN_LENGTH and text not in seen:
                seen.add(text)
                rows.append({"text": text, "label": ""})

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} examples to {OUTPUT_CSV}")
    print("Next: open the CSV and fill in the 'label' column for each row.")


if __name__ == "__main__":
    main()
