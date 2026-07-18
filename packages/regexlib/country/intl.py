import re
from re import Pattern
from typing import Final

COMMON_PATTERNS: Final[dict[str, Pattern[str]]] = {
    "dates": re.compile(
        r"(?i)(?:[0-3]?\d(?:st|nd|rd|th)?\s+(?:of\s+)?"
        r"(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|"
        r"jun\.?|june|jul\.?|july|aug\.?|august|sep\.?|september|oct\.?|october|"
        r"nov\.?|november|dec\.?|december)|"
        r"(?:jan\.?|january|feb\.?|february|mar\.?|march|apr\.?|april|may|"
        r"jun\.?|june|jul\.?|july|aug\.?|august|sep\.?|september|oct\.?|october|"
        r"nov\.?|november|dec\.?|december)\s+[0-3]?\d(?:st|nd|rd|th)?)"
        r"(?:,)?\s*(?:\d{4})?|[0-3]?\d[-\./][0-3]?\d[-\./]\d{2,4}"
    ),
    "times": re.compile(r"(?i)\b(?:\d{1,2}:\d{2}\s?(?:[ap]\.?m\.?)|\d[ap]\.?m\.?)\b"),
    "emails": re.compile(
        r"(?i)[A-Za-z0-9!#$%&'*+/=?^_{|.}~-]+@"
        r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
        r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    ),
    "ipv4": re.compile(
        r"\b(?:25[0-5]|2[0-4]\d|[01]?\d?\d)"
        r"(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d?\d)){3}\b"
    ),
    "md5_hash": re.compile(r"\b[0-9a-fA-F]{32}\b"),
    "sha1_hash": re.compile(r"\b[0-9a-fA-F]{40}\b"),
    "sha256_hash": re.compile(r"\b[0-9a-fA-F]{64}\b"),
    "credit_card": re.compile(r"(?<!\d)(?:\d{4}[- ]?){3}\d{4}(?!\d)"),
    "git_repo": re.compile(r"(?:git|ssh|https?)://[^\s]+\.git\b"),
}
