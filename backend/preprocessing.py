"""Text cleaning. MUST stay identical to clean_text() and STRIP_PATTERNS in the
training notebook (Step 4), otherwise the model sees different text at
prediction time than it saw during training."""
import re

STRIP_PATTERNS = [
    r"^.{0,120}?\(Reuters\)\s*-?\s*",            # dateline such as "WASHINGTON (Reuters) -"
    r"(?i)\breuters\b",                           # any remaining mention of the publisher
    r"(?i)featured image( via)?[^.\n]*",          # common fake-site image credits
    r"(?i)(getty|screenshot|image) (images|via)[^.\n]*",
    r"https?://\S+",                              # URLs
    r"@\w+",                                      # handles
    r"(?i)pic\.twitter\.com/\S+",                 # embedded-tweet links
    r"(?i)\b(?:www\.)?[a-z0-9\-]+\.(?:com|org|net)\b\S*",   # bare web addresses
]


def clean_text(s) -> str:
    s = "" if s is None else str(s)
    for p in STRIP_PATTERNS:
        s = re.sub(p, " ", s)
    return re.sub(r"\s+", " ", s).strip()
