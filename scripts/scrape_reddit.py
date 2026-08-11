"""
Pulls posts/comments from a subreddit into a CSV for manual annotation.

Uses Reddit's public read-only JSON endpoints (e.g. reddit.com/r/soccer/top.json) —
no API app registration or credentials required, just a descriptive User-Agent.
Only suitable for small, occasional, non-commercial pulls like this one.

Setup:
    pip install -r requirements.txt

Usage:
    python scrape_reddit.py
"""

import csv
import time
from pathlib import Path

import requests

SUBREDDIT = "soccer"        # ← change to your chosen community
NUM_POSTS = 200              # top-level posts to pull (paginated, 100 per request)
NUM_COMMENTS_PER_POST = 5    # top-level comments to pull per post
MIN_LENGTH = 20              # skip text shorter than this (chars)
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "data" / "raw_posts.csv"
USER_AGENT = "takemeter-scraper/0.1 by u/ttnn_"


def fetch_top_posts(subreddit, limit):
    headers = {"User-Agent": USER_AGENT}
    posts = []
    after = None
    while len(posts) < limit:
        params = {"limit": min(100, limit - len(posts)), "t": "year"}
        if after:
            params["after"] = after
        resp = requests.get(
            f"https://old.reddit.com/r/{subreddit}/top.json",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        posts.extend(child["data"] for child in data["children"])
        after = data.get("after")
        if not after:
            break
        time.sleep(1)  # be polite, avoid rate limiting
    return posts[:limit]


def fetch_comments(subreddit, post_id, limit):
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(
        f"https://old.reddit.com/r/{subreddit}/comments/{post_id}.json",
        headers=headers,
        params={"limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    comment_listing = resp.json()[1]["data"]["children"]
    comments = []
    for child in comment_listing[:limit]:
        if child["kind"] == "t1":
            comments.append(child["data"].get("body", ""))
    return comments


def main():
    rows = []
    seen = set()

    posts = fetch_top_posts(SUBREDDIT, NUM_POSTS)
    print(f"Fetched {len(posts)} posts from r/{SUBREDDIT}")

    for i, post in enumerate(posts):
        post_text = post.get("title", "")
        if post.get("selftext"):
            post_text += " " + post["selftext"]
        post_text = post_text.strip()
        if len(post_text) >= MIN_LENGTH and post_text not in seen:
            seen.add(post_text)
            rows.append({"text": post_text, "label": ""})

        for comment_text in fetch_comments(SUBREDDIT, post["id"], NUM_COMMENTS_PER_POST):
            comment_text = comment_text.strip()
            if (
                len(comment_text) >= MIN_LENGTH
                and comment_text not in seen
                and comment_text not in ("[deleted]", "[removed]")
            ):
                seen.add(comment_text)
                rows.append({"text": comment_text, "label": ""})

        time.sleep(1)  # be polite, avoid rate limiting
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(posts)} posts processed, {len(rows)} examples so far...")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} examples to {OUTPUT_CSV}")
    print("Next: open the CSV and fill in the 'label' column for each row.")


if __name__ == "__main__":
    main()
