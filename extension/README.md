# 📰 News Credibility Checker — Browser Extension

This directory contains the Chrome/Edge Manifest V3 browser extension for the News Credibility Assessment system.

---

## 🚀 How to Install and Test Locally

### 1. Start the FastAPI Backend
Before testing the extension, make sure the backend server is running:

```bash
cd backend
python -m uvicorn app.main:app --reload
```
You can verify it is running by checking `http://localhost:8000/health`.

---

### 2. Load the Extension in Google Chrome / Brave / Edge

1. Open your browser and go to `chrome://extensions` (or `edge://extensions`).
2. Toggle on **Developer mode** in the top-right corner.
3. Click the **Load unpacked** button.
4. Select the `extension` folder inside this repository:
   `c:\Users\...\news-credibility-checker\extension`
5. The **News Credibility Checker** extension will appear in your extensions list.

---

### 3. Test on a News Article

1. Navigate to any online news article in your browser.
2. (Optional) Highlight any specific claim sentence with your mouse if you want targeted fact-checking.
3. Click the **News Credibility Checker** icon in your browser toolbar.
4. Click **Analyse This Article**.
5. The extension will scrape the article text and metadata, send it to the FastAPI backend at `http://localhost:8000/analyze`, and display:
   - **Overall Assessment** (Lower Concern / Some Concern / Higher Concern)
   - **Combined Warning Score**
   - **ML Classifier Prediction & Probabilities**
   - **Language Warning Indicators** (sensational, clickbait, absolute claims, all-caps)
   - **Metadata Verification** (author, date, HTTPS, publisher domain)
   - **Evidence & Fact-Check Matches**
   - **Responsible AI Disclaimer**

