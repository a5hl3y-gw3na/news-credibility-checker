#Checks the availability and basic validity of article metadata. Missing or unusual metadata may indicate a warning sign,
#but does not establish that an article is unreliable.
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser
from app import config
from app.schemas import Indicator, IndicatorResult


def analyse(url: str,title: str | None,text: str,author: str | None,
    publish_date: str | None,site_name: str | None) -> IndicatorResult:

    indicators: list[Indicator] = []
    warnings = 0
    def add(indicator_id: str, severity: str, message: str):
        nonlocal warnings

        indicators.append(Indicator(id=indicator_id,severity=severity,message=message))

        if severity == "warning":
            warnings += 1
    # 1. Validate the article URL
    try:
        parsed = urlparse(url.strip())
        if (parsed.scheme not in ("http", "https") or not parsed.hostname):
            add("bad_url","warning","The article URL is missing a valid web address.")
        else:
            if parsed.scheme != "https":
                add("no_https","warning","Page is not served over HTTPS.")

            domain = parsed.hostname.lower().removeprefix("www.")
            add("domain","info",f"Publisher domain: {domain}")
    except (ValueError, AttributeError):
        add("bad_url","warning","The article URL could not be interpreted.")
    #Check publisher and author information
    if not (author or "").strip():
        add("no_author","warning","No author was found on the page.")
    if not (site_name or "").strip():
        add("no_site_name","info","No publisher name was declared in page metadata.")
    #Check the article headline
    if not (title or "").strip():
        add("no_title","warning","No headline was found.")
    #Check publication date
    if not (publish_date or "").strip():
        add("no_date","warning","No publication date was found.")
    else:
        try:
            publication_datetime = dateparser.parse(publish_date)

            if publication_datetime is None:
                raise ValueError("Unrecognised publication date.")

            if publication_datetime.tzinfo is None:
                publication_datetime = publication_datetime.replace(tzinfo=timezone.utc)

            current_datetime = datetime.now(timezone.utc)
            age = (current_datetime - publication_datetime.astimezone(timezone.utc)).days

            if age < 0:
                add("future_date","warning","The publication date appears to be in the future.")
            else:
                add("date","info",f"Published approximately {age} day(s) ago.")
        except (ValueError, OverflowError, TypeError):
            add("bad_date","warning","Publication date could not be interpreted.")
    #Check extracted article text
    if len(text.strip()) < config.MIN_TEXT_CHARS:
        add("short_text","warning","Very little article text was available for analysis.")
    #Calculate metadata warning score
    score = round(min(warnings / 5, 1.0), 3)

    return IndicatorResult(score=score,indicators=indicators)
