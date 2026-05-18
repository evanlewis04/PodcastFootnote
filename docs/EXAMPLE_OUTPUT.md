# Example Output

This fixture shows the kind of structured knowledge object Footnote creates from a transcript. The important product detail is that the model selects the term and writes the explanation, while the backend validates the schema and resolves the timestamp from an exact transcript quote.

## Extract Response

```json
{
  "video_id": "sample-ai-video",
  "cached": false,
  "metadata": {
    "prompt_version": "glossary-v1",
    "model": "fixture-model",
    "cache_status": "fixture",
    "transcript_segments": 5,
    "transcript_duration_seconds": 614.4,
    "term_count": 3,
    "timestamped_term_count": 2,
    "low_confidence_term_count": 1,
    "timestamp_coverage": 0.6667,
    "low_confidence_rate": 0.3333,
    "extraction_latency_ms": 420
  },
  "terms": [
    {
      "term": "LoRA",
      "expansion": "Low-Rank Adaptation",
      "one_liner": "A lightweight way to fine tune a large AI model.",
      "quote": "LoRA, which stands for Low-Rank Adaptation",
      "timestamp": 65.2,
      "confidence": 0.98
    },
    {
      "term": "retrieval augmented generation",
      "one_liner": "A method that gives a model retrieved context before it answers.",
      "quote": "compares retrieval augmented generation",
      "timestamp": 342.3,
      "confidence": 0.98
    }
  ]
}
```

## Evaluation Report

```json
{
  "video_id": "sample-ai-video",
  "expected_count": 3,
  "extracted_count": 3,
  "true_positives": 2,
  "false_positives": 1,
  "false_negatives": 1,
  "precision": 0.6667,
  "recall": 0.6667,
  "f1": 0.6667,
  "timestamp_coverage": 0.6667,
  "low_confidence_rate": 0.3333,
  "false_positive_terms": ["dropout"]
}
```

This example intentionally includes one false positive and one missed term so the evaluation output demonstrates how prompt and post-processing quality can be inspected.
