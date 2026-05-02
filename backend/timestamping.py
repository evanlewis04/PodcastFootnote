from __future__ import annotations

import re
from collections.abc import Iterable

from .models import RawExtractedTerm, TermCard, TranscriptSegment
from .storage import normalize_term as normalize_term


_WORD_PATTERN = re.compile(r"\w+")


def normalize_text(text: str) -> str:
    return " ".join(_WORD_PATTERN.findall(text.casefold()))


def dedupe_terms(raw_terms: Iterable[RawExtractedTerm]) -> list[RawExtractedTerm]:
    deduped: list[RawExtractedTerm] = []
    seen: set[str] = set()

    for raw_term in raw_terms:
        keys = _dedupe_keys(raw_term)
        if seen.intersection(keys):
            continue
        seen.update(keys)
        deduped.append(raw_term)

    return deduped


def resolve_timestamps(
    raw_terms: Iterable[RawExtractedTerm],
    transcript_segments: Iterable[TranscriptSegment],
) -> list[TermCard]:
    segments = sorted(transcript_segments, key=lambda segment: segment.start)
    cards: list[TermCard] = []

    for raw_term in dedupe_terms(raw_terms):
        match = _find_quote_match(raw_term.quote, segments)
        cards.append(
            TermCard(
                id=_term_id(raw_term.term),
                term=raw_term.term,
                expansion=raw_term.expansion,
                one_liner=raw_term.one_liner,
                deeper=raw_term.deeper,
                quote=raw_term.quote,
                category=raw_term.category,
                timestamp=match.timestamp,
                confidence=match.confidence,
            )
        )

    return sorted(cards, key=lambda card: (card.timestamp is None, card.timestamp or 0, card.term.casefold()))


class _QuoteMatch:
    def __init__(self, timestamp: float | None, confidence: float) -> None:
        self.timestamp = timestamp
        self.confidence = confidence


def _find_quote_match(quote: str, segments: list[TranscriptSegment]) -> _QuoteMatch:
    normalized_quote = normalize_text(quote)
    if not normalized_quote:
        return _QuoteMatch(timestamp=None, confidence=0.1)

    for segment in segments:
        if quote in segment.text:
            return _QuoteMatch(timestamp=segment.start, confidence=0.98)

    for segment in segments:
        if normalized_quote in normalize_text(segment.text):
            return _QuoteMatch(timestamp=segment.start, confidence=0.92)

    for window_size in range(2, min(4, len(segments)) + 1):
        for index in range(0, len(segments) - window_size + 1):
            window = segments[index : index + window_size]
            combined_text = " ".join(segment.text for segment in window)
            if quote in combined_text:
                return _QuoteMatch(timestamp=window[0].start, confidence=0.9)
            if normalized_quote in normalize_text(combined_text):
                return _QuoteMatch(timestamp=window[0].start, confidence=0.84)

    return _QuoteMatch(timestamp=None, confidence=0.1)


def _dedupe_keys(raw_term: RawExtractedTerm) -> set[str]:
    keys = {_compact_key(raw_term.term)}
    if raw_term.expansion:
        keys.add(_compact_key(raw_term.expansion))

    acronym = _acronym(raw_term.expansion)
    if acronym:
        keys.add(_compact_key(acronym))

    return {key for key in keys if key}


def _acronym(text: str | None) -> str:
    if not text:
        return ""
    words = _WORD_PATTERN.findall(text)
    if len(words) < 2:
        return ""
    return "".join(word[0] for word in words)


def _compact_key(text: str) -> str:
    return "".join(_WORD_PATTERN.findall(text.casefold()))


def _term_id(term: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_term(term)).strip("-")
    return slug or "term"
