import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.extraction_prompt import CATEGORIES, build_extraction_prompt, format_transcript_for_prompt
from backend.models import TranscriptSegment


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_transcript.json"


def _fixture_segments() -> list[TranscriptSegment]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as file:
        return [TranscriptSegment.model_validate(segment) for segment in json.load(file)]


def test_prompt_contains_density_skip_and_json_rules():
    prompt = build_extraction_prompt(
        transcript=_fixture_segments(),
        listener_profile="ML-curious software engineer",
        known_terms=["backpropagation", " GPU "],
    )

    assert "one useful term per 3-5 minutes" in prompt.user
    assert "Skip terms the speaker clearly defines or explains nearby" in prompt.user
    assert "Return JSON only" in prompt.user
    assert "Do not include timestamps" in prompt.user
    assert "- backpropagation" in prompt.user
    assert "- gpu" in prompt.user


def test_prompt_lists_all_allowed_categories():
    prompt = build_extraction_prompt(transcript=_fixture_segments())

    for category in CATEGORIES:
        assert category in prompt.user


def test_transcript_format_uses_timestamps_and_collapses_whitespace():
    transcript = [
        TranscriptSegment(start=65.2, duration=4, text="LoRA   adapters\nreduce trainable weights."),
        TranscriptSegment(start=3661, duration=2, text="An hour mark appears."),
    ]

    formatted = format_transcript_for_prompt(transcript)

    assert "[01:05] LoRA adapters reduce trainable weights." in formatted
    assert "[01:01:01] An hour mark appears." in formatted


def test_prompt_rejects_empty_transcript():
    with pytest.raises(ValueError, match="transcript"):
        build_extraction_prompt([])


def test_offline_prompt_cli_renders_fixture_prompt():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.offline_prompt",
            str(FIXTURE_PATH),
            "--known-term",
            "LoRA",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "SYSTEM:" in result.stdout
    assert "USER:" in result.stdout
    assert "Return JSON only" in result.stdout
    assert "- lora" in result.stdout
