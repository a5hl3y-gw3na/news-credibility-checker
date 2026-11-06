import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["MODEL_PATH"] = "models/does_not_exist.joblib"
os.environ["FACTCHECK_API_KEY"] = ""

from fastapi.testclient import TestClient
from app.main import app

LONG = "Officials said on Tuesday that 40 percent of the budget would be reallocated. " * 8


def test_health():
    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "ok"


def test_full_article_without_model():
    with TestClient(app) as c:
        r = c.post("/analyze", json={"url": "https://example.com/a", "title": "Budget update", "text": LONG,
                                     "author": "A. Writer", "publish_date": "2026-10-01"})
        d = r.json()
        assert r.status_code == 200
        assert d["model"]["available"] is False
        assert d["evidence"]["status"] == "not_configured"
        assert d["assessment"] in {"lower_concern", "some_concern", "higher_concern"}


def test_short_text_unable_to_assess():
    with TestClient(app) as c:
        d = c.post("/analyze", json={"url": "http://x.com", "text": "hi"}).json()
        assert d["assessment"] == "unable_to_assess"


def test_sensational_language_flagged():
    with TestClient(app) as c:
        d = c.post("/analyze", json={"url": "https://x.com/s", "title": "SHOCKING bombshell!!!",
                                     "text": LONG + " You won't believe this!"}).json()
        ids = [i["id"] for i in d["language"]["indicators"]]
        assert "sensational" in ids and "exclamations" in ids


def test_missing_url_rejected():
    with TestClient(app) as c:
        assert c.post("/analyze", json={"text": "x"}).status_code == 422
