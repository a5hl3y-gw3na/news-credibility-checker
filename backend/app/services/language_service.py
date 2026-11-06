"""
Identifies selected language patterns that may warrant closer inspection.
These indicators are heuristic signals, not proof of misinformation.
The NLP component can extend and refine the lexicon over time.
"""
import re
from app.schemas import Indicator, IndicatorResult

# Starter lexicon. The NLP/evidence component can refine these terms as the project develops.

LEXICON = {
    "sensational": ["shocking","bombshell","outrageous","unbelievable","explosive","devastating","horrifying"],
    "clickbait": ["you won't believe","what happens next","doctors hate","this one trick","will blow your mind"],
    "absolute": ["always","never","everyone","nobody","100%","undeniable","they don't want you to know"]
}

def analyse(title: str | None, text: str) -> IndicatorResult:
    """
    Examines article wording for selected language patterns.
    Returns:IndicatorResult containing detected indicators and an overall language-warning score.
    """
    full_text = f"{title or ''}\n{text}"
    lower_text = full_text.lower()
    indicators: list[Indicator] = []
    score = 0.0
    #Detect selected wording patterns
    for category, terms in LEXICON.items():
        hits = sorted({term
            for term in terms
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)",lower_text)})
        if hits:
            score += min(len(hits), 3) / 3 * 0.25

            indicators.append(Indicator(id=category,severity="warning",
                    message=(
                        f"{category.capitalize()} wording found: "f"{', '.join(hits[:5])}.")))
    #Detect excessive use of uppercase words
    words = re.findall(r"\b[A-Za-z']+\b", full_text)
    capitalised_words = [word
        for word in words
        if len(word) > 3 and word.isupper()]
    if words and len(capitalised_words) / len(words) > 0.05:
        score += 0.15

        indicators.append(Indicator(id="all_caps",severity="warning",
                message=("Frequent uppercase wording detected "
                         f"({len(capitalised_words)} words).")))
    #Detect repeated exclamation marks
    exclamation_count = full_text.count("!")
    if exclamation_count >= 3:
        score += 0.15
        indicators.append(Indicator(id="exclamations",severity="warning",
                message=(
                    f"{exclamation_count} exclamation marks detected.")))
    #Report when no selected patterns are detected
    if not indicators:
        indicators.append(Indicator(id="none",severity="info",
                message="No selected language warning patterns were found."))
    #Keep score within the permitted range
    score = round(min(score, 1.0), 3)

    return IndicatorResult(score=score,indicators=indicators)
