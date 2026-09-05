"""NLP text cleaning and headline extraction."""
import re
from functools import lru_cache

import nltk
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


@lru_cache(maxsize=None)
def _stop_words() -> frozenset:
    return frozenset(stopwords.words("english"))


@lru_cache(maxsize=None)
def _lemmatizer() -> WordNetLemmatizer:
    return WordNetLemmatizer()


def clean_text(text: str) -> str:
    """Lowercase, strip non-alphabetic characters, remove stopwords and lemmatize."""
    text = str(text).lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens = nltk.word_tokenize(text)
    tokens = [_lemmatizer().lemmatize(w) for w in tokens if w not in _stop_words()]
    return " ".join(tokens)


def extract_headlines(html: str) -> list[str]:
    """Extract non-empty heading texts (h1-h6) from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    headlines = [
        heading.text.strip()
        for tag in _HEADING_TAGS
        for heading in soup.find_all(tag)
    ]
    return [h for h in headlines if h]


def filter_cs_headlines(headlines: list[str], keywords: list[str]) -> list[str]:
    """Keep only headlines mentioning any of the given cyber-security keywords."""
    return [h for h in headlines if any(kw in h.lower() for kw in keywords)]
