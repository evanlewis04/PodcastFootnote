from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .models import ExtractResponse, KnownTerm


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("FOOTNOTE_DATA_DIR", REPO_ROOT / "data"))
CACHE_DIR = DATA_DIR / "cache"
KNOWN_TERMS_FILE = DATA_DIR / "known_terms.json"

_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def normalize_term(term: str) -> str:
    return " ".join(term.strip().casefold().split())


def get_cache(video_id: str) -> ExtractResponse | None:
    cache_path = _cache_path(video_id)
    if not cache_path.exists():
        return None

    with cache_path.open("r", encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)

    response = ExtractResponse.model_validate(data)
    return response.model_copy(update={"cached": True})


def set_cache(video_id: str, response: ExtractResponse) -> ExtractResponse:
    cache_path = _cache_path(video_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    response_to_store = response.model_copy(update={"video_id": video_id, "cached": False})
    _write_json(cache_path, response_to_store.model_dump(mode="json"))
    return response_to_store


def load_known_terms() -> list[KnownTerm]:
    _ensure_known_terms_file()
    with KNOWN_TERMS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{KNOWN_TERMS_FILE} must contain a JSON list")

    return [KnownTerm.model_validate(item) for item in data]


def add_known_term(term: str, source_video_id: str | None = None) -> KnownTerm:
    normalized = normalize_term(term)
    if not normalized:
        raise ValueError("term must not be blank")

    known_terms = load_known_terms()
    for known_term in known_terms:
        if known_term.normalized == normalized:
            return known_term

    known_term = KnownTerm(term=term.strip(), normalized=normalized, source_video_id=source_video_id)
    known_terms.append(known_term)
    _write_json(KNOWN_TERMS_FILE, [item.model_dump(mode="json") for item in known_terms])
    return known_term


def _cache_path(video_id: str) -> Path:
    video_id = video_id.strip()
    if not _VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("video_id may only contain letters, numbers, underscores, and hyphens")
    return CACHE_DIR / f"{video_id}.json"


def _ensure_known_terms_file() -> None:
    KNOWN_TERMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not KNOWN_TERMS_FILE.exists():
        _write_json(KNOWN_TERMS_FILE, [])


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")
