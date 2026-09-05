"""Pydantic request/response schemas for the API."""
import re
from typing import Literal

from pydantic import BaseModel, field_validator

_URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)


class AnalyzeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        url = value.strip()
        if not url:
            raise ValueError("url must not be empty")
        if not _URL_SCHEME_RE.match(url):
            url = f"https://{url}"
        return url


class HeadlineResult(BaseModel):
    headline: str
    trusted: Literal["Real", "Fake"]
    confidence: float


class AnalyzeResponse(BaseModel):
    url: str
    total: int
    real: int
    fake: int
    headlines: list[HeadlineResult]
