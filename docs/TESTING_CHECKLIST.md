# Footnote Manual Evaluation Checklist

Use this checklist after the backend and extension are running locally. Pick videos you know well enough to judge whether the glossary cards are genuinely helpful.

## Setup

1. Start the backend with `uvicorn backend.app:app --reload --port 8000`.
2. Load the unpacked `extension` folder in Chrome.
3. Open a YouTube watch page with captions.
4. Wait for the Footnote sidebar to show extracted cards.
5. Re-run the same video and confirm the second load comes from cache.

## Evaluation Table

| Video URL | Manual desired terms | Extracted terms | Useful extracted terms | Missed desired terms | Precision | Recall | Definition quality notes | Prompt tuning notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |

## Scoring

Precision:

```text
useful extracted terms / all extracted terms
```

Recall:

```text
manual desired terms found / all manual desired terms
```

Definition quality:

```text
accurate, right depth, context-aware, no hallucinated claims
```

## MVP Targets

- Precision above 80%.
- Recall above 70%.
- Zero hallucinated definitions.
- Quotes resolve to the right timestamp for most cards.
- Dismissed known terms stay hidden on future videos.

## Tuning Loop

False positives: add clearer skip rules, strengthen the listener profile, or raise the bar for local comprehension value.

False negatives: loosen the density target, add domain hints to the listener profile, or tell the prompt to prefer specific concept types.

Too shallow: require the `deeper` field to explain why the term matters in this transcript.

Too advanced: ask for simpler analogies in `one_liner` and fewer prerequisite-heavy details in `deeper`.

Bad sync: inspect the returned `quote` field. The quote should be a short exact phrase copied from the transcript, not a paraphrase.
