from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from .extraction_prompt import ExtractionPrompt, build_extraction_prompt
from .models import ExtractRequest, ExtractResponse, RawExtractedTerm
from .timestamping import resolve_timestamps


class ExtractionError(Exception):
    """Base exception for extraction failures."""


class ExtractionConfigError(ExtractionError):
    """Raised when local extraction configuration is missing."""


class ModelCallError(ExtractionError):
    """Raised when the OpenAI API request fails."""


class InvalidModelResponseError(ExtractionError):
    """Raised when the model response cannot be parsed or validated."""


def extract_terms(request: ExtractRequest) -> ExtractResponse:
    api_key = _required_env("OPENAI_API_KEY")
    model = _required_env("OPENAI_MODEL")
    prompt = build_extraction_prompt(
        transcript=request.transcript,
        listener_profile=request.listener_profile,
        known_terms=request.known_terms,
    )
    content = call_openai(prompt=prompt, api_key=api_key, model=model)
    raw_terms = parse_model_terms(content)
    terms = resolve_timestamps(raw_terms, request.transcript)
    return ExtractResponse(video_id=request.video_id, terms=terms, cached=False)


def call_openai(prompt: ExtractionPrompt, api_key: str, model: str) -> str:
    try:
        from openai import OpenAI, OpenAIError
    except ImportError as error:
        raise ExtractionConfigError("The openai package is not installed. Run pip install -r backend/requirements.txt.") from error

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=model,
            instructions=prompt.system,
            input=prompt.user,
            store=False,
        )
    except OpenAIError as error:
        raise ModelCallError(f"OpenAI request failed: {error}") from error

    content = extract_response_text(response)
    if not content:
        raise InvalidModelResponseError("OpenAI response did not include message content.")
    return content


def extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return ""

    text_parts: list[str] = []
    for item in output:
        content = getattr(item, "content", None)
        if not isinstance(content, list):
            continue
        for part in content:
            text = getattr(part, "text", None)
            if isinstance(text, str):
                text_parts.append(text)

    return "".join(text_parts)


def parse_model_terms(content: str) -> list[RawExtractedTerm]:
    try:
        data = json.loads(content)
    except JSONDecodeError as error:
        raise InvalidModelResponseError("Model response was not valid JSON.") from error

    if not isinstance(data, list):
        raise InvalidModelResponseError("Model response must be a JSON array.")

    try:
        return [RawExtractedTerm.model_validate(item) for item in data]
    except ValidationError as error:
        raise InvalidModelResponseError(f"Model response did not match the extraction schema: {error}") from error


def _required_env(name: str) -> str:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    value = os.getenv(name, "").strip()
    if not value:
        raise ExtractionConfigError(f"{name} is required for uncached extraction.")
    return value
