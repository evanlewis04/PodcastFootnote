# Next Session Handoff

## Current Status

- Reviewed `Project Overview.pdf`.
- Created `IMPLEMENTATION_PLAN.md` with the full MVP roadmap.
- Updated the plan to use the OpenAI API instead of Anthropic throughout.
- Removed temporary PDF-rendering artifacts and added `.gitignore` entries so they are not reintroduced.

No application code has been implemented yet. The project is ready to begin Phase 0 and Phase 1 from the implementation plan.

## Key Decisions

- Build a local-only MVP first: Chrome extension plus FastAPI backend.
- Use YouTube only for the MVP.
- Process the full transcript upfront instead of streaming.
- Keep API keys in the local backend only.
- Use `OPENAI_API_KEY` and `OPENAI_MODEL` environment variables.
- Cache extraction results by YouTube video ID.
- Start with JSON files instead of a database.

## First Implementation Target

Begin with backend and extension scaffolding:

- Create `backend/` and `extension/`.
- Add FastAPI `/health`.
- Add Pydantic models for transcript segments, extract requests, term cards, responses, and known terms.
- Add local JSON cache and known-term storage.
- Add focused tests for storage.
- Add a minimal Manifest V3 extension shell.
- Do not implement LLM calls or YouTube transcript scraping in the first pass.

## Suggested Next Prompt

```text
Start implementing the Footnote MVP from IMPLEMENTATION_PLAN.md.

Begin with Phase 0 and Phase 1 only:
- Create backend and extension folders.
- Add FastAPI /health endpoint.
- Add Pydantic models.
- Add local JSON cache and known-term storage.
- Add requirements.txt and .env.example using OPENAI_API_KEY and OPENAI_MODEL.
- Add tests for storage.
- Add a minimal Manifest V3 extension shell.
- Do not implement LLM calls or YouTube transcript scraping yet.

After implementation, run the backend tests and show the exact commands needed to start the server and load the extension.
```

## Files To Read First

1. `IMPLEMENTATION_PLAN.md`
2. `NEXT_SESSION.md`
3. `Project Overview.pdf` only if more product context is needed
