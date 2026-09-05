import pytest

from app.tasks import analyze_url_task

_SAMPLE_HTML = """
<html><body>
<h1>Major ransomware attack hits hospital network</h1>
<p>Some article body text.</p>
<h2>Security experts warn of new phishing campaign</h2>
<h2>Local sports team wins championship</h2>
</body></html>
"""


@pytest.fixture
def run_task(monkeypatch):
    events = []

    def fake_fetch(url):
        return _SAMPLE_HTML

    def fake_predict(headline):
        return ("Fake" if "phishing" in headline.lower() else "Real", 0.87)

    def fake_publish(task_id, event):
        events.append(event)

    monkeypatch.setattr("app.services.scraper.fetch_page", fake_fetch)
    monkeypatch.setattr("app.services.classifier.predict", fake_predict)
    monkeypatch.setattr("app.services.events.publish", fake_publish)
    monkeypatch.setattr("app.services.cache.cache_get", lambda url: None)
    monkeypatch.setattr("app.services.cache.cache_set", lambda url, payload: None)
    return events


def test_task_publishes_stages_and_result(run_task):
    payload = analyze_url_task.apply(args=["https://example.com"], throw=True).result

    assert payload["url"] == "https://example.com"
    assert payload["total"] == 3
    assert payload["real"] == 2
    assert payload["fake"] == 1
    assert len(payload["headlines"]) == 3

    events = run_task
    assert events[0] == {"type": "status", "stage": "scraping"}
    assert events[1] == {"type": "status", "stage": "analyzing", "total": 3}
    assert events[2]["type"] == "status" and events[2]["stage"] == "done"
    assert events[3] == {"type": "result", "result": payload}


def test_task_publishes_error_event_and_raises(monkeypatch):
    events = []

    def broken_fetch(url):
        raise TimeoutError("page did not load")

    monkeypatch.setattr("app.services.scraper.fetch_page", broken_fetch)
    monkeypatch.setattr("app.services.events.publish", lambda tid, event: events.append(event))
    monkeypatch.setattr("app.services.cache.cache_get", lambda url: None)
    monkeypatch.setattr("app.services.cache.cache_set", lambda url, payload: None)

    with pytest.raises(TimeoutError):
        analyze_url_task.apply(args=["https://example.com"], throw=True)

    assert events == [{"type": "status", "stage": "scraping"},
                      {"type": "error", "detail": "page did not load"}]


def test_task_applies_keyword_filter_when_enabled(run_task, monkeypatch):
    monkeypatch.setattr("app.config.settings.enable_keyword_filter", True)

    payload = analyze_url_task.apply(args=["https://example.com"], throw=True).result
    assert payload["total"] == 2  # ransomware + phishing headlines only


def test_task_stores_result_in_cache(run_task, monkeypatch):
    stored = {}

    def fake_cache_set(url, payload):
        stored[url] = payload

    monkeypatch.setattr("app.services.cache.cache_get", lambda url: None)
    monkeypatch.setattr("app.services.cache.cache_set", fake_cache_set)
    monkeypatch.setattr("app.config.settings.cache_ttl_seconds", 420)

    payload = analyze_url_task.apply(args=["https://example.com"], throw=True).result

    assert stored["https://example.com"] == payload


def test_task_returns_cached_result_without_scraping(run_task, monkeypatch):
    cached = {
        "url": "https://example.com",
        "total": 2,
        "real": 1,
        "fake": 1,
        "headlines": [
            {"headline": "Cached headline one", "trusted": "Real", "confidence": 0.9},
            {"headline": "Cached headline two", "trusted": "Fake", "confidence": 0.8},
        ],
    }
    fetched = []

    def fake_fetch(url):
        fetched.append(url)
        return "<html></html>"

    monkeypatch.setattr("app.services.scraper.fetch_page", fake_fetch)
    monkeypatch.setattr("app.services.cache.cache_get", lambda url: cached)
    monkeypatch.setattr("app.services.cache.cache_set", lambda url, payload: None)

    payload = analyze_url_task.apply(args=["https://example.com"], throw=True).result

    assert fetched == []  # scraper never called
    assert payload == cached
    assert [e["type"] for e in run_task] == ["status", "status", "status", "result"]
    assert run_task[0] == {"type": "status", "stage": "scraping"}
    assert run_task[1] == {"type": "status", "stage": "analyzing", "total": 2}
    assert run_task[2]["stage"] == "done"
