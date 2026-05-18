(function () {
  function getVideoId(urlText = location.href) {
    try {
      const url = new URL(urlText);
      return url.searchParams.get("v") || "";
    } catch {
      return "";
    }
  }

  async function getTranscript() {
    const videoId = getVideoId();
    if (!videoId) {
      throw new Error("No YouTube video ID found.");
    }

    let track = findCaptionTrack();
    if (!track) {
      track = await findCaptionTrackFromFreshPage(videoId);
    }

    if (track) {
      try {
        return await fetchCaptionTrack(track);
      } catch (error) {
        console.warn("Footnote caption endpoint failed; trying DOM transcript fallback.", error);
      }
    }

    return getDomTranscript();
  }

  function findCaptionTrack() {
    const response = findPlayerResponse();
    const tracks =
      response &&
      response.captions &&
      response.captions.playerCaptionsTracklistRenderer &&
      response.captions.playerCaptionsTracklistRenderer.captionTracks;

    if (!Array.isArray(tracks) || tracks.length === 0) {
      return null;
    }

    return (
      tracks.find((track) => track.languageCode && track.languageCode.startsWith("en")) ||
      tracks.find((track) => track.kind !== "asr") ||
      tracks[0]
    );
  }

  function findPlayerResponse() {
    const scripts = Array.from(document.scripts);
    for (const script of scripts) {
      const text = script.textContent || "";
      const marker = "ytInitialPlayerResponse";
      const markerIndex = text.indexOf(marker);
      if (markerIndex === -1) continue;

      const firstBrace = text.indexOf("{", markerIndex);
      if (firstBrace === -1) continue;

      const jsonText = extractBalancedJson(text, firstBrace);
      if (!jsonText) continue;

      try {
        return JSON.parse(jsonText);
      } catch {
        continue;
      }
    }
    return null;
  }

  async function findCaptionTrackFromFreshPage(videoId) {
    try {
      const response = await fetch(`https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`, {
        credentials: "include",
      });
      if (!response.ok) return null;
      const pageText = await response.text();
      return findCaptionTrackInText(pageText);
    } catch {
      return null;
    }
  }

  function findCaptionTrackInText(text) {
    const marker = "ytInitialPlayerResponse";
    const markerIndex = text.indexOf(marker);
    if (markerIndex === -1) return null;

    const firstBrace = text.indexOf("{", markerIndex);
    if (firstBrace === -1) return null;

    const jsonText = extractBalancedJson(text, firstBrace);
    if (!jsonText) return null;

    try {
      return pickCaptionTrack(JSON.parse(jsonText));
    } catch {
      return null;
    }
  }

  function pickCaptionTrack(response) {
    const tracks =
      response &&
      response.captions &&
      response.captions.playerCaptionsTracklistRenderer &&
      response.captions.playerCaptionsTracklistRenderer.captionTracks;

    if (!Array.isArray(tracks) || tracks.length === 0) {
      return null;
    }

    return (
      tracks.find((track) => track.languageCode && track.languageCode.startsWith("en") && track.kind !== "asr") ||
      tracks.find((track) => track.languageCode && track.languageCode.startsWith("en")) ||
      tracks.find((track) => track.kind !== "asr") ||
      tracks[0]
    );
  }

  function extractBalancedJson(text, startIndex) {
    let depth = 0;
    let inString = false;
    let escaped = false;

    for (let index = startIndex; index < text.length; index += 1) {
      const char = text[index];

      if (inString) {
        if (escaped) {
          escaped = false;
        } else if (char === "\\") {
          escaped = true;
        } else if (char === '"') {
          inString = false;
        }
        continue;
      }

      if (char === '"') {
        inString = true;
      } else if (char === "{") {
        depth += 1;
      } else if (char === "}") {
        depth -= 1;
        if (depth === 0) {
          return text.slice(startIndex, index + 1);
        }
      }
    }

    return "";
  }

  async function fetchCaptionTrack(track) {
    const urls = [track.baseUrl, withFormat(track.baseUrl, "json3"), withFormat(track.baseUrl, "srv3")];
    let lastError = null;

    for (const url of urls) {
      try {
        const response = await fetch(url, { credentials: "include" });
        if (!response.ok) {
          throw new Error("Transcript fetch was blocked or unavailable.");
        }

        const text = await response.text();
        if (!text.trim()) {
          throw new Error("Transcript endpoint returned an empty response.");
        }

        if (text.trim().startsWith("{")) {
          return parseJson3Transcript(JSON.parse(text));
        }
        return parseXmlTranscript(text);
      } catch (error) {
        lastError = error;
      }
    }

    throw lastError || new Error("Transcript fetch was blocked or unavailable.");
  }

  function withFormat(baseUrl, format) {
    const url = new URL(baseUrl);
    url.searchParams.set("fmt", format);
    return url.toString();
  }

  function parseJson3Transcript(data) {
    const events = Array.isArray(data.events) ? data.events : [];
    const segments = events
      .filter((event) => Array.isArray(event.segs))
      .map((event) => {
        const text = event.segs.map((seg) => seg.utf8 || "").join("").replace(/\s+/g, " ").trim();
        return {
          start: (event.tStartMs || 0) / 1000,
          duration: (event.dDurationMs || 0) / 1000,
          text,
        };
      })
      .filter((segment) => segment.text);

    if (!segments.length) {
      throw new Error("No captions available for this video.");
    }

    return segments;
  }

  function parseXmlTranscript(text) {
    const doc = new DOMParser().parseFromString(text, "text/xml");
    const nodes = Array.from(doc.querySelectorAll("text"));
    const segments = nodes
      .map((node) => ({
        start: Number(node.getAttribute("start") || 0),
        duration: Number(node.getAttribute("dur") || 0),
        text: (node.textContent || "").replace(/\s+/g, " ").trim(),
      }))
      .filter((segment) => segment.text);

    if (!segments.length) {
      throw new Error("No captions available for this video.");
    }

    return segments;
  }

  async function getDomTranscript() {
    await openTranscriptPanel();
    const segmentNodes = await waitForTranscriptSegments();
    const segments = segmentNodes
      .map(parseDomTranscriptSegment)
      .filter((segment) => segment.text && Number.isFinite(segment.start));

    if (!segments.length) {
      throw new Error("Transcript panel was found, but no readable timestamped segments were available.");
    }

    return segments;
  }

  async function openTranscriptPanel() {
    if (hasTranscriptSegments()) return;

    if (await clickTranscriptControl()) return;

    await expandDescription();
    if (hasTranscriptSegments()) return;
    if (await clickTranscriptControl()) return;

    const buttons = Array.from(document.querySelectorAll("button, yt-button-shape button"));
    const moreButton = buttons.find((button) => /more actions|actions menu/i.test(button.getAttribute("aria-label") || ""));
    if (moreButton) {
      moreButton.click();
      await sleep(300);
      await clickTranscriptControl();
    }
  }

  async function waitForTranscriptSegments() {
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline) {
      const nodes = findTranscriptSegmentNodes();
      if (nodes.length) return nodes;
      await sleep(250);
    }
    return [];
  }

  function hasTranscriptSegments() {
    return findTranscriptSegmentNodes().length > 0;
  }

  function findTranscriptSegmentNodes() {
    const selectors = [
      "ytd-transcript-segment-renderer",
      "ytd-transcript-segment-list-renderer ytd-transcript-segment-renderer",
      "[target-id='engagement-panel-searchable-transcript'] ytd-transcript-segment-renderer",
      "[target-id*='transcript'] ytd-transcript-segment-renderer",
      "ytd-engagement-panel-section-list-renderer ytd-transcript-segment-renderer",
    ];

    return uniqueElements(selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector))));
  }

  async function clickTranscriptControl() {
    const selectors = [
      "button",
      "yt-button-shape button",
      "ytd-button-renderer",
      "tp-yt-paper-item",
      "ytd-menu-service-item-renderer",
      "a",
    ];
    const controls = uniqueElements(selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector))));
    const transcriptControl = controls.find((element) => {
      const label = [
        element.getAttribute("aria-label"),
        element.getAttribute("title"),
        element.textContent,
      ]
        .filter(Boolean)
        .join(" ");
      return /show transcript|open transcript|transcript/i.test(label) && !/hide transcript|close transcript/i.test(label);
    });

    if (!transcriptControl) return false;
    transcriptControl.click();
    await sleep(700);
    return hasTranscriptSegments();
  }

  async function expandDescription() {
    const buttons = Array.from(document.querySelectorAll("button, yt-button-shape button"));
    const moreButton = buttons.find((button) => {
      const label = [button.getAttribute("aria-label"), button.textContent].filter(Boolean).join(" ");
      return /\bmore\b|show more/i.test(label);
    });

    if (!moreButton) return;
    moreButton.click();
    await sleep(400);
  }

  function parseDomTranscriptSegment(node) {
    const timeNode = node.querySelector(".segment-timestamp, yt-formatted-string.segment-timestamp, [class*='timestamp']");
    const textNode = node.querySelector(".segment-text, yt-formatted-string.segment-text, [class*='segment-text']");
    const fallback = parseTimestampedText(node.textContent || "");

    return {
      start: parseTimestamp(timeNode ? timeNode.textContent : fallback.timestampText),
      duration: 0,
      text: textNode ? textNode.textContent.replace(/\s+/g, " ").trim() : fallback.text,
    };
  }

  function parseTimestampedText(text) {
    const cleanText = String(text || "").replace(/\s+/g, " ").trim();
    const match = cleanText.match(/^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$/);
    if (!match) return { timestampText: "", text: cleanText };
    return { timestampText: match[1], text: match[2].trim() };
  }

  function uniqueElements(elements) {
    return Array.from(new Set(elements)).filter((element) => element && element.isConnected);
  }

  function parseTimestamp(text) {
    const parts = String(text || "")
      .trim()
      .split(":")
      .map((part) => Number(part));
    if (parts.some((part) => Number.isNaN(part))) return NaN;
    return parts.reduce((total, part) => total * 60 + part, 0);
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  window.FootnoteTranscript = {
    getTranscript,
    getVideoId,
  };
})();
