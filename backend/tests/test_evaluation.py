from pathlib import Path

from backend.evaluation import evaluate_response, load_evaluation_case, load_extract_response


FIXTURES = Path(__file__).parent / "fixtures"


def test_evaluate_response_scores_precision_recall_and_timestamp_coverage():
    response = load_extract_response(FIXTURES / "sample_extract_response.json")
    evaluation_case = load_evaluation_case(FIXTURES / "evaluation_case.json")

    report = evaluate_response(response, evaluation_case)

    assert report.video_id == "sample-ai-video"
    assert report.true_positives == 2
    assert report.false_positives == 1
    assert report.false_negatives == 1
    assert report.precision == 0.6667
    assert report.recall == 0.6667
    assert report.timestamp_coverage == 0.6667
    assert report.low_confidence_rate == 0.3333
    assert report.matches[0].timestamp_delta_seconds == 0
    assert report.false_positive_terms == ["dropout"]


def test_evaluate_response_matches_expected_aliases_against_expansions():
    response = load_extract_response(FIXTURES / "sample_extract_response.json")
    evaluation_case = load_evaluation_case(FIXTURES / "evaluation_case.json")
    evaluation_case.expected_terms[0].term = "Low-Rank Adaptation"
    evaluation_case.expected_terms[0].aliases = []

    report = evaluate_response(response, evaluation_case)

    assert report.matches[0].matched_term == "LoRA"
