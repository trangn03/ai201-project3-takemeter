# TakeMeter — Project Planning

## 1. Community

**Chosen community: r/soccer**

r/soccer is one of the largest sport-specific subreddits (2M+ members) and has an
unusually high ratio of *discourse* to *content-sharing* for a sports subreddit — a
huge share of the top posts and comment threads are people arguing about referee
decisions, tactics, transfers, and manager competence rather than just posting
highlight clips. That argument culture is exactly what makes it a good fit for a
text classification task: on any given match thread you'll find (a) someone doing
genuine tactical breakdown, (b) someone firing off an exaggerated, unfalsifiable
opinion for reaction/points, and (c) someone just reacting emotionally to what
happened. Those three registers are visually indistinguishable in a feed but read
very differently once you actually parse the sentence — which is the whole point of
building a classifier instead of just eyeballing it.

The name "TakeMeter" reflects the goal: given a post/comment from r/soccer, score how
much of it is a "take" (a hot take) versus analysis versus a simple emotional
reaction, so a community tool could, e.g., surface analysis-heavy threads or flag
low-effort hot-take spam.

## 2. Labels

Three labels, chosen because they map to distinct *communicative intents* rather than
topic or sentiment (which would overlap too much to be useful):

- **`analysis`** — A post that makes a substantive, reasoned claim about football
  (tactics, player performance, transfer logic, refereeing rules) that is grounded in
  specific evidence from the match/situation and could in principle be argued with on
  the merits.
  - *"Their back three kept getting dragged out of position every time Saka drifted
    inside, which is exactly why the second goal came down that channel."*
  - *"He's been playing as a false 9 all season, not a true striker, which is why his
    shot numbers look low relative to his xG contribution."*

- **`hot_take`** — A post that states a strong, provocative, or exaggerated opinion
  designed to draw a reaction, often absolute ("worst ever," "should be sacked,"
  "corrupt"), rarely tied to specific evidence, and often not really falsifiable.
  - *"Huge dropoff in viewership in Monaco."*
  - *"Trump's corruption is finally benefiting the country for once."*

- **`reaction`** — A post that expresses an emotional response to an event (joy,
  shock, sadness, hype) or simply reports/describes what happened, without arguing a
  claim or trying to provoke one.
  - *"Messi crying after receiving his runners-up medal."*
  - *"Argentina [3] - 0 Algeria — Lionel Messi 76' hat-trick."*

(A 4th label like `off_topic`/`meta` was considered for non-football tangents, e.g.
politics-flavored comments, but was dropped — those posts still function as hot takes
or reactions in this community, so adding a topic-based label would double-count
intent that the 3 labels already capture.)

## 3. Hard edge cases

The genuinely ambiguous boundary is **`analysis` vs. `hot_take`**: both are
opinionated, both can be phrased confidently, and the difference is really about
*how grounded* the claim is, not tone. A sentence like *"Ten Hag should have been
sacked after that tactical setup"* looks like a take, but if it were followed by a
specific tactical justification it would slide into analysis. The concrete failure
mode: a short comment that states a strong verdict ("he's finished") with just enough
context to sound like it's reasoned, but no actual specific evidence backing it up.

Handling rule adopted during annotation: default to `hot_take` unless the post cites
at least one concrete, checkable detail (a specific event, stat, tactical pattern, or
rule) as the basis for its claim. Absolutist/emotionally loaded language ("never,"
"worst," "disgrace," "corrupt") is a strong signal toward `hot_take` even when
evidence is present, because the *intent* reads as provocation rather than reasoned
argument. This rule was written down after the first ~30 rows of labeling, once it
became clear "confidence of tone" was not a reliable signal and "presence of specific
evidence" was.

The secondary ambiguous boundary is **`hot_take` vs. `reaction`** for short comments
without punctuation or context (e.g., sarcasm). When a comment could be read as either
genuine reaction or a sarcastic dig, it's labeled `hot_take` if it's clearly aimed at
being provocative/argumentative in context (thread-level judgment), and `reaction`
only when the emotional read is unambiguous on its own.

## 4. Data collection plan

**Source:** r/soccer, pulled via Reddit's public read-only JSON endpoints (see
[scrape_reddit.py](scrape_reddit.py) / [parse_reddit_json.py](parse_reddit_json.py)),
covering top posts from the last year plus their top-level (and nested) comments.
Comments are the primary source of labeled text in practice — post titles are mostly
just captions ("Messi scores winner") and skew heavily toward `reaction`, while the
real analysis/hot-take discourse lives in the comment threads.

- Target: ~200 examples total to start (already collected, see `raw_posts.csv`),
  aiming for a rough floor of **40+ examples per label** before training, ideally
  closer to balanced (e.g., 60/70/70).
- Current actual distribution after the first labeling pass of 200 rows:
  `reaction` = 90, `hot_take` = 81, `analysis` = 29 — `analysis` is underrepresented
  as expected, since deep tactical breakdowns are rarer than one-liner
  reactions/takes in a fast-scrolling comment section.

**If a label is underrepresented after 200 examples (as `analysis` currently is):**
1. Re-scrape with a source shift rather than pulling more of the same top/year
   listing — target known analysis-heavy contexts specifically: post-match "Match
   Thread" / "Post Match Thread" stickies (which get longer, more considered
   comments once the emotional peak has passed), and threads tagged `[Analysis]` in
   the title, which r/soccer users self-tag.
2. Pull comments sorted by "top" within individual threads rather than only
   top-level comments from top posts — analysis tends to be a reply that gets
   upvoted after the initial reaction wave, not the first comment.
3. Raise `MIN_LENGTH`/note that analysis comments tend to be longer; a cheap
   pre-filter (e.g., only keep comments over ~150 characters for a supplementary
   pull) increases the hit rate of analysis-labeled text before manual review, since
   one-liners are almost never analysis.
4. As a last resort, accept a moderately imbalanced training set and address it at
   training time (class weighting, oversampling) rather than forcing collection to
   hit an artificial balance — better to have real, correctly-labeled imbalance than
   to pad the `analysis` class with borderline `hot_take`s just to hit a count.

## 5. Evaluation metrics

Accuracy alone is misleading here because the classes are naturally imbalanced
(reaction/hot_take are more common than analysis) — a model that never predicts
`analysis` could still post a deceptively high accuracy while being useless for the
one label a real tool would care most about (surfacing genuine analysis).

Metrics to use:
- **Macro-averaged F1** as the headline metric — averages F1 across the three
  labels unweighted, so poor performance on the rare `analysis` class can't be
  hidden by strong performance on `reaction`/`hot_take`. This is the single number
  used to compare model versions.
- **Per-class precision and recall**, not just F1, because the two failure modes
  matter differently by label:
  - For `analysis`: recall matters most — missing genuine analysis (false negative)
    defeats the point of a tool meant to surface it; some `hot_take` bleed-in
    (lower precision) is a more acceptable cost.
  - For `hot_take`: precision matters most, especially if this ever gates something
    like a "hide hot takes" filter — mislabeling real analysis as a hot take and
    hiding it is a worse user experience than an occasional missed hot take.
- **Confusion matrix**, to explicitly check whether errors concentrate on the known
  hard boundary (analysis ↔ hot_take) versus being spread evenly — if errors
  concentrate there, that confirms the boundary defined in §3 is where model
  improvement effort (more training examples, clearer labeling) should go.

## 6. Definition of success

**Genuinely useful (target):** macro-F1 ≥ 0.75, with `analysis` recall ≥ 0.65 and
`hot_take` precision ≥ 0.80. At this level, the classifier catches most real
analysis (so a "show me the analysis threads" feature would actually surface
signal) and rarely mislabels analysis as a hot take (so a hot-take filter doesn't
accidentally bury thoughtful comments) — the two failure modes that would make the
tool actively annoying rather than just imperfect.

**"Good enough" for deployment as a real community tool (floor):** macro-F1 ≥ 0.65,
with no single class's F1 below 0.5. Below this, disagreement between the model and
a human reader would happen often enough (roughly one in three) that users would
stop trusting the label, and for a lightweight community tool (not a
safety-critical system) that trust is the whole value proposition — a classifier
that's "usually right but you have to double check" isn't worth the UI it lives in.
Given that `analysis`↔`hot_take` is a genuinely hard boundary even for a human
annotator (see §3), 100% agreement isn't the bar; the bar is being right *more
consistently than a quick human skim*, which the "good enough" floor is calibrated to
approximate.

## 7. AI tool plan

This project has no code-generation surface worth planning around — the notebook
pipeline is fixed and small. The places an AI tool actually changes the outcome are
upstream and downstream of the model: sharpening the label definitions before
annotation, optionally speeding up annotation itself, and reading the error list
after evaluation. Each use is scoped below, including how it'll be disclosed.

**1. Label stress-testing (before annotation).**
Before doing the full 200-row labeling pass, prompt an LLM (e.g. Claude or the
Groq model already wired up for the baseline) with the label definitions and edge
case rules from §2–3 and ask it to generate 5–10 short r/soccer-style posts/comments
deliberately written to sit on the `analysis`/`hot_take` boundary (and a couple on
the `hot_take`/`reaction` boundary). Manually label the generated set using the
rules in §3 alone, with no peeking at how the model intended them.

- **Pass/fail check:** if any generated example can't be cleanly assigned using the
  §3 rules — i.e. the "cite at least one concrete, checkable detail" test and the
  absolutist-language signal don't resolve it — that's a sign the rule, not the
  example, is underspecified. Tighten §3 and re-run the stress test before starting
  real annotation, not after.
- This is a one-time calibration step; it doesn't feed training data directly (the
  generated examples are synthetic and not representative of real r/soccer phrasing
  frequency), so they're discarded after the definitions are finalized, not added to
  `raw_posts.csv`.

**2. Annotation assistance (during labeling).**
Decision: **no LLM pre-labeling for this pass.** With only ~200 rows and a known
hard boundary (§3) that the annotation rule itself was only discovered by hand after
~30 rows, pre-labeling risks anchoring the human labeler toward the model's
`analysis`/`hot_take` split rather than applying the §3 rule independently — the
exact failure mode this dataset is most exposed to, since that boundary is also the
one the zero-shot Groq baseline is separately being evaluated on (using it to
pre-label would contaminate the baseline/fine-tuned comparison in §5).

- If this decision is revisited for a larger future pull (e.g. under §4's
  expansion plan), any pre-labeling would use the same Groq zero-shot setup as the
  baseline, and pre-labeled rows would be marked with an extra `prelabeled_by`
  column in the raw CSV (value = model name, blank for hand-first labels) so the
  AI-usage disclosure can state exactly which rows were touched by a model before a
  human saw them.

**3. Failure analysis (after evaluation).**
Once the fine-tuned model's test-set predictions are in, pull the misclassified rows
(predicted label ≠ true label, from the confusion matrix in §5) into a list of
`(text, true_label, predicted_label)` tuples and give that list to an LLM asking it
to cluster the errors and describe any patterns — e.g. "these are short comments
with no evidence markers," "these all contain absolutist language but were labeled
`analysis`," or "these are sarcasm cases where tone flips the intended read."

- **What to look for:** whether errors cluster on the known hard boundary
  (`analysis`↔`hot_take`, per §3) versus being spread evenly, and whether any
  cluster suggests a labeling error (mislabeled ground truth) rather than a model
  error.
- **Verification:** treat the AI's clustering as a hypothesis, not a finding —
  manually re-read every example in a claimed cluster against the §3 rule before
  citing it in the write-up. Only patterns that hold up under that manual re-read
  (and, for suspected ground-truth errors, get corrected in the CSV with a note) go
  into the final evaluation report; the rest are discarded as false patterns fitted
  to a small error set.
