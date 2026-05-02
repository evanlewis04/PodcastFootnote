# Footnote

Footnote is a local MVP for timestamp-synced glossary cards on YouTube videos. This first implementation includes the FastAPI backend skeleton, local JSON storage, and a loadable Chrome extension shell.

## Local Backend Setup

```powershell
cd "C:\Users\aruba\OneDrive\Documents\111 Projects\Podcast Footnote Project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy backend\.env.example backend\.env
uvicorn backend.app:app --reload --port 8000
```

Before uncached extraction works, set both values in `backend\.env`:

```powershell
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_id
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{
  "ok": true
}
```

## Chrome Extension Setup

1. Open Chrome and go to `chrome://extensions`.
2. Enable Developer mode.
3. Select Load unpacked.
4. Choose the `extension` folder in this repository.
5. Open a YouTube watch page.

The extension injects a Footnote sidebar on YouTube watch pages. It collects captions, sends the transcript to the local backend, renders glossary cards, highlights the active card during playback, and lets you dismiss terms you already know.

## Run Tests

```powershell
pytest
```

## Render the Offline Extraction Prompt

Phase 2 includes a prompt-only harness for validating prompt shape against a saved transcript fixture. This does not call the OpenAI API.

```powershell
python -m backend.offline_prompt backend\tests\fixtures\sample_transcript.json --known-term LoRA
```

## Extract Terms

`POST /extract` is cache-first. If `data\cache\{video_id}.json` exists, the backend returns that file without calling OpenAI. On a cache miss, it uses the Responses API, validates the model JSON, writes the cache, and returns the saved response.

Returned terms are post-processed before caching. Footnote deduplicates obvious repeats, matches each model-provided `quote` against the transcript, assigns the earliest matching segment timestamp, and keeps unmatched terms with a low confidence score and no timestamp.

```powershell
$body = @{
  video_id = "abc123"
  video_url = "https://www.youtube.com/watch?v=abc123"
  transcript = @(
    @{ start = 0; duration = 4.2; text = "The model uses LoRA adapters during fine tuning." }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod http://localhost:8000/extract -Method Post -ContentType "application/json" -Body $body
```

## MVP Testing Loop

Use [docs\TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) to evaluate real videos for precision, recall, definition quality, sync quality, cache behavior, and known-term dismissal.
