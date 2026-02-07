from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

DEFAULT_KEYWORDS = [
    "public health", "health disparities", "food insecurity",
    "community health", "nutrition", "epidemiology",
]
DEFAULT_DISCIPLINES = [
    "public health", "epidemiology", "social sciences", "life sciences",
]


@dataclass
class Config:
    keywords: list[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    disciplines: list[str] = field(default_factory=lambda: list(DEFAULT_DISCIPLINES))
    academic_level: str = "phd_student"
    citizenship: str = "us_citizen"
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    sender_email: str = ""
    recipient_email: str = ""
    score_threshold: int = 10


def load_config() -> Config:
    profile_json = os.environ.get("PROFILE_JSON", "")
    profile = json.loads(profile_json) if profile_json else {}

    kwargs: dict = {}
    if "keywords" in profile:
        kwargs["keywords"] = profile["keywords"]
    if "disciplines" in profile:
        kwargs["disciplines"] = profile["disciplines"]
    if "academic_level" in profile:
        kwargs["academic_level"] = profile["academic_level"]
    if "citizenship" in profile:
        kwargs["citizenship"] = profile["citizenship"]
    if "score_threshold" in profile:
        kwargs["score_threshold"] = int(profile["score_threshold"])

    kwargs["gmail_client_id"] = os.environ.get("GMAIL_CLIENT_ID", "")
    kwargs["gmail_client_secret"] = os.environ.get("GMAIL_CLIENT_SECRET", "")
    kwargs["gmail_refresh_token"] = os.environ.get("GMAIL_REFRESH_TOKEN", "")
    kwargs["sender_email"] = os.environ.get("SENDER_EMAIL", "")
    kwargs["recipient_email"] = os.environ.get("RECIPIENT_EMAIL", "")

    return Config(**kwargs)
