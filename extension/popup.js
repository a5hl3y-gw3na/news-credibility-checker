/**
 * Popup script for News Credibility Checker extension.
 */

document.addEventListener("DOMContentLoaded", () => {
  const analyzeBtn = document.getElementById("analyze-btn");
  const reanalyzeBtn = document.getElementById("reanalyze-btn");
  const retryBtn = document.getElementById("retry-btn");
  const apiUrlInput = document.getElementById("api-url");
  const backendStatusEl = document.getElementById("backend-status");

  const actionSection = document.getElementById("action-section");
  const loadingSection = document.getElementById("loading-section");
  const errorSection = document.getElementById("error-section");
  const resultsSection = document.getElementById("results-section");

  // Load saved API URL or default
  chrome.storage?.local?.get(["apiUrl"], (result) => {
    if (result && result.apiUrl) {
      apiUrlInput.value = result.apiUrl;
    }
    checkBackendHealth();
  }) || checkBackendHealth();

  apiUrlInput.addEventListener("change", () => {
    const val = apiUrlInput.value.trim().replace(/\/$/, "");
    apiUrlInput.value = val;
    chrome.storage?.local?.set({ apiUrl: val });
    checkBackendHealth();
  });

  analyzeBtn.addEventListener("click", startAnalysis);
  reanalyzeBtn.addEventListener("click", startAnalysis);
  retryBtn.addEventListener("click", startAnalysis);

  function getApiUrl() {
    return (apiUrlInput.value.trim() || "http://localhost:8000").replace(/\/$/, "");
  }

  // Check if FastAPI backend is reachable
  async function checkBackendHealth() {
    backendStatusEl.className = "status-indicator status-checking";
    backendStatusEl.title = "Checking backend...";
    try {
      const response = await fetch(`${getApiUrl()}/health`, { method: "GET" });
      if (response.ok) {
        const data = await response.json();
        backendStatusEl.className = "status-indicator status-online";
        backendStatusEl.title = `Backend online (Model loaded: ${data.model_loaded})`;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (e) {
      backendStatusEl.className = "status-indicator status-offline";
      backendStatusEl.title = "Backend unreachable at " + getApiUrl();
    }
  }

  function showLoading() {
    actionSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    errorSection.classList.add("hidden");
    loadingSection.classList.remove("hidden");
  }

  function showError(message, helpText) {
    loadingSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    actionSection.classList.add("hidden");
    errorSection.classList.remove("hidden");

    document.getElementById("error-message").innerText = message;
    if (helpText) {
      document.querySelector(".error-help").innerHTML = helpText;
    }
  }

  // Get active tab content via content script
  async function extractActiveTabArticle() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      throw new Error("No active browser tab found.");
    }

    if (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://") || tab.url.startsWith("about:")) {
      throw new Error("Cannot analyse internal browser pages. Please open a news article.");
    }

    try {
      // First attempt: send message to pre-loaded content script
      const response = await chrome.tabs.sendMessage(tab.id, { action: "extract_article" });
      if (response && response.success) {
        return response.data;
      }
      throw new Error(response ? response.error : "Failed to extract");
    } catch (err) {
      // Fallback: inject content script dynamically if page was loaded before extension
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"]
      });
      const retryResponse = await chrome.tabs.sendMessage(tab.id, { action: "extract_article" });
      if (retryResponse && retryResponse.success) {
        return retryResponse.data;
      }
      throw new Error(retryResponse?.error || "Could not read article content from this page.");
    }
  }

  // Main execution flow
  async function startAnalysis() {
    showLoading();

    let articleData = null;
    try {
      articleData = await extractActiveTabArticle();
    } catch (err) {
      showError(err.message, "Make sure you are on a webpage containing an article.");
      return;
    }

    try {
      const response = await fetch(`${getApiUrl()}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(articleData)
      });

      if (!response.ok) {
        const errorDetail = await response.text();
        throw new Error(`Server returned HTTP ${response.status}: ${errorDetail}`);
      }

      const result = await response.json();
      renderResults(result);
    } catch (err) {
      showError("Analysis Failed", `Backend at <code>${getApiUrl()}</code> did not respond.<br><br>Error: ${err.message}`);
    }
  }

  // Render backend response
  function renderResults(res) {
    loadingSection.classList.add("hidden");
    errorSection.classList.add("hidden");
    actionSection.classList.add("hidden");
    resultsSection.classList.remove("hidden");

    // 1. Overall assessment badge & summary
    const badgeEl = document.getElementById("assessment-badge");
    const summaryEl = document.getElementById("assessment-summary");
    const scoreValEl = document.getElementById("score-value");
    const scoreBarEl = document.getElementById("score-bar");

    const assessmentLabels = {
      lower_concern: { text: "Lower Concern", class: "badge-lower", color: "#10b981" },
      some_concern: { text: "Some Concern", class: "badge-some", color: "#f59e0b" },
      higher_concern: { text: "Higher Concern", class: "badge-higher", color: "#ef4444" },
      unable_to_assess: { text: "Unable to Assess", class: "badge-unable", color: "#6b7280" }
    };

    const currentConfig = assessmentLabels[res.assessment] || assessmentLabels.unable_to_assess;
    badgeEl.innerText = currentConfig.text;
    badgeEl.className = `badge ${currentConfig.class}`;
    summaryEl.innerText = res.summary || "";

    // 2. Score bar
    if (res.combined_score !== null && res.combined_score !== undefined) {
      const percentage = Math.round(res.combined_score * 100);
      scoreValEl.innerText = `${res.combined_score.toFixed(2)} (${percentage}%)`;
      scoreBarEl.style.width = `${percentage}%`;
      scoreBarEl.style.backgroundColor = currentConfig.color;
    } else {
      scoreValEl.innerText = "N/A";
      scoreBarEl.style.width = "0%";
    }

    // 3. Model Results
    const modelBadge = document.getElementById("model-status-badge");
    const modelPrediction = document.getElementById("model-prediction");
    const modelRisk = document.getElementById("model-risk");
    const modelProbGrid = document.getElementById("model-probabilities");
    const modelNote = document.getElementById("model-note");

    if (res.model && res.model.available) {
      modelBadge.innerText = "Active";
      modelBadge.style.color = "#059669";
      modelPrediction.innerText = res.model.predicted_label ? res.model.predicted_label.toUpperCase() : "N/A";
      modelRisk.innerText = res.model.risk_probability !== null ? `${Math.round(res.model.risk_probability * 100)}%` : "N/A";
      modelNote.innerText = res.model.note || "";

      modelProbGrid.innerHTML = "";
      if (res.model.probabilities) {
        for (const [cls, prob] of Object.entries(res.model.probabilities)) {
          const chip = document.createElement("div");
          chip.className = "prob-chip";
          chip.innerHTML = `<span>${cls}</span><strong>${Math.round(prob * 100)}%</strong>`;
          modelProbGrid.appendChild(chip);
        }
      }
    } else {
      modelBadge.innerText = "Unavailable";
      modelPrediction.innerText = "N/A";
      modelRisk.innerText = "N/A";
      modelProbGrid.innerHTML = "";
      modelNote.innerText = res.model?.note || "Machine learning model unavailable.";
    }

    // 4. Language Indicators
    const langBadge = document.getElementById("language-score-badge");
    const langList = document.getElementById("language-indicators");
    langBadge.innerText = res.language ? `Score: ${res.language.score}` : "--";
    langList.innerHTML = "";

    if (res.language && res.language.indicators && res.language.indicators.length > 0) {
      res.language.indicators.forEach((item) => {
        const row = document.createElement("div");
        row.className = `indicator-item indicator-${item.severity}`;
        row.innerHTML = `<span>${item.severity === "warning" ? "⚠️" : "ℹ️"}</span><span>${item.message}</span>`;
        langList.appendChild(row);
      });
    } else {
      langList.innerHTML = "<p class='note-text'>No language indicators triggered.</p>";
    }

    // 5. Metadata Indicators
    const metaBadge = document.getElementById("metadata-score-badge");
    const metaList = document.getElementById("metadata-indicators");
    metaBadge.innerText = res.metadata ? `Score: ${res.metadata.score}` : "--";
    metaList.innerHTML = "";

    if (res.metadata && res.metadata.indicators && res.metadata.indicators.length > 0) {
      res.metadata.indicators.forEach((item) => {
        const row = document.createElement("div");
        row.className = `indicator-item indicator-${item.severity}`;
        row.innerHTML = `<span>${item.severity === "warning" ? "⚠️" : "ℹ️"}</span><span>${item.message}</span>`;
        metaList.appendChild(row);
      });
    } else {
      metaList.innerHTML = "<p class='note-text'>No metadata indicators triggered.</p>";
    }

    // 6. NLP Indicators
    const nlpBadge = document.getElementById("nlp-score-badge");
    const nlpList = document.getElementById("nlp-indicators");
    
    if (nlpBadge && nlpList) {
      nlpBadge.innerText = res.nlp ? `Score: ${res.nlp.score}` : "--";
      nlpList.innerHTML = "";

      if (res.nlp && res.nlp.indicators && res.nlp.indicators.length > 0) {
        res.nlp.indicators.forEach((item) => {
          const row = document.createElement("div");
          row.className = `indicator-item indicator-${item.severity}`;
          row.innerHTML = `<span>${item.severity === "warning" ? "⚠️" : "ℹ️"}</span><span>${item.message}</span>`;
          nlpList.appendChild(row);
        });
      } else {
        nlpList.innerHTML = "<p class='note-text'>No linguistic warning signs detected.</p>";
      }
    }

    // 7. Evidence Results
    const evidenceBadge = document.getElementById("evidence-status-badge");
    const evidenceNote = document.getElementById("evidence-note");
    const evidenceList = document.getElementById("evidence-items");

    evidenceBadge.innerText = res.evidence?.status ? res.evidence.status.replace("_", " ") : "--";
    evidenceNote.innerText = res.evidence?.note || "";
    evidenceList.innerHTML = "";

    if (res.evidence && res.evidence.items && res.evidence.items.length > 0) {
      res.evidence.items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "evidence-item";
        card.innerHTML = `
          <a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title || item.claim}</a>
          <div class="evidence-meta">
            <span><strong>Source:</strong> ${item.source_name}</span> |
            <span><strong>Rating:</strong> ${item.rating || "Unrated"}</span>
          </div>
        `;
        evidenceList.appendChild(card);
      });
    }

    // 8. Disclaimer
    document.getElementById("disclaimer-text").innerText = res.disclaimer || "";
  }
});