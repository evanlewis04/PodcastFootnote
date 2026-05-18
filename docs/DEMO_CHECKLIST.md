# Demo Checklist

Use this checklist to produce portfolio assets once the backend and extension are running locally.

## Screenshots To Capture

1. YouTube page with the Footnote sidebar visible and 3-5 glossary cards rendered.
2. Same video with the overlay enabled on top of the player.
3. A card highlighted during playback near its timestamp.
4. Browser extension loaded in `chrome://extensions` to show it is a real Chrome extension.
5. Terminal output from `pytest` showing the green test suite.
6. Terminal output from `python -m backend.evaluation ...` showing precision, recall, and timestamp coverage.

## Suggested GIF

Record a short 10-15 second clip:

1. Open a YouTube technical video.
2. Let Footnote load cached cards.
3. Seek near a timestamped term.
4. Show the active card highlight.
5. Toggle the overlay.

## Where To Put Assets

Create:

```text
docs/assets/
  footnote-sidebar.png
  footnote-overlay.png
  footnote-active-card.gif
  tests-green.png
  evaluation-report.png
```

Then add them to the README under a `Demo` section.

## Recommended README Demo Copy

```markdown
## Demo

Footnote runs as a local Chrome extension on YouTube. It extracts glossary cards from the transcript, caches the structured response, and syncs active cards to playback time.

![Footnote sidebar](docs/assets/footnote-sidebar.png)
![Footnote overlay](docs/assets/footnote-overlay.png)
```

## Good Demo Video Criteria

Choose a video that has captions, contains dense technical terms, and is not so specialized that every card requires deep domain expertise. AI research explainers, engineering talks, finance interviews, and infrastructure podcasts are good candidates.
