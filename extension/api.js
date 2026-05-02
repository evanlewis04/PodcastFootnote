(function () {
  const API_BASE_URL = "http://localhost:8000";

  async function extractTerms(payload) {
    const response = await fetch(`${API_BASE_URL}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      const detail = data && data.detail ? data.detail : `Request failed with ${response.status}`;
      throw new Error(detail);
    }

    return data;
  }

  window.FootnoteApi = {
    extractTerms,
  };
})();
