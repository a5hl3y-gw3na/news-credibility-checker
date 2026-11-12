"""
Coordinates the different components of the news credibility assessment pipeline.
Each analysis component retains its own results. The combined score provides an overall summary of available signals.
"""
import logging
from app.services import nlp_service
from app import config
from app.schemas import AnalysisResponse, ArticleRequest, ModelResult, IndicatorResult, EvidenceResult
from app.services import evidence_service, language_service, metadata_service, model_service

logger = logging.getLogger(__name__)

DISCLAIMER = ("This system provides decision support, not a definitive truth detector. Warning signs are not proof an article is false, "
              "and the absence of warning signs is not proof it is accurate.")
LIMITATIONS = [
    "The classifier learns patterns in its training dataset, which may reflect writing style rather than the truth.",
    "Metadata, language, and NLP checks rely on heuristics and may be wrong.",
    "Evidence retrieval only finds fact-checks that already exist and supporting sources.",
    "The Combined score represents observed warning signs, not the probability that an article is false"
]

# Default scoring weights (adjusted to include NLP)
MODEL_WEIGHT = 0.40
METADATA_WEIGHT = 0.20
LANGUAGE_WEIGHT = 0.20
NLP_WEIGHT = 0.20

def calculate_score(model, metadata, language, nlp):
    #Calculates a weighted average using available analysis signals.
    #The model contributes only when a valid risk probability is available.
    parts = [
        (metadata.score, METADATA_WEIGHT),
        (language.score, LANGUAGE_WEIGHT),
        (nlp.score, NLP_WEIGHT)
    ]
    if model.available and model.risk_probability is not None:
        parts.append((model.risk_probability, MODEL_WEIGHT))
        
    total_weight = sum(weight for _, weight in parts)
    if total_weight == 0:
        return None
        
    weighted_score = sum(score * weight for score, weight in parts) / total_weight
    return round(weighted_score, 3)

def determine_assessment(score):
    #Converts the combined warning score into an assessment category.
    if score is None:
        return "unable_to_assess"
    if score < 0.33:
        return "lower_concern"
    if score < 0.66:
        return "some_concern"
    return "higher_concern"

def generate_summary(assessment):
    #Generates a user-friendly explanation of the overall assessment.
    summaries = {
        "lower_concern": ("Few warning signs were identified. "
            "However, independent verification is still recommended."),
        "some_concern": ("Some warning signs were identified. "
            "Review the analysis details and available evidence carefully."),
        "higher_concern": ("Several warning signs were identified. "
            "Verify the article using other reliable sources before relying on it."),
        "unable_to_assess": ("There was insufficient article information to produce "
            "a meaningful overall assessment.")
    }
    return summaries[assessment]

async def run(req: ArticleRequest) -> AnalysisResponse:
    #Executes the complete news credibility assessment pipeline.
    #Prepare article information
    article_text = req.text[:config.MAX_TEXT_CHARS]
    title = req.title or ""
    
    #Check whether enough article text is available
    if len(article_text.strip()) < config.MIN_TEXT_CHARS:
        logger.info("Insufficient article text for meaningful assessment.")
        return AnalysisResponse(
            assessment="unable_to_assess",
            summary=generate_summary("unable_to_assess"),
            combined_score=None,
            model=ModelResult(available=False,note="Insufficient article text for model prediction."),
            metadata=IndicatorResult(score=0.0,indicators=[]),
            language=IndicatorResult(score=0.0,indicators=[]),
            nlp=IndicatorResult(score=0.0,indicators=[]),
            evidence=EvidenceResult(status="insufficient_evidence", note="Insufficient article text for evidence retrieval."),
            limitations=LIMITATIONS,
            disclaimer=DISCLAIMER
        )
        
    #Run the individual analysis components
    try:
        model = model_service.predict(article_text, title)
    except Exception:
        logger.exception("Machine learning analysis failed.")
        model = ModelResult(available=False, note="Machine learning analysis is currently unavailable.")
        
    try:
        metadata = metadata_service.analyse(
            req.url,req.title,article_text,req.author,
            req.publish_date,req.site_name)
    except Exception:
        logger.exception("Metadata analysis failed.")
        metadata = IndicatorResult(score=0.0,indicators=[])
        
    try:
        language = language_service.analyse(title,article_text)
    except Exception:
        logger.exception("Language analysis failed.")
        language = IndicatorResult(score=0.0,indicators=[])
        
    try:
        nlp = nlp_service.analyse(title, article_text)
    except Exception:
        logger.exception("NLP analysis failed.")
        nlp = IndicatorResult(score=0.0,indicators=[])
        
    try:
        evidence = await evidence_service.retrieve(title,article_text,req.claims)
    except Exception:
        logger.exception("Evidence retrieval failed.")
        evidence = EvidenceResult(status="error",note="Evidence retrieval could not be completed.")
        
    #Calculate the combined warning score
    score = calculate_score(model, metadata, language, nlp)
    
    #Determine the overall assessment
    assessment = determine_assessment(score)
    
    #Generate the final explanation
    summary = generate_summary(assessment)
    
    #Return the consolidated response
    return AnalysisResponse(
        assessment=assessment,
        summary=summary,
        combined_score=score,
        model=model,
        metadata=metadata,
        language=language,
        nlp=nlp,
        evidence=evidence,
        limitations=LIMITATIONS,
        disclaimer=DISCLAIMER
    )