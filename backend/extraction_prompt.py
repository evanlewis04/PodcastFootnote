from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import TranscriptSegment
from .storage import normalize_term


CATEGORIES = (
    "ml_research",
    "biology",
    "neuroscience",
    "physics",
    "economics",
    "medicine",
    "cs_systems",
    "math_stats",
    "named_entity",
    "other",
)

DEFAULT_LISTENER_PROFILE = (
    "Technically curious generalist. Comfortable with common software, internet, "
    "and high-school science vocabulary, but not necessarily with specialist jargon."
)


@dataclass(frozen=True)
class ExtractionPrompt:
    system: str
    user: str


def build_extraction_prompt(
    transcript: Iterable[TranscriptSegment],
    listener_profile: str = "",
    known_terms: Iterable[str] | None = None,
) -> ExtractionPrompt:
    segments = list(transcript)
    if not segments:
        raise ValueError("transcript must contain at least one segment")

    profile = listener_profile.strip() or DEFAULT_LISTENER_PROFILE
    known_terms_text = _format_known_terms(known_terms or [])
    transcript_text = format_transcript_for_prompt(segments)
    duration_minutes = max(_estimate_duration_minutes(segments), 1)
    target_min = max(round(duration_minutes / 5), 1)
    target_max = max(round(duration_minutes / 3), target_min)

    system = (
        "You are Footnote, an expert glossary editor for technical long-form audio. "
        "Your job is to identify only the terms that would materially improve a listener's "
        "understanding at the moment they are heard."
    )

    user = f"""Analyze this timestamped transcript and return glossary terms for the listener.

Target density:
- Aim for roughly one useful term per 3-5 minutes of content.
- For this transcript, return about {target_min}-{target_max} terms unless the content clearly needs fewer.
- Prefer precision over coverage; a shorter high-signal list is better than filler.

Listener profile:
{profile}

Known terms to skip:
{known_terms_text}

Selection rules:
- Include jargon, acronyms, named entities, methods, technical concepts, and field-specific phrases that are important for local comprehension.
- Skip terms the speaker clearly defines or explains nearby.
- Skip obvious terms for the listener profile and all known terms listed above.
- Skip generic words, vague topics, clickbait phrasing, and terms that are merely interesting but not needed to follow the discussion.
- Do not invent facts beyond what is needed for a concise explanation.

Output rules:
- Return JSON only: a single array with no Markdown, prose, or code fence.
- Each array item must contain exactly these keys:
  "term", "expansion", "one_liner", "deeper", "quote", "category"
- Use null for "expansion" when there is no standard expansion.
- "one_liner" must be one plain-language sentence.
- "deeper" must be 2-3 sentences that explain the term in this transcript's context.
- "quote" must be a short exact phrase copied from the transcript where the term appears.
- Do not include timestamps; Footnote resolves timestamps later by quote matching.
- "category" must be one of: {", ".join(CATEGORIES)}.

Transcript:
{transcript_text}
"""

    return ExtractionPrompt(system=system, user=user)


def format_transcript_for_prompt(transcript: Iterable[TranscriptSegment]) -> str:
    return "\n".join(_format_segment(segment) for segment in transcript)


def _format_segment(segment: TranscriptSegment) -> str:
    timestamp = _format_timestamp(segment.start)
    text = " ".join(segment.text.split())
    return f"[{timestamp}] {text}"


def _format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _estimate_duration_minutes(transcript: list[TranscriptSegment]) -> float:
    last_segment = max(transcript, key=lambda segment: segment.start + segment.duration)
    return (last_segment.start + last_segment.duration) / 60


def _format_known_terms(known_terms: Iterable[str]) -> str:
    normalized_terms = sorted({normalize_term(term) for term in known_terms if normalize_term(term)})
    if not normalized_terms:
        return "- None"
    return "\n".join(f"- {term}" for term in normalized_terms)
