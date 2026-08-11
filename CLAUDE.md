# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

TakeMeter — a text classifier for r/soccer posts/comments into three labels
(`analysis`, `hot_take`, `reaction`), comparing a zero-shot LLM baseline
(Groq/Llama) against a fine-tuned DistilBERT model. See [planning.md](planning.md)
for the full rationale behind the label definitions, the hard
`analysis`/`hot_take` boundary rule, data collection plan, and evaluation
targets (macro-F1 ≥ 0.75 target, ≥ 0.65 floor) — read it before touching
labels, the classification prompt, or eval metrics.

## Commands

Setup:
```
pip install -r requirements.txt
```

Data collection (either path writes to `data/raw_posts.csv`):
```
python scripts/scrape_reddit.py        # live pull via old.reddit.com JSON endpoints
python scripts/parse_reddit_json.py    # parses manually-saved JSON in data/raw/ instead
```

Training/evaluation happens in
[Copy_of_ai201_project3_takemeter_starter_clean.ipynb](Copy_of_ai201_project3_takemeter_starter_clean.ipynb),
designed to run on Google Colab (uses `google.colab.files.upload()` and
`google.colab.userdata` for the Groq API key) rather than locally. There is
no CLI training entrypoint — the notebook is the pipeline.

## Architecture

**Data pipeline:** `scripts/scrape_reddit.py` pulls posts + top-level comments
from `old.reddit.com/r/soccer/*.json` (no auth needed, just a User-Agent) →
`data/raw_posts.csv` (columns: `text`, `label`, label filled in by hand).
`scripts/parse_reddit_json.py` is the offline alternative: it walks
manually-saved listing/comment JSON in `data/raw/` (including nested comment
replies) into the same CSV shape. Comments, not post titles, are the primary
source of `analysis`/`hot_take` signal — titles skew toward `reaction`.

**Notebook pipeline** (sequential, each stage depends on the last):
1. `LABEL_MAP` (`analysis`=0, `hot_take`=1, `reaction`=2) — the single source
   of truth for label↔id mapping, reused by both the DistilBERT head and the
   Groq label-parsing logic.
2. Load labeled CSV → stratified 70/15/15 train/val/test split
   (`random_state=42`) → tokenize with `distilbert-base-uncased`
   (`max_length=256`).
3. Fine-tune `AutoModelForSequenceClassification` via HF `Trainer`
   (3 epochs, `lr=2e-5`, batch size 16/32, `load_best_model_at_end` on
   accuracy) → evaluate on the test split → confusion matrix.
4. Independently, zero-shot baseline via Groq (`llama-3.3-70b-versatile`,
   `temperature=0`) using `SYSTEM_PROMPT`, whose category definitions must
   stay in sync with `planning.md` §2–3 and `LABEL_MAP`. Response parsing
   matches longest label names first to avoid substring collisions.
5. Baseline vs. fine-tuned accuracy are compared and written to
   `evaluation_results.json` alongside `confusion_matrix.png` — both are
   meant to be committed and referenced in the README write-up.

**Key invariant:** label names in `LABEL_MAP`, the Groq `SYSTEM_PROMPT`, and
`planning.md` §2–3 must all agree — changing one without the others will
silently break either training or baseline parsing.
