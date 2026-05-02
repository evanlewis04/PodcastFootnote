from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .extraction import ExtractionConfigError, InvalidModelResponseError, ModelCallError, extract_terms
from .models import ExtractRequest, ExtractResponse
from .storage import get_cache, set_cache


app = FastAPI(title="Footnote API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.youtube.com", "https://m.youtube.com"],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/cache/{video_id}", response_model=ExtractResponse)
def read_cache(video_id: str) -> ExtractResponse:
    try:
        cached_response = get_cache(video_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if cached_response is None:
        raise HTTPException(status_code=404, detail="No cached extraction found for this video_id.")

    return cached_response


@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest) -> ExtractResponse:
    cached_response = get_cache(request.video_id)
    if cached_response is not None:
        return cached_response

    try:
        response = extract_terms(request)
    except ExtractionConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except InvalidModelResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ModelCallError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return set_cache(request.video_id, response)
