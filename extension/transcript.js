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

    const track = findCaptionTrack();
    if (track) {
      return fetchCaptionTrack(track);
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
    const url = new URL(track.baseUrl);
    url.searchParams.set("fmt", "json3");

    const response = await fetch(url.toString(), { credentials: "include" });
    if (!response.ok) {
      throw new Error("Transcript fetch was blocked or unavailable.");
    }

    const text = await response.text();
    try {
      return parseJson3Transcript(JSON.parse(text));
    } catch {
      return parseXmlTranscript(text);
    }
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
      .map((node) => {
        const timeNode = node.querySelector(".segment-timestamp, yt-formatted-string.segment-timestamp");
        const textNode = node.querySelector(".segment-text, yt-formatted-string.segment-text");
        return {
          start: parseTimestamp(timeNode ? timeNode.textContent : ""),
          duration: 0,
          text: textNode ? textNode.textContent.replace(/\s+/g, " ").trim() : "",
        };
      })
      .filter((segment) => segment.text && Number.isFinite(segment.start));

    if (!segments.length) {
      throw new Error("No captions available for this video.");
    }

    return segments;
  }

  async function openTranscriptPanel() {
    if (document.querySelector("ytd-transcript-segment-renderer")) return;

    const buttons = Array.from(document.querySelectorAll("button, yt-button-shape button"));
    const moreButton = buttons.find((button) => /more actions/i.test(button.getAttribute("aria-label") || ""));
    if (moreButton) {
      moreButton.click();
      await sleep(300);
      const menuItems = Array.from(document.querySelectorAll("tp-yt-paper-item, ytd-menu-service-item-renderer"));
      const transcriptItem = menuItems.find((item) => /show transcript|transcript/i.test(item.textContent || ""));
      if (transcriptItem) {
        transcriptItem.click();
        await sleep(500);
      }
    }
  }

  async function waitForTranscriptSegments() {
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline) {
      const nodes = Array.from(document.querySelectorAll("ytd-transcript-segment-renderer"));
      if (nodes.length) return nodes;
      await sleep(250);
    }
    return [];
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
