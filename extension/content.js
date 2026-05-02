(function () {
  const ROOT_ID = "footnote-root";
  const OVERLAY_ID = "footnote-overlay-root";
  const DEFAULT_LISTENER_PROFILE =
    "Technically curious generalist. Comfortable with common software, internet, and high-school science vocabulary.";
  const OVERLAY_SIZES = ["small", "medium", "large"];
  const OVERLAY_DIMENSIONS = {
    small: { width: 280, heightRatio: 0.4 },
    medium: { width: 360, heightRatio: 0.56 },
    large: { width: 460, heightRatio: 0.72 },
  };

  let currentVideoId = "";
  let cleanupPlayback = null;
  let routePoller = null;
  let overlayVisible = false;
  let overlaySize = "small";
  let currentCards = [];
  let sidebarPlacementTimer = 0;

  function boot() {
    startRouteWatcher();
    installClickHandlers();
    installDebugHooks();
    maybeLoadForCurrentPage();
  }

  function startRouteWatcher() {
    document.addEventListener("yt-navigate-finish", maybeLoadForCurrentPage);
    document.addEventListener("fullscreenchange", updateOverlayPlacement);
    document.addEventListener("webkitfullscreenchange", updateOverlayPlacement);
    window.addEventListener("resize", updateOverlayPlacement);
    window.addEventListener("scroll", updateOverlayPlacement, { passive: true });

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

  function installClickHandlers() {
    document.addEventListener("click", (event) => {
      const overlayToggle = event.target.closest && event.target.closest(".footnote-overlay-toggle");
      if (overlayToggle) {
        event.preventDefault();
        overlayVisible = !overlayVisible;
        syncOverlay();
        return;
      }

      const overlayClose = event.target.closest && event.target.closest(".footnote-overlay-close");
      if (overlayClose) {
        event.preventDefault();
        overlayVisible = false;
        syncOverlay();
        return;
      }

      const sizeButton = event.target.closest && event.target.closest(".footnote-size-button");
      if (sizeButton) {
        event.preventDefault();
        resizeOverlay(sizeButton.dataset.sizeAction === "larger" ? 1 : -1);
      }
    });
  }

  function installDebugHooks() {
    window.FootnoteDebug = {
      showOverlay() {
        overlayVisible = true;
        syncOverlay();
        return document.getElementById(OVERLAY_ID);
      },
      hideOverlay() {
        overlayVisible = false;
        syncOverlay();
        return document.getElementById(OVERLAY_ID);
      },
      state() {
        return {
          currentVideoId,
          cards: currentCards.length,
          overlayVisible,
          overlaySize,
          sidebar: document.getElementById(ROOT_ID),
          overlay: document.getElementById(OVERLAY_ID),
          sidebarHost: getSidebarHost(),
        };
      },
    };
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
    window.clearTimeout(sidebarPlacementTimer);
    const existingRoot = document.getElementById(ROOT_ID);
    if (existingRoot) existingRoot.remove();
    const overlayRoot = document.getElementById(OVERLAY_ID);
    if (overlayRoot) overlayRoot.remove();
    currentCards = [];
    if (resetVideoId) currentVideoId = "";
  }

  function injectSidebar() {
    const root = document.createElement("aside");
    root.id = ROOT_ID;
    root.className = "footnote-root is-sidebar";
    root.innerHTML = `
      <div class="footnote-header">
        <div>
          <div class="footnote-title">Footnote</div>
          <div class="footnote-subtitle">Glossary cards</div>
        </div>
        <div class="footnote-actions">
          <button class="footnote-overlay-toggle" type="button" title="Show Footnote over the video">Overlay</button>
          <button class="footnote-refresh" type="button" title="Refresh Footnote">Refresh</button>
        </div>
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

    placeSidebar(root);
    return root;
  }

  function placeSidebar(root) {
    const host = getSidebarHost();
    if (host) {
      root.classList.remove("is-floating", "is-pending-placement");
      host.prepend(root);
      return;
    }

    root.classList.add("is-pending-placement");
    window.clearTimeout(sidebarPlacementTimer);
    sidebarPlacementTimer = window.setTimeout(() => {
      if (document.getElementById(ROOT_ID) === root || !root.isConnected) {
        placeSidebar(root);
      }
    }, 250);
  }

  function renderState(root, type, message) {
    root.dataset.state = type;
    const status = root.querySelector(".footnote-status");
    const list = root.querySelector(".footnote-card-list");
    status.textContent = message;
    list.innerHTML = "";
    currentCards = [];
    syncOverlay(root);
  }

  function renderCards(root, cards, cached) {
    const status = root.querySelector(".footnote-status");
    const list = root.querySelector(".footnote-card-list");
    const sortedCards = sortCards(cards);
    currentCards = sortedCards;
    root.dataset.state = "ready";

    if (!sortedCards.length) {
      status.textContent = "No glossary cards for this video.";
      list.innerHTML = "";
      syncOverlay(root);
      return;
    }

    status.textContent = cached ? "Loaded from cache" : "Fresh extraction";
    list.innerHTML = "";

    for (const card of sortedCards) {
      list.append(createCard(card));
    }

    if (cleanupPlayback) cleanupPlayback();
    cleanupPlayback = window.FootnotePlayback.startPlaybackSync(root, sortedCards);
    syncOverlay(root);
  }

  function createCard(card, options = {}) {
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
      ${options.readOnly ? "" : '<button class="footnote-dismiss" type="button">I know this</button>'}
    `;

    if (!options.readOnly) {
      article.querySelector(".footnote-dismiss").addEventListener("click", async () => {
        await window.FootnoteStorage.saveKnownTerm(card.term);
        removeCard(card.id);
      });
    }

    return article;
  }

  function syncOverlay(sidebarRoot = document.getElementById(ROOT_ID)) {
    updateOverlayButton(sidebarRoot);

    if (!overlayVisible) {
      removeOverlay();
      return;
    }

    const overlayRoot = ensureOverlay();
    applyOverlayBaseStyles(overlayRoot);
    if (!overlayRoot.isConnected) {
      document.body.append(overlayRoot);
    }
    overlayRoot.dataset.state = sidebarRoot ? sidebarRoot.dataset.state || "ready" : "ready";
    overlayRoot.dataset.overlaySize = overlaySize;
    overlayRoot.querySelector(".footnote-status").textContent = sidebarRoot
      ? sidebarRoot.querySelector(".footnote-status").textContent
      : "";

    const list = overlayRoot.querySelector(".footnote-card-list");
    list.innerHTML = "";
    for (const card of currentCards) {
      const sidebarCard = sidebarRoot ? sidebarRoot.querySelector(`.footnote-card[data-card-id="${cssEscape(card.id)}"]`) : null;
      const cardElement = createCard(card, { readOnly: true });
      cardElement.classList.toggle("is-active", Boolean(sidebarCard && sidebarCard.classList.contains("is-active")));
      list.append(cardElement);
    }

    updateOverlayPlacement();
  }

  function ensureOverlay() {
    let overlayRoot = document.getElementById(OVERLAY_ID);
    if (overlayRoot) return overlayRoot;

    overlayRoot = document.createElement("aside");
    overlayRoot.id = OVERLAY_ID;
    overlayRoot.className = "footnote-root footnote-overlay-root is-overlay";
    applyOverlayBaseStyles(overlayRoot);
    overlayRoot.innerHTML = `
      <div class="footnote-header">
        <div>
          <div class="footnote-title">Footnote</div>
          <div class="footnote-subtitle">Video overlay</div>
        </div>
        <div class="footnote-actions">
          <button class="footnote-size-button" data-size-action="smaller" type="button" title="Make overlay smaller">-</button>
          <button class="footnote-size-button" data-size-action="larger" type="button" title="Make overlay larger">+</button>
          <button class="footnote-overlay-close" type="button" title="Hide video overlay">Hide</button>
        </div>
      </div>
      <div class="footnote-status" role="status"></div>
      <div class="footnote-card-list"></div>
    `;

    document.body.append(overlayRoot);
    return overlayRoot;
  }

  function updateOverlayPlacement() {
    const overlayRoot = document.getElementById(OVERLAY_ID);
    if (!overlayRoot || !overlayVisible) return;

    applyOverlayBaseStyles(overlayRoot);
    overlayRoot.classList.remove("is-floating");
    const fullscreenHost = document.fullscreenElement || document.webkitFullscreenElement;
    if (fullscreenHost) {
      overlayRoot.classList.add("is-fullscreen");
      overlayRoot.style.position = "absolute";
      positionOverlayInRect(overlayRoot, fullscreenHost.getBoundingClientRect(), true);
      fullscreenHost.append(overlayRoot);
    } else {
      overlayRoot.classList.remove("is-fullscreen");
      positionOverlayOverVideo(overlayRoot);
      document.body.append(overlayRoot);
    }
  }

  function positionOverlayOverVideo(overlayRoot) {
    const videoBox = getVideoBox();
    if (!videoBox) {
      positionOverlayInViewport(overlayRoot);
      return;
    }

    positionOverlayInRect(overlayRoot, videoBox, false);
  }

  function positionOverlayInViewport(overlayRoot) {
    const dimensions = getOverlayDimensions(window.innerWidth, window.innerHeight);
    overlayRoot.style.top = "96px";
    overlayRoot.style.left = `${Math.max(window.innerWidth - dimensions.width - 24, 16)}px`;
    overlayRoot.style.width = `${dimensions.width}px`;
    overlayRoot.style.maxHeight = `${dimensions.height}px`;
  }

  function positionOverlayInRect(overlayRoot, rect, fullscreen) {
    const dimensions = getOverlayDimensions(rect.width, rect.height);
    const inset = fullscreen ? 28 : 18;
    const top = Math.max(rect.top + inset, inset);
    const left = Math.max(rect.right - dimensions.width - inset, inset);
    overlayRoot.style.top = `${Math.round(top)}px`;
    overlayRoot.style.left = `${Math.round(left)}px`;
    overlayRoot.style.right = "auto";
    overlayRoot.style.width = `${dimensions.width}px`;
    overlayRoot.style.maxHeight = `${dimensions.height}px`;
  }

  function getOverlayDimensions(containerWidth, containerHeight) {
    const size = OVERLAY_DIMENSIONS[overlaySize] || OVERLAY_DIMENSIONS.small;
    const width = Math.min(size.width, Math.max(containerWidth * 0.38, 240), window.innerWidth - 32);
    const height = Math.min(Math.max(containerHeight * size.heightRatio, 180), window.innerHeight - 120);
    return { width: Math.round(width), height: Math.round(height) };
  }

  function applyOverlayBaseStyles(overlayRoot) {
    overlayRoot.style.display = "block";
    overlayRoot.style.visibility = "visible";
    overlayRoot.style.opacity = "1";
    overlayRoot.style.pointerEvents = "auto";
    overlayRoot.style.position = "fixed";
    overlayRoot.style.zIndex = "2147483647";
    overlayRoot.style.margin = "0";
  }

  function getVideoBox() {
    const candidates = [
      document.querySelector("#player"),
      document.querySelector("#movie_player"),
      document.querySelector(".html5-video-player"),
      document.querySelector("video"),
    ];

    for (const candidate of candidates) {
      if (!candidate) continue;
      const box = candidate.getBoundingClientRect();
      if (box.width > 100 && box.height > 100) {
        return box;
      }
    }

    return null;
  }

  function removeOverlay() {
    const overlayRoot = document.getElementById(OVERLAY_ID);
    if (overlayRoot) overlayRoot.remove();
  }

  function resizeOverlay(direction) {
    const currentIndex = OVERLAY_SIZES.indexOf(overlaySize);
    const nextIndex = Math.min(Math.max(currentIndex + direction, 0), OVERLAY_SIZES.length - 1);
    overlaySize = OVERLAY_SIZES[nextIndex];
    syncOverlay();
  }

  function removeCard(cardId) {
    currentCards = currentCards.filter((card) => card.id !== cardId);
    document.querySelectorAll(`.footnote-card[data-card-id="${cssEscape(cardId)}"]`).forEach((card) => card.remove());
    syncOverlay();
  }

  function updateOverlayButton(root) {
    if (!root) return;
    const button = root.querySelector(".footnote-overlay-toggle");
    if (!button) return;
    button.textContent = overlayVisible ? "Hide overlay" : "Overlay";
    button.title = overlayVisible ? "Hide Footnote over the video" : "Show Footnote over the video";
    button.classList.toggle("is-active", overlayVisible);
  }

  function getSidebarHost() {
    return document.querySelector("#secondary-inner") || document.querySelector("#secondary");
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

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return String(value).replace(/["\\]/g, "\\$&");
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = String(value || "");
    return div.innerHTML;
  }

  boot();
})();
