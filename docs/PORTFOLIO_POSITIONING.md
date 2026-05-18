# Portfolio Positioning

## One-Line Description

Footnote is an AI-assisted comprehension layer for technical long-form video: it extracts high-signal concepts from transcripts, resolves them to playback timestamps, and turns passive media into a navigable knowledge workflow.

## Resume-Ready Description

Built a local Chrome extension and FastAPI backend that generate timestamp-synced glossary cards for YouTube videos using structured LLM extraction, transcript quote alignment, cache-first storage, known-term personalization, and an evaluation loop for precision, recall, and timestamp coverage.

## What This Project Signals

Footnote demonstrates applied AI engineering beyond a generic chat UI. The system has ingestion, prompt design, structured outputs, validation, post-processing, caching, browser workflow integration, and quality evaluation. It also shows product thinking: the feature is embedded in the moment a user needs help, rather than asking the user to leave their workflow and query a bot.

## Stronger Framing

Weak framing:

```text
AI Chrome extension that explains YouTube videos.
```

Stronger framing:

```text
Workflow-native AI system that converts long-form technical transcripts into timestamped, personalized comprehension cards with measurable extraction quality.
```

## Differentiators To Emphasize

- Converts unstructured transcript data into structured, UI-ready knowledge objects.
- Uses model output only where it adds judgment, then relies on deterministic backend logic for validation, deduplication, and timestamp alignment.
- Treats retrieval and extraction quality as measurable system behavior through labeled evaluation cases.
- Fits into an existing workflow through a browser extension, sidebar, overlay, playback sync, and known-term dismissal.
- Provides a clear path from MVP to production-style architecture: async jobs, metadata, eval history, domain profiles, and persistent knowledge stores.

## Upgrade Themes

Near-term upgrades should make the repository feel like a real applied AI system:

- Add extraction-run metadata: model, prompt version, duration, token usage, cache status, term counts, confidence distribution.
- Expand the eval set across several video domains and track metrics over time.
- Add a small run dashboard or CLI report for extraction quality and latency.
- Move from file cache to SQLite with explicit tables for videos, transcript segments, terms, known terms, and evaluation runs.
- Add background jobs for extraction and a polling API for the extension.
- Add domain profiles that change selection rules and listener assumptions.
- Add source-backed concept memory so repeated terms get consistent explanations across videos.

## Before Sharing Publicly

- Add screenshots or a short GIF from a real YouTube run.
- Label 3-5 real videos and include their evaluation reports.
- Pick one representative cached extraction and include it in the README as proof of system behavior.
