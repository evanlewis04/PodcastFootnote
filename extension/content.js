(function () {
  const ROOT_ID = "footnote-root";
  const DEFAULT_LISTENER_PROFILE =
    "Technically curious generalist. Comfortable with common software, internet, and high-school science vocabulary.";

  let currentVideoId = "";
  let cleanupPlayback = null;
  let routePoller = null;

  function boot() {
    startRouteWatcher();
    maybeLoadForCurrentPage();
  }

  function startRouteWatcher() {
    document.addEventListener("yt-navigate-finish", maybeLoadForCurrentPage);

    if (!routePoller) {
      let lastUrl = location.href;
      routePoller = window.setInterval(() => {
        if (location.href !== lastUrl) {
          lastUrl = location.href;
          maybeLoadForCurrentPage();
        }
      }, 1000);
    }
  }

  async function maybeLoadForCurrentPage() {
    const videoId = window.FootnoteTranscript.getVideoId();
    if (!videoId) {
      teardown();
      return;
    }

    if (videoId === currentVideoId && document.getElementById(ROOT_ID)) {
      return;
    }

    currentVideoId = videoId;
    teardown(false);
    const root = injectSidebar();
    renderState(root, "loading", "Collecting transcript...");

    try {
      const knownTerms = await window.FootnoteStorage.loadKnownTerms();
      let transcript = null;
      try {
        transcript = await window.FootnoteTranscript.getTranscript();
      } catch (transcriptError) {
        renderState(root, "loading", "Transcript unavailable; checking cache...");
        const cachedResponse = await loadCachedResponse(videoId, knownTerms, transcriptError);
        if (cachedResponse) {
          const visibleTerms = filterKnownTerms(cachedResponse.terms || [], knownTerms);
          renderCards(root, visibleTerms, true);
          return;
        }
        throw transcriptError;
      }

      renderState(root, "loading", "Extracting glossary cards...");
      const response = await window.FootnoteApi.extractTerms({
        video_id: videoId,
        video_url: location.href,
        title: getVideoTitle(),
        listener_profile: DEFAULT_LISTENER_PROFILE,
        known_terms: knownTerms,
        transcript,
      });

      const visibleTerms = filterKnownTerms(response.terms || [], knownTerms);
      renderCards(root, visibleTerms, Boolean(response.cached));
    } catch (error) {
      renderState(root, "error", error && error.message ? error.message : "Footnote could not load this video.");
    }
  }

  async function loadCachedResponse(videoId, knownTerms, originalError) {
    try {
      return await window.FootnoteApi.getCachedTerms(videoId);
    } catch (cacheError) {
      console.warn("Footnote cache lookup failed after transcript error.", {
        transcriptError: originalError,
        cacheError,
        knownTerms,
      });
      return null;
    }
  }

  function teardown(resetVideoId = true) {
    if (cleanupPlayback) {
      cleanupPlayback();
      cleanupPlayback = null;
    }
    const existingRoot = document.getElementById(ROOT_ID);
    if (existingRoot) existingRoot.remove();
    if (resetVideoId) currentVideoId = "";
  }

  function injectSidebar() {
    const root = document.createElement("aside");
    root.id = ROOT_ID;
    root.className = "footnote-root";
    root.innerHTML = `
      <div class="footnote-header">
        <div>
          <div class="footnote-title">Footnote</div>
          <div class="footnote-subtitle">Glossary cards</div>
        </div>
        <button class="footnote-refresh" type="button" title="Refresh Footnote">Refresh</button>
      </div>
      <div class="footnote-status" role="status"></div>
      <div class="footnote-card-list"></div>
    `;

    root.querySelector(".footnote-refresh").addEventListener("click", () => {
      const previousVideoId = currentVideoId;
      currentVideoId = "";
      maybeLoadForCurrentPage();
      currentVideoId = previousVideoId;
    });

    const secondary = document.querySelector("#secondary-inner") || document.querySelector("#secondary");
    if (secondary) {
      secondary.prepend(root);
    } else {
      document.body.append(root);
      root.classList.add("is-floating");
    }

    return root;
  }

  function renderState(root, type, message) {
    root.dataset.state = type;
    const status = root.querySelector(".footnote-status");
    const list = root.querySelector(".footnote-card-list");
    status.textContent = message;
    list.innerHTML = "";
  }

  function renderCards(root, cards, cached) {
    const status = root.querySelector(".footnote-status");
    const list = root.querySelector(".footnote-card-list");
    const sortedCards = sortCards(cards);
    root.dataset.state = "ready";

    if (!sortedCards.length) {
      status.textContent = "No glossary cards for this video.";
      list.innerHTML = "";
      return;
    }

    status.textContent = cached ? "Loaded from cache" : "Fresh extraction";
    list.innerHTML = "";

    for (const card of sortedCards) {
      list.append(createCard(card));
    }

    if (cleanupPlayback) cleanupPlayback();
    cleanupPlayback = window.FootnotePlayback.startPlaybackSync(root, sortedCards);
  }

  function createCard(card) {
    const article = document.createElement("article");
    article.className = "footnote-card";
    article.dataset.cardId = card.id;
    if (typeof card.timestamp === "number") article.dataset.timestamp = String(card.timestamp);

    const timestamp = typeof card.timestamp === "number" ? formatTimestamp(card.timestamp) : "Unsynced";
    const expansion = card.expansion ? `<div class="footnote-expansion">${escapeHtml(card.expansion)}</div>` : "";
    article.innerHTML = `
      <div class="footnote-card-topline">
        <span class="footnote-time">${timestamp}</span>
        <span class="footnote-category">${escapeHtml(card.category || "other")}</span>
      </div>
      <h3 class="footnote-term">${escapeHtml(card.term)}</h3>
      ${expansion}
      <p class="footnote-one-liner">${escapeHtml(card.one_liner || "")}</p>
      <p class="footnote-deeper">${escapeHtml(card.deeper || "")}</p>
      <button class="footnote-dismiss" type="button">I know this</button>
    `;

    article.querySelector(".footnote-dismiss").addEventListener("click", async () => {
      await window.FootnoteStorage.saveKnownTerm(card.term);
      article.remove();
    });

    return article;
  }

  function sortCards(cards) {
    return [...cards].sort((a, b) => {
      const aTime = typeof a.timestamp === "number" ? a.timestamp : Number.POSITIVE_INFINITY;
      const bTime = typeof b.timestamp === "number" ? b.timestamp : Number.POSITIVE_INFINITY;
      if (aTime !== bTime) return aTime - bTime;
      return String(a.term || "").localeCompare(String(b.term || ""));
    });
  }

  function filterKnownTerms(cards, knownTerms) {
    const known = new Set((knownTerms || []).map(window.FootnoteStorage.normalizeTerm));
    return cards.filter((card) => !known.has(window.FootnoteStorage.normalizeTerm(card.term)));
  }

  function getVideoTitle() {
    const title = document.querySelector("ytd-watch-metadata h1") || document.querySelector("h1.title");
    return title ? title.textContent.trim() : document.title.replace(/ - YouTube$/, "");
  }

  function formatTimestamp(seconds) {
    const totalSeconds = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = totalSeconds % 60;
    return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = String(value || "");
    return div.innerHTML;
  }

  boot();
})();
