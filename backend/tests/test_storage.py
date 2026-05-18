import json

import pytest

from backend import storage
from backend.models import ExtractResponse, ExtractionMetadata, TermCard


@pytest.fixture()
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(storage, "KNOWN_TERMS_FILE", tmp_path / "known_terms.json")
    return tmp_path


def _response(video_id: str = "abc123") -> ExtractResponse:
    return ExtractResponse(
        video_id=video_id,
        metadata=ExtractionMetadata(
            model="test-model",
            cache_status="miss",
            transcript_segments=1,
            transcript_duration_seconds=127.65,
            term_count=1,
            timestamped_term_count=1,
            low_confidence_term_count=0,
            timestamp_coverage=1,
            low_confidence_rate=0,
            extraction_latency_ms=250,
        ),
        terms=[
            TermCard(
                id="lora",
                term="LoRA",
                expansion="Low-Rank Adaptation",
                one_liner="A lightweight way to fine tune a large AI model.",
                deeper="LoRA trains small adapter matrices instead of changing every model weight.",
                quote="uses LoRA adapters during fine tuning",
                category="ml_research",
                timestamp=123.45,
                confidence=0.86,
            )
        ],
    )


def test_cache_round_trip_marks_loaded_response_cached(isolated_data_dir):
    stored_response = storage.set_cache("abc123", _response())

    assert stored_response.cached is False
    assert (isolated_data_dir / "cache" / "abc123.json").exists()

    loaded_response = storage.get_cache("abc123")

    assert loaded_response is not None
    assert loaded_response.cached is True
    assert loaded_response.video_id == "abc123"
    assert loaded_response.terms[0].term == "LoRA"
    assert loaded_response.metadata is not None
    assert loaded_response.metadata.cache_status == "hit"
    assert loaded_response.metadata.model == "test-model"


def test_cache_miss_returns_none(isolated_data_dir):
    assert storage.get_cache("missing_video") is None


def test_cache_rejects_unsafe_video_id(isolated_data_dir):
    with pytest.raises(ValueError, match="video_id"):
        storage.set_cache("../escape", _response(video_id="../escape"))


def test_known_terms_file_is_created_when_missing(isolated_data_dir):
    known_terms = storage.load_known_terms()

    assert known_terms == []
    assert (isolated_data_dir / "known_terms.json").exists()

    with (isolated_data_dir / "known_terms.json").open("r", encoding="utf-8") as file:
        assert json.load(file) == []


def test_add_known_term_persists_and_dedupes_by_normalized_term(isolated_data_dir):
    first = storage.add_known_term(" LoRA ", source_video_id="abc123")
    second = storage.add_known_term("lora", source_video_id="other")
    known_terms = storage.load_known_terms()

    assert first == second
    assert len(known_terms) == 1
    assert known_terms[0].term == "LoRA"
    assert known_terms[0].normalized == "lora"
    assert known_terms[0].source_video_id == "abc123"
