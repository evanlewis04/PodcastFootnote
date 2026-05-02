from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extraction_prompt import build_extraction_prompt
from .models import TranscriptSegment


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Footnote extraction prompt for a saved transcript.")
    parser.add_argument("transcript_json", type=Path, help="Path to a JSON array of transcript segments.")
    parser.add_argument("--listener-profile", default="", help="Optional listener profile override.")
    parser.add_argument("--known-term", action="append", default=[], help="Known term to exclude. Can be repeated.")
    args = parser.parse_args()

    transcript = _load_transcript(args.transcript_json)
    prompt = build_extraction_prompt(
        transcript=transcript,
        listener_profile=args.listener_profile,
        known_terms=args.known_term,
    )

    print("SYSTEM:")
    print(prompt.system)
    print()
    print("USER:")
    print(prompt.user)


def _load_transcript(path: Path) -> list[TranscriptSegment]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("transcript fixture must contain a JSON array")
    return [TranscriptSegment.model_validate(segment) for segment in data]


if __name__ == "__main__":
    main()
