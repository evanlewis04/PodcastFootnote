# Evaluation Loop

Footnote is only useful if the cards are accurate, timely, and sparse enough to keep the video experience intact. The evaluation loop treats extraction quality as a product metric, not just a prompt tweak.

## What To Measure

| Metric | Why it matters |
| --- | --- |
| Precision | Keeps the sidebar from becoming noisy or tutorial-like. |
| Recall | Catches the terms a listener actually needs in order to follow the discussion. |
| F1 | Balances useful coverage against distraction. |
| Timestamp coverage | Shows whether cards can be synced into the workflow instead of becoming static notes. |
| Low-confidence rate | Surfaces quote-matching failures and hallucinated or paraphrased quotes. |

## Labeled Case Format

Create a JSON file with the terms a human reviewer expected the system to extract:

```json
{
  "video_id": "sample-ai-video",
  "notes": "AI systems sample episode.",
  "expected_terms": [
    {
      "term": "LoRA",
      "aliases": ["Low-Rank Adaptation"],
      "expected_timestamp": 65.2
    }
  ]
}
```

## Run Against A Cached Response

```powershell
python -m backend.evaluation backend\tests\fixtures\evaluation_case.json backend\tests\fixtures\sample_extract_response.json
```

The command prints a JSON report with precision, recall, F1, timestamp coverage, low-confidence rate, per-term matches, and false positives.

See [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md) for a short sample response and evaluation report.

## How To Use The Results

Precision failures usually mean the prompt is over-selecting general background concepts or producing terms that are interesting but not necessary at that moment.

Recall failures usually mean the listener profile, density target, or category guidance is too restrictive for the domain.

Timestamp failures usually mean the model returned a paraphrased quote. The prompt should be tightened around exact short transcript spans, or the backend should add stronger fuzzy matching before caching.

Low-confidence failures are useful debugging handles. They show which cards may be semantically plausible but cannot yet be trusted in the playback workflow.
