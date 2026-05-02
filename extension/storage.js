(function () {
  const STORAGE_KEY = "footnote_known_terms";

  function normalizeTerm(term) {
    return String(term || "").trim().toLowerCase().replace(/\s+/g, " ");
  }

  function getChromeStorage() {
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      return chrome.storage.local;
    }
    return null;
  }

  async function loadKnownTerms() {
    const chromeStorage = getChromeStorage();
    if (chromeStorage) {
      const result = await chromeStorage.get({ [STORAGE_KEY]: [] });
      return Array.isArray(result[STORAGE_KEY]) ? result[STORAGE_KEY] : [];
    }

    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  async function saveKnownTerm(term) {
    const normalized = normalizeTerm(term);
    if (!normalized) return [];

    const knownTerms = await loadKnownTerms();
    const nextTerms = Array.from(new Set([...knownTerms.map(normalizeTerm), normalized])).sort();
    const chromeStorage = getChromeStorage();

    if (chromeStorage) {
      await chromeStorage.set({ [STORAGE_KEY]: nextTerms });
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextTerms));
    }

    return nextTerms;
  }

  window.FootnoteStorage = {
    loadKnownTerms,
    normalizeTerm,
    saveKnownTerm,
  };
})();
