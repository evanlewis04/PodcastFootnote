(function () {
  function startPlaybackSync(root, cards) {
    const video = document.querySelector("video");
    const list = root.querySelector(".footnote-card-list");
    if (!video || !list) {
      return function cleanup() {};
    }

    const timedCards = cards
      .filter((card) => typeof card.timestamp === "number")
      .sort((a, b) => a.timestamp - b.timestamp);

    let activeId = "";
    let userScrolling = false;
    let scrollTimer = 0;
    let throttleTimer = 0;

    function onScroll() {
      userScrolling = true;
      window.clearTimeout(scrollTimer);
      scrollTimer = window.setTimeout(() => {
        userScrolling = false;
      }, 1200);
    }

    function updateActiveCard() {
      throttleTimer = 0;
      if (!timedCards.length) return;

      const currentTime = video.currentTime || 0;
      let activeCard = null;
      for (const card of timedCards) {
        if (card.timestamp <= currentTime) activeCard = card;
        if (card.timestamp > currentTime) break;
      }

      const nextId = activeCard ? activeCard.id : "";
      if (nextId === activeId) return;
      activeId = nextId;

      root.querySelectorAll(".footnote-card").forEach((element) => {
        element.classList.toggle("is-active", element.dataset.cardId === activeId);
      });

      window.dispatchEvent(
        new CustomEvent("footnote-active-card-changed", {
          detail: {
            activeId,
            currentTime,
          },
        })
      );

      if (!userScrolling && activeId) {
        const activeElement = root.querySelector(`.footnote-card[data-card-id="${cssEscape(activeId)}"]`);
        if (activeElement) {
          activeElement.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
    }

    function scheduleUpdate() {
      if (throttleTimer) return;
      throttleTimer = window.setTimeout(updateActiveCard, 250);
    }

    list.addEventListener("scroll", onScroll, { passive: true });
    video.addEventListener("timeupdate", scheduleUpdate);
    video.addEventListener("seeked", updateActiveCard);
    updateActiveCard();

    return function cleanup() {
      list.removeEventListener("scroll", onScroll);
      video.removeEventListener("timeupdate", scheduleUpdate);
      video.removeEventListener("seeked", updateActiveCard);
      window.clearTimeout(scrollTimer);
      window.clearTimeout(throttleTimer);
    };
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return String(value).replace(/["\\]/g, "\\$&");
  }

  window.FootnotePlayback = {
    startPlaybackSync,
  };
})();
