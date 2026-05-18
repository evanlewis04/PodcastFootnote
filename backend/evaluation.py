from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel, Field

from .models import ExtractResponse, TermCard
from .storage import normalize_term


class ExpectedTerm(BaseModel):
    term: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    expected_timestamp: float | None = Field(default=None, ge=0)


class EvaluationCase(BaseModel):
    video_id: str = Field(min_length=1)
    expected_terms: list[ExpectedTerm] = Field(default_factory=list)
    notes: str = ""


class TermMatch(BaseModel):
    expected_term: str
    matched_term: str | None = None
    status: str
    timestamp_delta_seconds: float | None = None


class EvaluationReport(BaseModel):
    video_id: str
    expected_count: int
    extracted_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    timestamp_coverage: float
    low_confidence_rate: float
    matches: list[TermMatch]
    false_positive_terms: list[str]


def evaluate_response(
    response: ExtractResponse,
    evaluation_case: EvaluationCase,
    *,
    low_confidence_threshold: float = 0.5,
) -> EvaluationReport:
    matched_card_ids: set[str] = set()
    matches: list[TermMatch] = []

    for expected in evaluation_case.expected_terms:
        card = _find_matching_card(expected, response.terms, matched_card_ids)
        if card is None:
            matches.append(TermMatch(expected_term=expected.term, status="missing"))
            continue

        matched_card_ids.add(card.id)
        matches.append(
            TermMatch(
                expected_term=expected.term,
                matched_term=card.term,
                status="matched",
                timestamp_delta_seconds=_timestamp_delta(expected.expected_timestamp, card.timestamp),
            )
        )

    true_positives = len(matched_card_ids)
    false_negatives = max(len(evaluation_case.expected_terms) - true_positives, 0)
    false_positive_cards = [card for card in response.terms if card.id not in matched_card_ids]
    precision = _safe_divide(true_positives, len(response.terms))
    recall = _safe_divide(true_positives, len(evaluation_case.expected_terms))
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    timestamped_terms = [card for card in response.terms if card.timestamp is not None]
    low_confidence_terms = [card for card in response.terms if card.confidence < low_confidence_threshold]

    return EvaluationReport(
        video_id=response.video_id,
        expected_count=len(evaluation_case.expected_terms),
        extracted_count=len(response.terms),
        true_positives=true_positives,
        false_positives=len(false_positive_cards),
        false_negatives=false_negatives,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        timestamp_coverage=round(_safe_divide(len(timestamped_terms), len(response.terms)), 4),
        low_confidence_rate=round(_safe_divide(len(low_confidence_terms), len(response.terms)), 4),
        matches=matches,
        false_positive_terms=[card.term for card in false_positive_cards],
    )


def load_evaluation_case(path: Path) -> EvaluationCase:
    with path.open("r", encoding="utf-8") as file:
        return EvaluationCase.model_validate(json.load(file))


def load_extract_response(path: Path) -> ExtractResponse:
    with path.open("r", encoding="utf-8") as file:
        return ExtractResponse.model_validate(json.load(file))


def _find_matching_card(
    expected: ExpectedTerm,
    cards: list[TermCard],
    matched_card_ids: set[str],
) -> TermCard | None:
    expected_keys = {normalize_term(expected.term)}
    expected_keys.update(normalize_term(alias) for alias in expected.aliases)
    expected_keys = {key for key in expected_keys if key}

    for card in cards:
        if card.id in matched_card_ids:
            continue
        card_keys = {normalize_term(card.term)}
        if card.expansion:
            card_keys.add(normalize_term(card.expansion))
        if expected_keys.intersection(card_keys):
            return card

    return None


def _timestamp_delta(expected: float | None, actual: float | None) -> float | None:
    if expected is None or actual is None:
        return None
    return round(abs(actual - expected), 3)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0
    return numerator / denominator


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a Footnote extraction against a labeled term set.")
    parser.add_argument("expected", type=Path, help="Path to an evaluation case JSON file.")
    parser.add_argument("actual", type=Path, help="Path to an ExtractResponse JSON file or cache file.")
    args = parser.parse_args()

    report = evaluate_response(load_extract_response(args.actual), load_evaluation_case(args.expected))
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
