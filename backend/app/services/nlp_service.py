"""
NLP analysis for the News Credibility Checker.

Adds an independent linguistic signal alongside the ML model, metadata and
language services. It uses only the standard library (no NLTK / spaCy), so it
works offline and needs no extra dependencies.

What it does
------------
1. Text statistics   - length, readability (Flesch), lexical diversity.
2. Writing patterns  - emotional / conspiratorial wording, calls to share,
                       vague sourcing, opinion language, repetition.
3. Headline checks   - clickbait patterns and headline-vs-body mismatch.
4. Attribution       - how much of the article cites a source or a quotation.
5. Claim extraction  - ranks check-worthy sentences for evidence_service.
6. Entity extraction - frequent names / places (capitalised phrases).

Like language_service, every result is a heuristic warning sign, NOT proof that
an article is false. Indicator ids here are different from language_service
(which already covers sensational / clickbait / absolute wording, ALL CAPS and
exclamation marks), so the two can run side by side without double counting.

Public API
----------
analyse(title, text)           -> IndicatorResult   (same shape as language_service)
analyse_detailed(title, text)  -> dict              (indicators + statistics + claims + entities)
extract_claims(title, text, max_claims=3) -> list[str]
extract_entities(text, limit=8)           -> list[tuple[str, int]]
text_statistics(text)                     -> dict
split_sentences(text) / tokenize(text)    -> helpers
"""
from __future__ import annotations

import math
import re
from collections import Counter

from app.schemas import Indicator, IndicatorResult

# --------------------------------------------------------------------------- #
# Lexicons. Lower-case, straight apostrophes. Extend these as the project grows.
# --------------------------------------------------------------------------- #
LEXICONS: dict[str, list[str]] = {
    "emotional": [
        "outrage", "outraged", "furious", "disgusting", "disgraceful", "sickening",
        "appalling", "traitor", "traitors", "nightmare", "terrifying", "horrific",
        "slams", "blasts", "destroys", "eviscerates", "meltdown", "betrayal",
    ],
    "conspiratorial": [
        "mainstream media", "msm", "cover-up", "cover up", "wake up", "sheeple",
        "deep state", "hoax", "hidden truth", "they are lying", "they're lying",
        "what they don't tell you", "what they aren't telling you", "globalist",
        "globalists", "puppet masters", "false flag", "crisis actor",
        "crisis actors", "big pharma", "new world order",
    ],
    "call_to_share": [
        "share this", "share before", "spread the word", "before it's deleted",
        "before it gets deleted", "before it's taken down", "must share",
        "pass this on", "forward this", "like and share", "share if you",
        "tell everyone", "going viral",
    ],
    "vague_sourcing": [
        "sources say", "sources claim", "some say", "many people say",
        "people are saying", "it is believed", "it is rumoured", "it is rumored",
        "rumour has it", "rumor has it", "insiders", "an anonymous source",
        "unnamed sources", "experts say", "experts believe", "critics say",
        "reportedly", "allegedly", "some experts", "studies show",
        "scientists say", "they say", "everyone knows", "it is said",
    ],
    "opinion": [
        "i think", "i believe", "in my opinion", "in my view", "clearly",
        "obviously", "of course", "frankly", "needless to say", "it is obvious",
        "as we all know", "we all know", "i feel", "let's be honest",
    ],
}

HEADLINE_PATTERNS = [
    r"^\s*\d+\s+(things|reasons|ways|facts|secrets|signs|tricks|tips|photos|people|celebrities)\b",
    r"\byou (need to|have to|must|should) (see|know|watch|read)\b",
    r"\bthis is (why|how|what)\b",
    r"\bhere'?s (why|what|how)\b",
    r"\bthe (truth|real reason) (about|behind)\b",
    r"\bwill (shock|amaze|surprise|blow)\b",
    r"\b(jaw|mind|heart)[- ](dropping|blowing|stopping)\b",
    r"\b(won't|will not|can't|cannot) believe\b",
]

ATTRIBUTION_CUES = re.compile(
    r"\b(said|says|told|according to|announced|confirmed|stated|statement|"
    r"spokes(?:man|woman|person)|reported|testified|wrote|added|noted|explained|"
    r"study|survey|press release|data from|officials?)\b",
    re.IGNORECASE,
)

STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before
being below between both but by can could did do does doing down during each few for from
further had has have having he her here hers him his how i if in into is it its just me more
most my no nor not now of off on once only or other our out over own same she should so some
such than that the their them then there these they this those through to too under until up
us very was we were what when where which while who whom why will with would you your said
says new one two""".split())

_IGNORED_ENTITIES = frozenset({
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "the", "this", "that",
    "he", "she", "it", "they", "we", "i", "in", "on", "at", "a", "an", "mr",
    "mrs", "ms", "dr", "officials", "according",
})

_ABBREV_END = re.compile(
    r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|Sen|Rep|Gov|Gen|Col|Lt|St|Jr|Sr|vs|Inc|Ltd|Co|No))\.$"
)
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_ENTITY = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b")
_QUOTE = re.compile(r'["\u201c][^"\u201d]{3,}["\u201d]')
_NUMBER = re.compile(r"\b\d[\d,.]*%?")

# Compile each lexicon once as a single alternation (longest phrase first).
_LEXICON_REGEX = {
    name: re.compile(
        r"(?<!\w)(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r")(?!\w)"
    )
    for name, terms in LEXICONS.items()
}
_HEADLINE_REGEX = [re.compile(p, re.IGNORECASE) for p in HEADLINE_PATTERNS]


# --------------------------------------------------------------------------- #
# Basic text helpers
# --------------------------------------------------------------------------- #
def _normalise(text: str | None) -> str:
    """Straighten curly apostrophes so lexicon matching is consistent."""
    return (text or "").replace("\u2019", "'").replace("\u2018", "'")


def split_sentences(text: str) -> list[str]:
    """Rule-based sentence splitter that avoids breaking on common abbreviations."""
    pieces = re.split(r"(?<=[.!?])\s+", _normalise(text).strip())
    sentences: list[str] = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if sentences and _ABBREV_END.search(sentences[-1]):
            sentences[-1] += " " + piece
        else:
            sentences.append(piece)
    return sentences


def tokenize(text: str) -> list[str]:
    """Lower-cased word tokens."""
    return [w.lower() for w in _WORD.findall(_normalise(text))]


def _stem(word: str) -> str:
    """Very light suffix stripping, enough for headline/body word matching."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _count_syllables(word: str) -> int:
    word = word.lower()
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def _lexical_diversity(tokens: list[str]) -> float:
    """Moving-average type/token ratio (window 100); plain TTR for short texts."""
    if not tokens:
        return 0.0
    window = 100
    if len(tokens) <= window:
        return len(set(tokens)) / len(tokens)
    ratios = [
        len(set(tokens[i:i + window])) / window
        for i in range(0, len(tokens) - window + 1, 50)
    ]
    return sum(ratios) / len(ratios)


def _find_hits(lexicon: str, lower_text: str) -> list[str]:
    return sorted(set(_LEXICON_REGEX[lexicon].findall(lower_text)))


# --------------------------------------------------------------------------- #
# Statistics, entities, claims
# --------------------------------------------------------------------------- #
def text_statistics(text: str) -> dict:
    """Descriptive statistics used by the indicators (and handy for the report)."""
    sentences = split_sentences(text)
    tokens = tokenize(text)
    n_words, n_sent = len(tokens), len(sentences)
    if not n_words or not n_sent:
        return {"words": n_words, "sentences": n_sent, "avg_sentence_length": 0.0,
                "avg_word_length": 0.0, "lexical_diversity": 0.0,
                "flesch_reading_ease": None, "quotations": 0, "numbers": 0,
                "attribution_ratio": 0.0}

    syllables = sum(_count_syllables(w) for w in tokens)
    flesch = 206.835 - 1.015 * (n_words / n_sent) - 84.6 * (syllables / n_words)
    attributed = sum(1 for s in sentences if ATTRIBUTION_CUES.search(s) or _QUOTE.search(s))
    return {
        "words": n_words,
        "sentences": n_sent,
        "avg_sentence_length": round(n_words / n_sent, 2),
        "avg_word_length": round(sum(len(w) for w in tokens) / n_words, 2),
        "lexical_diversity": round(_lexical_diversity(tokens), 3),
        "flesch_reading_ease": round(flesch, 1),
        "quotations": len(_QUOTE.findall(text)),
        "numbers": len(_NUMBER.findall(text)),
        "attribution_ratio": round(attributed / n_sent, 3),
    }


def extract_entities(text: str, limit: int = 8) -> list[tuple[str, int]]:
    """Most frequent capitalised phrases (people, organisations, places)."""
    counts: Counter[str] = Counter()
    for sentence in split_sentences(text):
        for match in _ENTITY.finditer(sentence):
            phrase = match.group(0)
            single = " " not in phrase
            if single and (match.start() == 0 or phrase.lower() in _IGNORED_ENTITIES):
                continue  # sentence-initial capital or common word
            if phrase.lower() in _IGNORED_ENTITIES:
                continue
            counts[phrase] += 1
    return counts.most_common(limit)


def _check_worthiness(sentence: str) -> float:
    """Heuristic score for how checkable / factual a sentence looks."""
    lower = sentence.lower()
    score = 0.0
    if _NUMBER.search(sentence):
        score += 2.0
    if ATTRIBUTION_CUES.search(sentence):
        score += 2.0
    if _QUOTE.search(sentence):
        score += 1.0
    entities = sum(
        1 for m in _ENTITY.finditer(sentence)
        if m.start() > 0 and m.group(0).lower() not in _IGNORED_ENTITIES
    )
    score += min(entities, 3) * 0.5
    if sentence.rstrip().endswith("?"):
        score -= 2.0
    if _LEXICON_REGEX["opinion"].search(lower) or _LEXICON_REGEX["vague_sourcing"].search(lower):
        score -= 1.5
    return score


def extract_claims(title: str | None, text: str, max_claims: int = 3) -> list[str]:
    """
    Picks the most check-worthy sentences. Drop-in replacement for
    evidence_service.extract_claims (same arguments and return type).
    """
    claims: list[str] = []
    title = (title or "").strip()
    if (len(title.split()) >= 4 and not title.endswith("?")
            and not any(p.search(title) for p in _HEADLINE_REGEX)):
        claims.append(title)  # clickbait or question headlines are not factual claims

    scored = []
    for index, sentence in enumerate(split_sentences(text)):
        sentence = sentence.strip()
        if 40 <= len(sentence) <= 300:
            score = _check_worthiness(sentence)
            if score >= 2.0 and sentence not in claims:
                scored.append((score, index, sentence))

    room = max(max_claims - len(claims), 0)
    best = sorted(scored, key=lambda item: (-item[0], item[1]))[:room]
    claims.extend(sentence for _, _, sentence in sorted(best, key=lambda item: item[1]))
    return list(dict.fromkeys(claims))[:max_claims]


# --------------------------------------------------------------------------- #
# Headline analysis
# --------------------------------------------------------------------------- #
def _headline_coverage(title: str, text: str) -> float | None:
    """Share of the headline's content words that also appear in the article body."""
    title_words = {_stem(w) for w in tokenize(title) if w not in STOPWORDS and len(w) > 2}
    if len(title_words) < 3:
        return None
    body_words = {_stem(w) for w in tokenize(text)}
    return len(title_words & body_words) / len(title_words)


# --------------------------------------------------------------------------- #
# Main analysis
# --------------------------------------------------------------------------- #
def _run(title: str | None, text: str) -> tuple[IndicatorResult, dict]:
    title = _normalise(title).strip()
    text = _normalise(text)
    lower = f"{title}\n{text}".lower()
    stats = text_statistics(text)
    indicators: list[Indicator] = []
    score = 0.0

    def add(indicator_id: str, severity: str, message: str, weight: float = 0.0) -> None:
        nonlocal score
        indicators.append(Indicator(id=indicator_id, severity=severity, message=message))
        score += weight

    def listing(hits: list[str]) -> str:
        return ", ".join(hits[:5])

    # 1. Emotionally loaded wording (needs 2+ distinct terms to avoid one-off false alarms)
    emotional = _find_hits("emotional", lower)
    if len(emotional) >= 2:
        add("emotional_language", "warning",
            f"Emotionally charged wording found: {listing(emotional)}.",
            min(len(emotional), 4) / 4 * 0.20)

    # 2. Conspiratorial framing
    conspiratorial = _find_hits("conspiratorial", lower)
    if conspiratorial:
        add("conspiratorial_framing", "warning",
            f"Conspiracy-style phrasing found: {listing(conspiratorial)}.",
            min(len(conspiratorial), 3) / 3 * 0.25)

    # 3. Calls to share
    sharing = _find_hits("call_to_share", lower)
    if sharing:
        add("call_to_share", "warning",
            f"The text urges readers to share it: {listing(sharing)}.", 0.20)

    # 4. Vague sourcing
    vague = _find_hits("vague_sourcing", lower)
    if len(vague) >= 2:
        add("vague_sourcing", "warning",
            f"Claims rely on unnamed or vague sources: {listing(vague)}.",
            min(len(vague), 4) / 4 * 0.20)

    # 5. Opinion framing in what should be a news report
    opinion = _find_hits("opinion", lower)
    if len(opinion) >= 3:
        add("opinion_language", "warning",
            f"Opinion-style wording is frequent: {listing(opinion)}.", 0.10)

    # 6. Attribution: does a long article cite anyone at all?
    if stats["sentences"] >= 8:
        if stats["attribution_ratio"] == 0:
            add("few_attributions", "warning",
                "No sentence names a source, statement or quotation.", 0.20)
        else:
            add("attribution", "info",
                f"{round(stats['attribution_ratio'] * 100)}% of sentences cite a source "
                f"or quotation ({stats['quotations']} quotation(s)).")

    # 7. Headline checks
    if title:
        if any(p.search(title) for p in _HEADLINE_REGEX):
            add("headline_pattern", "warning",
                "The headline uses a common clickbait pattern.", 0.15)
        if title.endswith("?"):
            add("question_headline", "info",
                "The headline is phrased as a question; the article may not actually answer it.")
        coverage = _headline_coverage(title, text)
        if coverage is not None and stats["words"] >= 80 and coverage < 0.30:
            add("headline_mismatch", "warning",
                f"Only {round(coverage * 100)}% of the headline's key words appear in the article body.",
                0.20)

    # 8. Repetition (copy-pasted or padded text)
    sentences = [s.lower() for s in split_sentences(text) if len(s.split()) >= 5]
    if len(sentences) >= 6:
        duplicate_ratio = 1 - len(set(sentences)) / len(sentences)
        if duplicate_ratio >= 0.15:
            add("repetitive_text", "warning",
                f"{round(duplicate_ratio * 100)}% of sentences are repeated.", 0.10)

    # 9. Readability (informational only: complexity is not a credibility signal by itself)
    if stats["words"] >= 50 and stats["flesch_reading_ease"] is not None:
        flesch = stats["flesch_reading_ease"]
        level = ("very easy" if flesch >= 80 else "easy" if flesch >= 60
                 else "standard" if flesch >= 40 else "difficult")
        add("readability", "info",
            f"Reading level: {level} (Flesch {flesch}); "
            f"average sentence length {stats['avg_sentence_length']} words.")

    if not any(i.severity == "warning" for i in indicators):
        add("nlp_none", "info", "No NLP warning patterns were found.")

    return IndicatorResult(score=round(min(score, 1.0), 3), indicators=indicators), stats


def analyse(title: str | None, text: str) -> IndicatorResult:
    """Run the NLP checks. Returns the same IndicatorResult shape as language_service."""
    return _run(title, text)[0]


def analyse_detailed(title: str | None, text: str) -> dict:
    """Full output for notebooks, reports and debugging."""
    result, stats = _run(title, text)
    return {
        "result": result,
        "statistics": stats,
        "claims": extract_claims(title, text),
        "entities": extract_entities(text),
    }
