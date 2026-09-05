"""Shared text cleaning used by training. Mirrors backend/app/services/preprocess.py."""
import re
from functools import lru_cache

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


@lru_cache(maxsize=None)
def _stop_words() -> frozenset:
    return frozenset(stopwords.words("english"))


@lru_cache(maxsize=None)
def _lemmatizer() -> WordNetLemmatizer:
    return WordNetLemmatizer()


def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens = nltk.word_tokenize(text)
    tokens = [_lemmatizer().lemmatize(w) for w in tokens if w not in _stop_words()]
    return " ".join(tokens)
