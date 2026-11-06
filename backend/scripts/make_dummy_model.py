"""PLACEHOLDER model so backend/extension can be integrated before the AI lead's real model exists.
Trained on toy sentences - predictions are meaningless. Replace models/baseline.joblib with the real
pipeline (an sklearn Pipeline supporting predict_proba). Run from backend/: python scripts/make_dummy_model.py"""
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

X = ["officials confirmed the budget figures in a statement", "the committee published its annual report",
     "researchers reported the findings in a journal", "shocking bombshell you won't believe what they hid",
     "outrageous secret they don't want you to know", "unbelievable explosive claim everyone must share"]
y = ["real", "real", "real", "fake", "fake", "fake"]
joblib.dump(make_pipeline(TfidfVectorizer(), LogisticRegression()).fit(X, y), "models/baseline.joblib")
print("Saved models/baseline.joblib (DUMMY)")
