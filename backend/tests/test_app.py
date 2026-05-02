from fastapi.testclient import TestClient

from backend import app as app_module
from backend.extraction import ExtractionConfigError, InvalidModelResponseError, ModelCallError
from backend.models import ExtractResponse, TermCard


client = TestClient(app_module.app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_cors_allows_youtube_origin():
    response = client.options(
        "/extract",
        headers={
            "Origin": "https://www.youtube.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://www.youtube.com"


def test_read_cache_returns_cached_response(monkeypatch):
    cached_response = ExtractResponse(video_id="abc123", cached=True, terms=[])
    monkeypatch.setattr(app_module, "get_cache", lambda video_id: cached_response)

    response = client.get("/cache/abc123")

    assert response.status_code == 200
    assert response.json()["cached"] is True


def test_read_cache_returns_404_for_cache_miss(monkeypatch):
    monkeypatch.setattr(app_module, "get_cache", lambda video_id: None)

    response = client.get("/cache/abc123")

    assert response.status_code == 404


def test_extract_returns_cached_response(monkeypatch):
    cached_response = ExtractResponse(
        video_id="abc123",
        cached=True,
        terms=[
            TermCard(
                id="lora",
                term="LoRA",
                one_liner="A lightweight way to fine tune a large AI model.",
                deeper="LoRA trains small adapter matrices instead of changing every model weight.",
                quote="uses LoRA adapters",
                category="ml_research",
                timestamp=12.3,
                confidence=0.9,
            )
        ],
    )

    def fake_get_cache(video_id: str):
        assert video_id == "abc123"
        return cached_response

    monkeypatch.setattr(app_module, "get_cache", fake_get_cache)

    response = client.post(
        "/extract",
        json={
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "title": "Demo",
            "listener_profile": "Technically curious generalist",
            "known_terms": [],
            "transcript": [{"start": 0, "duration": 4.2, "text": "The model uses LoRA adapters."}],
        },
    )

    assert response.status_code == 200
    assert response.json()["cached"] is True
    assert response.json()["terms"][0]["term"] == "LoRA"


def test_extract_cache_miss_returns_config_error_when_env_is_missing(monkeypatch):
    monkeypatch.setattr(app_module, "get_cache", lambda video_id: None)
    monkeypatch.setattr(
        app_module,
        "extract_terms",
        lambda request: (_ for _ in ()).throw(ExtractionConfigError("OPENAI_API_KEY is required")),
    )

    response = client.post(
        "/extract",
        json={
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "transcript": [{"start": 0, "duration": 4.2, "text": "The model uses LoRA adapters."}],
        },
    )

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_extract_cache_miss_calls_model_and_writes_cache(monkeypatch):
    response_to_cache = ExtractResponse(
        video_id="abc123",
        terms=[
            TermCard(
                id="rag",
                term="retrieval augmented generation",
                one_liner="A way to add retrieved source material to a model prompt.",
                deeper="The system looks up relevant documents before answering. In this transcript, it is being compared with supervised fine tuning.",
                quote="compares retrieval augmented generation",
                category="ml_research",
            )
        ],
    )
    cached_calls = []

    monkeypatch.setattr(app_module, "get_cache", lambda video_id: None)
    monkeypatch.setattr(app_module, "extract_terms", lambda request: response_to_cache)

    def fake_set_cache(video_id: str, response: ExtractResponse) -> ExtractResponse:
        cached_calls.append((video_id, response))
        return response.model_copy(update={"cached": False})

    monkeypatch.setattr(app_module, "set_cache", fake_set_cache)

    response = client.post(
        "/extract",
        json={
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "transcript": [{"start": 0, "duration": 4.2, "text": "They compare retrieval augmented generation."}],
        },
    )

    assert response.status_code == 200
    assert response.json()["cached"] is False
    assert response.json()["terms"][0]["term"] == "retrieval augmented generation"
    assert cached_calls[0][0] == "abc123"


def test_extract_invalid_model_json_returns_bad_gateway(monkeypatch):
    monkeypatch.setattr(app_module, "get_cache", lambda video_id: None)
    monkeypatch.setattr(
        app_module,
        "extract_terms",
        lambda request: (_ for _ in ()).throw(InvalidModelResponseError("Model response was not valid JSON.")),
    )

    response = client.post(
        "/extract",
        json={
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "transcript": [{"start": 0, "duration": 4.2, "text": "The model uses LoRA adapters."}],
        },
    )

    assert response.status_code == 502
    assert "valid JSON" in response.json()["detail"]


def test_extract_model_failure_returns_bad_gateway(monkeypatch):
    monkeypatch.setattr(app_module, "get_cache", lambda video_id: None)
    monkeypatch.setattr(
        app_module,
        "extract_terms",
        lambda request: (_ for _ in ()).throw(ModelCallError("OpenAI request failed")),
    )

    response = client.post(
        "/extract",
        json={
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "transcript": [{"start": 0, "duration": 4.2, "text": "The model uses LoRA adapters."}],
        },
    )

    assert response.status_code == 502
    assert "OpenAI request failed" in response.json()["detail"]


def test_extract_invalid_payload_returns_validation_error():
    response = client.post(
        "/extract",
        json={
            "video_id": "abc123",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "transcript": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "transcript"


def test_extract_rejects_unsafe_video_id():
    response = client.post(
        "/extract",
        json={
            "video_id": "../escape",
            "video_url": "https://www.youtube.com/watch?v=abc123",
            "transcript": [{"start": 0, "duration": 4.2, "text": "The model uses LoRA adapters."}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "video_id"
