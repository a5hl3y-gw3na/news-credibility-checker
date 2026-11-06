"""
Loads and manages the saved scikit-learn classification pipeline.
The pipeline consists of TF-IDF vectorization and Logistic Regression.
It generates article classifications and associated risk probabilities.
"""
import os
import logging
from pathlib import Path
import joblib
from app import config
from app.schemas import ModelResult


logger = logging.getLogger(__name__)
_pipeline = None

def load_model() -> None:
    #Loads the trained machine-learning pipeline.The API can still operate without the classifier.
    global _pipeline
    #Reset the current model before attempting to load another.
    _pipeline = None
    model_path = Path(config.MODEL_PATH)

    if not model_path.is_file():
        logger.warning("No trained model found at %s. "
            "Classifier functionality will be unavailable.",model_path)
        return
    try:
        loaded_pipeline = joblib.load(model_path)
        #Verify that the loaded object supports the required operations.
        if not callable(getattr(loaded_pipeline, "predict_proba", None)):
            raise ValueError(
                "Loaded model does not support predict_proba().")
        if not hasattr(loaded_pipeline, "classes_"):
            raise ValueError(
                "Loaded model does not expose class labels.")

        _pipeline = loaded_pipeline
        logger.info("Machine-learning pipeline loaded successfully from %s",model_path)
        logger.info("Available classification labels: %s",list(_pipeline.classes_))
    except Exception:
        _pipeline = None
        logger.exception("Failed to load machine-learning pipeline from %s",model_path)

def is_loaded() -> bool:
    #Returns whether the trained classifier is available.
    return _pipeline is not None

def predict(text: str) -> ModelResult:
    #Classifies article text and calculates its risk probability.
    #Risk probability is determined using the labels defined in config.RISK_LABELS.

    if _pipeline is None:
        return ModelResult(available=False,note="Classifier is not currently loaded.")

    if len(text.strip()) < config.MIN_TEXT_CHARS:
        return ModelResult(available=False,
            note="Article text is too short for a meaningful prediction.")

    try:
        # Generate class probabilities.
        probabilities = _pipeline.predict_proba([text])[0]
        #Obtain the labels associated with the probabilities.
        classes = [str(label).lower()
            for label in _pipeline.classes_]

        probability_map = {label: round(float(probability), 4)
            for label, probability in zip(classes, probabilities)}
        # Identify the most likely classification.
        predicted_label = max(probability_map,key=probability_map.get)
        # Identify which model classes are considered risky.
        risk_labels = {str(label).lower()
            for label in config.RISK_LABELS}
        matching_labels = set(classes).intersection(risk_labels)

        if not matching_labels:
            logger.warning("None of the configured risk labels %s "
                "match the model classes %s.",risk_labels,classes)

            return ModelResult(available=True,predicted_label=predicted_label,
                probabilities=probability_map,risk_probability=None,
                note=("Prediction completed, but the configured risk "
                    "labels do not match the classifier's classes."))
        # Calculate the combined probability of risky classes.
        risk_probability = sum(probability_map[label]
                for label in matching_labels)

        return ModelResult(available=True,predicted_label=predicted_label,
            probabilities=probability_map,risk_probability=round(risk_probability, 4),
            note=("Prediction reflects patterns learned from the "
                "training dataset, not independently verified truth."))
    except Exception:
        logger.exception("Machine-learning prediction failed.")

        return ModelResult(available=False,note="The classifier encountered an error during prediction.")
