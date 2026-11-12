"""Tests the REAL trained model through the backend's model_service.
Skipped if models/model.joblib is missing. Guards against the label mismatch that
previously made the model's risk probability None (classes are 0/1, not 'fake'/'real')."""
import os, sys
from pathlib import Path
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import config
from app.services import model_service

REAL = Path(__file__).resolve().parent.parent / "models" / "model.joblib"
pytestmark = pytest.mark.skipif(not REAL.exists(), reason="models/model.joblib not present")

NEWS = ("The U.S. Senate voted on Tuesday to approve a spending bill, officials said, after weeks of "
        "negotiations between Republican and Democratic leaders. The bill, which passed 68-32, now goes "
        "to the House of Representatives, a spokesman told reporters. Lawmakers said they expected a final vote by Friday. ") * 2
OPINION = ("BREAKING: Obama just DESTROYED the media with an insane move! Watch this video, you won't believe it. "
           "Hillary and the GOP are lying to America again, and nobody is talking about it. ") * 3


@pytest.fixture(autouse=True)
def load_real_model(monkeypatch):
    monkeypatch.setattr(config, "MODEL_PATH", REAL)
    model_service.load_model()
    yield
    model_service._pipeline = None


def test_risk_labels_match_model_classes():
    classes = {str(c).lower() for c in model_service._pipeline.classes_}
    assert classes & config.RISK_LABELS, f"RISK_LABELS {config.RISK_LABELS} match none of {classes}"


def test_risk_probability_is_produced_and_ordered():
    news = model_service.predict(NEWS, "Senate approves spending bill")
    opinion = model_service.predict(OPINION, "SHOCKING: Obama DESTROYS the media!!!")
    assert news.risk_probability is not None and opinion.risk_probability is not None
    assert opinion.risk_probability > news.risk_probability
