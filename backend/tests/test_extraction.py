import pytest
from types import SimpleNamespace

from backend.extraction import (
    InvalidModelResponseError,
    build_extraction_metadata,
    extract_response_text,
    extract_terms,
    parse_model_terms,
)


VALID_MODEL_JSON = """
[
  {
    "term": "LoRA",
    "expansion": "Low-Rank Adaptation",
    "one_liner": "A lightweight way to fine tune a large AI model.",
    "deeper": "LoRA trains small adapter matrices instead of changing every model weight. That lowers memory use during fine tuning.",
    "quote": "LoRA, which stands for Low-Rank Adaptation",
    "category": "ml_research"
  }
]
"""


def test_parse_model_terms_accepts_valid_json_array():
    terms = parse_model_terms(VALID_MODEL_JSON)

    assert len(terms) == 1
    assert terms[0].term == "LoRA"
    assert terms[0].category == "ml_research"


def test_parse_model_terms_rejects_invalid_json():
    with pytest.raises(InvalidModelResponseError, match="valid JSON"):
        parse_model_terms("not json")


def test_parse_model_terms_rejects_non_array_json():
    with pytest.raises(InvalidModelResponseError, match="JSON array"):
        parse_model_terms('{"terms": []}')


def test_parse_model_terms_rejects_schema_mismatch():
    with pytest.raises(InvalidModelResponseError, match="extraction schema"):
        parse_model_terms('[{"term": "LoRA", "category": "not_allowed"}]')


def test_extract_response_text_prefers_output_text():
    response = SimpleNamespace(output_text="[]", output=[])

    assert extract_response_text(response) == "[]"


def test_extract_response_text_falls_back_to_output_parts():
    response = SimpleNamespace(
        output_text=None,
        output=[
            SimpleNamespace(
                content=[
                    SimpleNamespace(text="["),
                    SimpleNamespace(text="]"),
                ]
            )
        ],
    )

    assert extract_response_text(response) == "[]"


def test_extract_terms_resolves_timestamps_from_model_quotes(monkeypatch):
    from backend import extraction
    from backend.models import ExtractRequest

    monkeypatch.setattr(extraction, "_required_env", lambda name: "test-value")
    monkeypatch.setattr(extraction, "call_openai", lambda prompt, api_key, model: VALID_MODEL_JSON)

    response = extract_terms(
        ExtractRequest(
            video_id="abc123",
            video_url="https://www.youtube.com/watch?v=abc123",
            transcript=[
                {
                    "start": 65.2,
                    "duration": 5,
                    "text": "A common approach is LoRA, which stands for Low-Rank Adaptation.",
                }
            ],
        )
    )

    assert response.terms[0].timestamp == 65.2
    assert response.terms[0].confidence == 0.98
    assert response.metadata is not None
    assert response.metadata.model == "test-value"
    assert response.metadata.cache_status == "miss"
    assert response.metadata.term_count == 1
    assert response.metadata.timestamp_coverage == 1
    assert response.metadata.low_confidence_rate == 0
    assert response.metadata.extraction_latency_ms is not None


def test_build_extraction_metadata_counts_sync_and_low_confidence_terms():
    from backend.models import TermCard, TranscriptSegment

    metadata = build_extraction_metadata(
        model="test-model",
        transcript=[
            TranscriptSegment(start=0, duration=10, text="First segment."),
            TranscriptSegment(start=25, duration=5, text="Last segment."),
        ],
        terms=[
            TermCard(
                id="synced",
                term="Synced",
                one_liner="A synced term.",
                deeper="A synced term with confidence.",
                quote="Synced",
                category="other",
                timestamp=1,
                confidence=0.9,
            ),
            TermCard(
                id="unsynced",
                term="Unsynced",
                one_liner="An unsynced term.",
                deeper="An unsynced term with low confidence.",
                quote="Missing",
                category="other",
                timestamp=None,
                confidence=0.1,
            ),
        ],
        latency_ms=123,
    )

    assert metadata.model == "test-model"
    assert metadata.transcript_segments == 2
    assert metadata.transcript_duration_seconds == 30
    assert metadata.term_count == 2
    assert metadata.timestamped_term_count == 1
    assert metadata.low_confidence_term_count == 1
    assert metadata.timestamp_coverage == 0.5
    assert metadata.low_confidence_rate == 0.5
    assert metadata.extraction_latency_ms == 123
