"""
Retrieves existing fact-checking evidence for selected article claims.
Default provider: Google Fact Check Tools API. An API key is required.
Additional providers can be registered in PROVIDERS.
Each provider must implement:
    async def provider(claim: str) -> list[EvidenceItem]
"""
import logging
import re
import httpx
from app import config
from app.schemas import EvidenceItem, EvidenceResult


logger = logging.getLogger(__name__)
FACTCHECK_URL = ("https://factchecktools.googleapis.com/v1alpha1/claims:search")

def extract_claims(title: str | None,text: str,max_claims: int = 3) -> list[str]:
    """
    Selects possible factual claims using simple text heuristics.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    cues = re.compile(r'\d|["\u201c]|\b(said|says|claims?|according to|reported|found that)\b',re.IGNORECASE)
    selected = []
    # Include the article headline where available.
    if title and title.strip():
        selected.append(title.strip())
    # Select sentences containing possible factual claim indicators.
    for sentence in sentences:
        sentence = sentence.strip()
        if (
            40 <= len(sentence) <= 300 and cues.search(sentence) and sentence not in selected):
            selected.append(sentence)
        if len(selected) >= max_claims:
            break
    # Remove duplicates while preserving their original order.
    return list(dict.fromkeys(selected))[:max_claims]

async def factcheck_provider(claim: str) -> list[EvidenceItem]:
    #Searches Google Fact Check Tools for existing reviews of a claim.
    params = {"query": claim[:200],"key": config.FACTCHECK_API_KEY,"pageSize": 3}
    async with httpx.AsyncClient(timeout=config.EVIDENCE_TIMEOUT_S) as client:
        response = await client.get(FACTCHECK_URL,params=params)
        response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected evidence API response.")

    items = []
    for result in data.get("claims", []):
        if not isinstance(result, dict):
            continue
        reviews = result.get("claimReview", [])
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            if not isinstance(review, dict):
                continue
            publisher = review.get("publisher") or {}
            if not isinstance(publisher, dict):
                publisher = {}
            items.append(EvidenceItem(claim=claim,source_name=publisher.get("name") or "Unknown",
                    url=review.get("url") or "",title=review.get("title"),
                    rating=review.get("textualRating"),date=review.get("reviewDate")))
    return items
# Providers can be extended by the NLP/evidence component.
PROVIDERS = [factcheck_provider]

async def retrieve(title: str | None,text: str,user_claims: list[str]) -> EvidenceResult:
#Retrieves fact-checking evidence for up to three claims.Article content and retrieved results are processed in memory only.
    if not config.FACTCHECK_API_KEY:
        return EvidenceResult(status="not_configured",
            note=("No evidence provider is configured. "
                "External fact-checking could not be performed."))
    #Use supplied claims where available; otherwise extract them.
    claims = [claim.strip()
        for claim in user_claims[:3]
        if claim and claim.strip()]

    if not claims:
        claims = extract_claims(title, text)

    #Remove duplicate claims.
    claims = list(dict.fromkeys(claims))[:3]

    if not claims:
        return EvidenceResult(status="insufficient_evidence",
            note="No suitable claims were identified for fact-checking.")

    found: list[EvidenceItem] = []
    successful_lookups = 0
    failed_lookups = 0
    #Query each registered provider.
    for claim in claims:
        for provider in PROVIDERS:
            try:
                results = await provider(claim)
                successful_lookups += 1

                if results:
                    found.extend(results)
            except Exception:
                failed_lookups += 1
                # Do not log article claims or request contents.
                logger.warning("Evidence provider %s failed during lookup.",provider.__name__)
    #Remove duplicate evidence records.
    unique_items = []
    seen = set()
    for item in found:
        identifier = (item.claim,item.source_name,item.url,item.title)
        if identifier not in seen:
            seen.add(identifier)
            unique_items.append(item)
    #Determine the retrieval outcome.
    if unique_items:
        note = ""
        if failed_lookups:
            note = (
                "Some evidence provider lookups failed. ""The available results may be incomplete.")

        return EvidenceResult(status="found",claims_checked=claims,items=unique_items,note=note)

    if successful_lookups == 0 and failed_lookups > 0:
        return EvidenceResult(status="error",claims_checked=claims,
            note="Evidence providers could not complete the requested lookups.")

    return EvidenceResult(status="insufficient_evidence",claims_checked=claims,
        note=("No matching fact-checks were found. "
            "This does not establish whether the claims are true or false."))
