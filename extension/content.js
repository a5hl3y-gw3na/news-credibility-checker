/**
 * Content script to extract article content, metadata, and user selections from web pages.
 */

function extractMetadata() {
  const getMeta = (names) => {
    for (const name of names) {
      const el = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
      if (el && el.content && el.content.trim()) {
        return el.content.trim();
      }
    }
    return null;
  };

  // 1. Title extraction
  let title = getMeta(["og:title", "twitter:title", "headline"]);
  if (!title) {
    const h1 = document.querySelector("h1");
    if (h1 && h1.innerText.trim()) {
      title = h1.innerText.trim();
    } else {
      title = document.title || "";
    }
  }

  // 2. Author extraction
  let author = getMeta(["author", "article:author", "byl", "twitter:creator"]);
  if (!author) {
    const authorEl = document.querySelector('[rel="author"], .byline, .author-name, [itemprop="author"]');
    if (authorEl && authorEl.innerText.trim()) {
      author = authorEl.innerText.trim();
    }
  }

  // 3. Publication Date extraction
  let publishDate = getMeta(["article:published_time", "publication_date", "date", "pubdate"]);
  if (!publishDate) {
    const timeEl = document.querySelector("time[datetime], time");
    if (timeEl) {
      publishDate = timeEl.getAttribute("datetime") || timeEl.innerText.trim();
    }
  }

  // 4. Site Name extraction
  let siteName = getMeta(["og:site_name", "application-name"]);
  if (!siteName) {
    siteName = window.location.hostname.replace(/^www\./, "");
  }

  // 5. Article Text extraction
  let articleText = "";
  const articleEl = document.querySelector("article, [role='main'], main, .article-body, .story-body, .post-content, #article-body");
  if (articleEl) {
    // Clone to avoid modifying DOM
    const clone = articleEl.cloneNode(true);
    // Remove scripts, styles, comments, nav, ads, footers
    const toRemove = clone.querySelectorAll("script, style, noscript, nav, footer, header, aside, .ad, .advertisement, [aria-hidden='true']");
    toRemove.forEach((el) => el.remove());

    const paragraphs = Array.from(clone.querySelectorAll("p"))
      .map((p) => p.innerText.trim())
      .filter((t) => t.length > 20);

    if (paragraphs.length > 0) {
      articleText = paragraphs.join("\n\n");
    } else {
      articleText = clone.innerText.trim();
    }
  }

  // Fallback to all page paragraphs if article container was not found or has little text
  if (!articleText || articleText.length < 200) {
    const allP = Array.from(document.querySelectorAll("p"))
      .map((p) => p.innerText.trim())
      .filter((t) => t.length > 30);
    if (allP.length > 0) {
      articleText = allP.join("\n\n");
    }
  }

  // 6. Highlighted Claims (if user selected any text before clicking analyse)
  const selection = window.getSelection() ? window.getSelection().toString().trim() : "";
  const claims = selection.length > 10 ? [selection] : [];

  return {
    url: window.location.href,
    title: title || "",
    text: articleText || "",
    author: author || null,
    publish_date: publishDate || null,
    site_name: siteName || null,
    claims: claims
  };
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extract_article") {
    try {
      const data = extractMetadata();
      sendResponse({ success: true, data: data });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
  return true; // Keep message channel open for async response
});

