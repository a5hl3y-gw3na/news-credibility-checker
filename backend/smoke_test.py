"""Smoke test for the News Credibility Checker backend (run it with the backend already running).
Usage:  python smoke_test.py [base_url]        default: http://127.0.0.1:8000
Standard library only. Checks the backend WITHOUT the browser extension."""
import json, sys, urllib.request, urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
EXT_ORIGIN = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"   # fake id, only tests CORS

CALM = ("A U.S. Senate committee voted on Tuesday to advance a bill that would fund road, bridge and water "
        "projects, according to a statement from the committee chairman's office. The measure passed 14-8, "
        "a spokesman for the Senate majority leader told reporters. Senator Mark Hollis said about 40 percent "
        "of the funds would go to highway repairs. Lawmakers said they expected a floor vote this month. ") * 2
SENSATIONAL = ("BREAKING!!! WATCH THIS VIDEO before it gets deleted. The mainstream media is HIDING the real "
               "story and nobody is talking about it! You won't believe what they are hiding from you. "
               "Sources say it is a total cover-up. Wake up, America! Share this with everyone you know!!! ") * 3


def call(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()
    except Exception as e:
        return None, {}, f"{type(e).__name__}: {e}"


ok_all = True
def check(name, ok, detail=""):
    global ok_all
    ok_all &= bool(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (f"   -> {detail}" if detail else ""))


s, _, b = call("GET", "/health")
if s is None:
    print("FAIL  backend not reachable:", b, "\nStart it first:  python -m uvicorn app.main:app --reload")
    sys.exit(1)
h = json.loads(b) if s == 200 else {}
check("backend reachable (/health)", s == 200, b[:100])
check("REAL model loaded (model_loaded is true)", h.get("model_loaded") is True,
      "if false: models/model.joblib missing, wrong MODEL_PATH, or scikit-learn version mismatch")


def analyse(title, text, **extra):
    payload = {"url": "https://example.com/news/story", "title": title, "text": text,
               "author": "A. Writer", "publish_date": "2026-11-10", "site_name": "Example", **extra}
    s, hd, b = call("POST", "/analyze", payload)
    try:
        return s, hd, json.loads(b)
    except Exception:
        return s, hd, {}

s, hd, calm = analyse("Senate committee advances funding bill", CALM)
check("POST /analyze works (calm article)", s == 200, f"HTTP {s}")
for key in ["assessment", "summary", "combined_score", "model", "metadata", "language", "evidence", "disclaimer"]:
    check(f"response has '{key}'", key in calm)
m = calm.get("model", {})
check("model produced a risk probability (not null)", m.get("available") and m.get("risk_probability") is not None,
      f"model={m.get('note')!r}  <- null here means the RISK_LABELS fix is missing")

s, _, sens = analyse("SHOCKING: THEY ARE HIDING THE TRUTH!!!", SENSATIONAL, author=None, publish_date=None)
c1, c2 = calm.get("combined_score"), sens.get("combined_score")
print(f"      calm: {calm.get('assessment')} ({c1})   sensational: {sens.get('assessment')} ({c2})")
check("sensational article scores higher than the calm one", c1 is not None and c2 is not None and c2 > c1)

s, _, short = analyse("x", "too short")
check("very short text handled (unable_to_assess)", s == 200 and short.get("assessment") == "unable_to_assess")
s, _, _ = call("POST", "/analyze", {"text": "x"})
check("missing url rejected (422)", s == 422, f"HTTP {s}")

s, hd, _ = call("POST", "/analyze", {"url": "https://x.com", "text": "x"}, headers={"Origin": EXT_ORIGIN})
allow = {k.lower(): v for k, v in hd.items()}.get("access-control-allow-origin")
check("CORS allows a browser-extension origin", allow is not None, f"allow-origin: {allow}")
print("evidence status:", calm.get("evidence", {}).get("status"), "(not_configured = no FACTCHECK_API_KEY set; expected)")
print("\nALL CHECKS PASSED" if ok_all else "\nSOME CHECKS FAILED: fix the FAIL lines first")
