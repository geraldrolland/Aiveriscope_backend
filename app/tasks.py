"""Celery task that performs the headline analysis and streams progress."""
from celery import Task

from .celery_app import celery_app
from .config import settings
from .schemas import AnalyzeResponse, HeadlineResult
from .services import cache, classifier, events, preprocess, scraper


def analyze(url: str, task_id: str) -> dict:
    """Run the analysis pipeline and publish progress events."""
    events.publish(task_id, {"type": "status", "stage": "scraping"})

    cached = cache.cache_get(url)
    if cached is not None:
        events.publish(
            task_id, {"type": "status", "stage": "analyzing", "total": cached["total"]}
        )
        events.publish(
            task_id,
            {"type": "status", "stage": "done", "total": cached["total"],
             "real": cached["real"], "fake": cached["fake"]},
        )
        events.publish(task_id, {"type": "result", "result": cached})
        return cached

    html = scraper.fetch_page(url)

    headlines = preprocess.extract_headlines(html)
    if settings.enable_keyword_filter:
        headlines = preprocess.filter_cs_headlines(headlines, settings.cs_keywords)

    events.publish(task_id, {"type": "status", "stage": "analyzing", "total": len(headlines)})

    results = []
    for headline in headlines:
        trusted, confidence = classifier.predict(headline)
        results.append(
            HeadlineResult(headline=headline, trusted=trusted, confidence=confidence)
        )

    real = sum(1 for r in results if r.trusted == "Real")
    payload = AnalyzeResponse(
        url=url,
        total=len(results),
        real=real,
        fake=len(results) - real,
        headlines=results,
    ).model_dump()

    events.publish(
        task_id,
        {"type": "status", "stage": "done", "total": payload["total"],
         "real": payload["real"], "fake": payload["fake"]},
    )
    cache.cache_set(url, payload)
    events.publish(task_id, {"type": "result", "result": payload})
    return payload


@celery_app.task(name="analyze_url", bind=True)
def analyze_url_task(self: Task, url: str) -> dict:
    task_id = self.request.id
    try:
        return analyze(url, task_id)
    except Exception as exc:
        events.publish(task_id, {"type": "error", "detail": str(exc)})
        raise
