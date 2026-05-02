from backend.models import RawExtractedTerm, TranscriptSegment
from backend.timestamping import dedupe_terms, normalize_term, normalize_text, resolve_timestamps


def _term(term: str, quote: str, expansion: str | None = None) -> RawExtractedTerm:
    return RawExtractedTerm(
        term=term,
        expansion=expansion,
        one_liner=f"{term} in one sentence.",
        deeper=f"{term} gets a contextual explanation.",
        quote=quote,
        category="ml_research",
    )


def _segment(start: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, duration=4, text=text)


def test_normalize_text_is_case_and_whitespace_insensitive():
    assert normalize_text(" LoRA\tAdapters\nFine-Tuning! ") == "lora adapters fine tuning"


def test_normalize_term_collapses_case_and_whitespace():
    assert normalize_term("  Low   Rank ADAPTATION ") == "low rank adaptation"


def test_exact_quote_match_resolves_to_segment_start():
    cards = resolve_timestamps(
        [_term("LoRA", "uses LoRA adapters during fine tuning")],
        [_segment(123.45, "The model uses LoRA adapters during fine tuning.")],
    )

    assert cards[0].timestamp == 123.45
    assert cards[0].confidence == 0.98


def test_normalized_quote_match_handles_case_and_whitespace_variants():
    cards = resolve_timestamps(
        [_term("LoRA", "USES   lora adapters during fine tuning")],
        [_segment(12, "The model uses LoRA adapters during fine tuning.")],
    )

    assert cards[0].timestamp == 12
    assert cards[0].confidence == 0.92


def test_adjacent_segment_quote_match_uses_earliest_segment_start():
    cards = resolve_timestamps(
        [_term("RAG", "retrieval augmented generation with standard supervised fine tuning")],
        [
            _segment(30, "Later, the team compares retrieval augmented"),
            _segment(34, "generation with standard supervised fine tuning."),
        ],
    )

    assert cards[0].timestamp == 30
    assert cards[0].confidence == 0.9


def test_dedupe_terms_collapses_acronym_and_expansion_duplicates():
    raw_terms = [
        _term("RAG", "RAG helps", expansion="Retrieval Augmented Generation"),
        _term("Retrieval Augmented Generation", "retrieval augmented generation helps"),
    ]

    deduped = dedupe_terms(raw_terms)

    assert len(deduped) == 1
    assert deduped[0].term == "RAG"


def test_unmatched_quote_is_retained_unsynced_with_low_confidence():
    cards = resolve_timestamps(
        [_term("Quantization", "lower precision weights")],
        [_segment(0, "No matching phrase appears here.")],
    )

    assert cards[0].timestamp is None
    assert cards[0].confidence == 0.1


def test_resolved_cards_are_sorted_by_timestamp_with_unsynced_last():
    cards = resolve_timestamps(
        [
            _term("Unmatched", "missing quote"),
            _term("Later", "later quote"),
            _term("Earlier", "earlier quote"),
        ],
        [
            _segment(50, "This segment has a later quote."),
            _segment(10, "This segment has an earlier quote."),
        ],
    )

    assert [card.term for card in cards] == ["Earlier", "Later", "Unmatched"]
