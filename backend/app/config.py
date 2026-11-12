#Central configuration for the News Credibility Checker.Environment variables can override default settings.
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Base directory: backend/
BASE_DIR = Path(__file__).resolve().parent.parent
# Machine learning model configuration
_model_path = os.getenv("MODEL_PATH","models/model.joblib")
MODEL_PATH = Path(_model_path)
# Resolve relative model paths against the backend directory.
if not MODEL_PATH.is_absolute():
    MODEL_PATH = BASE_DIR / MODEL_PATH
# Classification labels considered potential risk indicators.
RISK_LABELS = {label.strip().lower()
    for label in os.getenv("RISK_LABELS","1,fake,unreliable").split(",")
    if label.strip()}
# Article text processing limits.
MIN_TEXT_CHARS = int(os.getenv("MIN_TEXT_CHARS", "300"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "50000"))
# Evidence retrieval configuration.
FACTCHECK_API_KEY = os.getenv("FACTCHECK_API_KEY","").strip()
EVIDENCE_TIMEOUT_S = float(os.getenv("EVIDENCE_TIMEOUT_S", "6.0"))

# Basic configuration validation.
if MIN_TEXT_CHARS < 1:
    raise ValueError("MIN_TEXT_CHARS must be greater than zero.")

if MAX_TEXT_CHARS < MIN_TEXT_CHARS:
    raise ValueError("MAX_TEXT_CHARS must not be smaller than MIN_TEXT_CHARS.")

if EVIDENCE_TIMEOUT_S <= 0:
    raise ValueError("EVIDENCE_TIMEOUT_S must be greater than zero.")
