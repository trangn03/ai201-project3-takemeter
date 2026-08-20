# TakeMeter

TakeMeter is a text classification project designed to categorize posts and comments from the **r/soccer** subreddit based on their communicative intent. By distinguishing between thoughtful analysis, provocative hot takes, and simple emotional reactions, TakeMeter aims to help surface high-quality discourse and filter out low-effort spam in community forums.

For detailed project planning, rationale, and label definitions, please refer to the [planning.md](planning.md) document.

## 🏷️ Labels

The classifier categorizes text into one of three labels:

1. **`analysis`**: A substantive, reasoned claim about football (tactics, player performance, etc.) grounded in specific evidence.
2. **`hot_take`**: A strong, provocative, or exaggerated opinion designed to draw a reaction, often absolute and rarely tied to specific evidence.
3. **`reaction`**: An emotional response to an event or a simple report/description of what happened, without arguing a claim.

### Edge Cases
The hardest boundary is between `analysis` and `hot_take`. Our labeling rule defaults to `hot_take` unless the post cites at least one concrete, checkable detail (e.g., a specific event, stat, or tactical pattern). Absolutist or emotionally loaded language often pushes a comment toward `hot_take`.

## 📊 Data Collection

Data was scraped from the r/soccer subreddit using Reddit's public JSON endpoints, focusing on match threads and top comment threads where most of the relevant discourse lives. The dataset contains 433 labeled examples, with the following distribution:
- `hot_take`: 218 (50.3%)
- `reaction`: 131 (30.3%)
- `analysis`: 84 (19.4%)

## 🧠 Model Training

We fine-tuned a **DistilBERT** (`distilbert-base-uncased`) model for 3 epochs using HuggingFace's `Trainer` API. 
The dataset was split into 70% training, 15% validation, and 15% test sets.

We compared the fine-tuned model's performance against a zero-shot baseline using **OpenAI** (`openai/gpt-oss-120b`) prompted with our specific label definitions.

## 📈 Evaluation Results

**Test Set Size:** 65 examples

- **Zero-shot Baseline (OpenAI) Accuracy:** 60.00%
- **Fine-Tuned Model Accuracy:** 53.85%

**Fine-Tuned Model Per-Class Metrics:**
```text
              precision    recall  f1-score   support

    analysis       0.00      0.00      0.00        13
    hot_take       0.53      0.94      0.68        33
    reaction       0.57      0.21      0.31        19

   macro avg       0.37      0.38      0.33        65
```

The fine-tuned model underperformed the zero-shot baseline. The macro-averaged F1 score was 0.33, largely because the model completely failed to predict the minority `analysis` class (0 recall/precision), defaulting to the majority `hot_take` class.

### Confusion Matrix

| True \ Predicted | Analysis | Hot Take | Reaction |
|------------------|----------|----------|----------|
| **Analysis**     | 0        | 12       | 1        |
| **Hot Take**     | 0        | 31       | 2        |
| **Reaction**     | 0        | 15       | 4        |

*(Supplementary Copy)*
![Confusion Matrix](confusion_matrix.png)

## 🔍 Error Analysis

Here is a deep dive into 3 specific wrong predictions from the test set to understand where the fine-tuned model struggles:

**1. Tone Confusion: All Caps / Emotion**
> **Text:** "I SAID JOHNNY, YOU'RE KILLING ME HERE GIANNI, YOU GOTTA DO SOMETHING GIANNII"
> **True:** `reaction` | **Predicted:** `hot_take` (Confidence: 0.55)
*Analysis:* The model seems to interpret the aggressive, all-caps format as a provocative `hot_take`. It fails to recognize that this is merely a dramatic, emotional `reaction` to a game event, demonstrating that tone (which can be loud in both classes) is tricking the model.

**2. Missing Tactical Context for Analysis**
> **Text:** "The definition of a system player but even now, he can’t get a start with City. He should be hitting his prime but the opposite is happening, he is regressing towards it"
> **True:** `analysis` | **Predicted:** `hot_take` (Confidence: 0.60)
*Analysis:* The user is making an analytical point about a player's lack of playing time at Manchester City and their career trajectory. However, the use of phrases like "definition of a system player" and "regressing" sound like typical hot-take buzzwords. The model misses the checkable evidence ("can't get a start with City") and assumes it's a hot take.

**3. Non-Tactical Analysis Misclassification**
> **Text:** "This specific controversy is probably going to draw a lot more attention to the game in American media and cause more Americans to tune in out of curiosity (or more people to hate-watch or something)."
> **True:** `analysis` | **Predicted:** `hot_take` (Confidence: 0.54)
*Analysis:* This is a reasoned claim about media impact and viewership, which fits our definition of `analysis` even if it isn't about on-pitch tactics. The model likely predicted `hot_take` because it lacks traditional football statistics/events, highlighting the difficulty the model has in identifying reasoned arguments outside of strict tactical discussions. 

**Conclusion:** The fine-tuned DistilBERT model struggles with class imbalance and relies too heavily on superficial tone markers (like strong language or all-caps) rather than actual substantive evidence. Future iterations require oversampling the `analysis` class or using a larger base model.