import pytest

from app.services import preprocess


def test_clean_text_lowercases_and_removes_stopwords():
    cleaned = preprocess.clean_text("The Hacker News Reports Ransomware Attack")
    tokens = cleaned.split()
    assert "the" not in tokens
    assert all(word.islower() for word in tokens)
    assert "ransomware" in tokens
    assert "attack" in tokens


def test_clean_text_strips_punctuation_and_digits():
    cleaned = preprocess.clean_text("Phishing 2024: Beware! (SMS scams) #1")
    assert "2024" not in cleaned
    assert "!" not in cleaned
    assert "#" not in cleaned


def test_clean_text_lemmatizes():
    cleaned = preprocess.clean_text("Attacks attackers attacked systems")
    tokens = cleaned.split()
    assert "attacks" not in tokens
    assert "attack" in tokens


def test_extract_headlines_finds_heading_tags():
    html = "<h1>Title One</h1><p>body</p><h2>Sub Two</h2><h3></h3>"
    assert preprocess.extract_headlines(html) == ["Title One", "Sub Two"]


def test_filter_cs_headlines_keyword_match_case_insensitive():
    headlines = ["Big data breach at bank", "Weather forecast today", "Cyber attack warning"]
    filtered = preprocess.filter_cs_headlines(headlines, ["breach", "cyber"])
    assert filtered == ["Big data breach at bank", "Cyber attack warning"]
