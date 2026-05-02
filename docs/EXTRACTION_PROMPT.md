# Footnote Extraction Prompt

Phase 2 adds the offline prompt builder in `backend/extraction_prompt.py`. It does not call the OpenAI API yet; that wiring belongs to Phase 3.

## Prompt Contract

The prompt asks the model to act as a glossary editor for technical long-form audio. It receives:

- Timestamped transcript text rendered as `[MM:SS] transcript segment`.
- A listener profile.
- A normalized list of known terms to skip.

The model must return JSON only: a single array of objects with exactly these keys:

```json
[
  {
    "term": "LoRA",
    "expansion": "Low-Rank Adaptation",
    "one_liner": "A lightweight way to fine tune a large AI model.",
    "deeper": "LoRA trains small adapter matrices instead of changing every model weight. In this conversation, it matters because it lowers memory use during fine tuning.",
    "quote": "LoRA, which stands for Low-Rank Adaptation",
    "category": "ml_research"
  }
]
```

Allowed categories:

- `ml_research`
- `biology`
- `neuroscience`
- `physics`
- `economics`
- `medicine`
- `cs_systems`
- `math_stats`
- `named_entity`
- `other`

## Selection Rules

- Target roughly one useful term per 3-5 minutes of content.
- Prefer precision over coverage.
- Include jargon, acronyms, named entities, methods, technical concepts, and field-specific phrases that matter for local comprehension.
- Skip terms the speaker clearly defines or explains nearby.
- Skip terms from the listener profile and known-term list.
- Skip generic words, vague topics, and terms that are interesting but not needed to follow the episode.

## Timestamp Strategy

The model must not return timestamps. It returns a short exact transcript quote instead. Later phases resolve timestamps by matching `quote` against the transcript, which should be more reliable than trusting model-generated seconds.

## Offline Harness

Render the prompt against the sample fixture:

```powershell
python -m backend.offline_prompt backend\tests\fixtures\sample_transcript.json --known-term LoRA
```

Useful variations:

```powershell
python -m backend.offline_prompt backend\tests\fixtures\sample_transcript.json --listener-profile "Curious product manager" --known-term backpropagation
```

## Tuning Notes

If the model returns too many obvious terms, strengthen the listener profile or add examples of terms to skip. If it misses important jargon, loosen the density target or name the domain in the listener profile. If explanations are too shallow, require the `deeper` field to connect the term to the surrounding transcript context rather than giving a dictionary definition.
