import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class FakeTaskResult:
    def __init__(self, state, result=None):
        self.state = state
        self.result = result


class FakeCeleryTask:
    def __init__(self):
        self.calls = []

    def apply_async(self, args=None, task_id=None, **_):
        self.calls.append({"args": args, "task_id": task_id})


@pytest.fixture
def fake_task(monkeypatch):
    task = FakeCeleryTask()
    monkeypatch.setattr("app.routers.analyze.analyze_url_task", task)
    return task


def test_health_endpoint(client):
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "Server is running!"}


def test_analyze_enqueues_task(client, fake_task):
    response = client.post("/api/analyze", json={"url": "https://example.com"})
    assert response.status_code == 202

    body = response.json()
    assert body["status"] == "queued"
    assert body["url"] == "https://example.com"
    uuid.UUID(body["task_id"])
    assert fake_task.calls[0]["args"] == ["https://example.com"]
    assert fake_task.calls[0]["task_id"] == body["task_id"]


def test_analyze_normalizes_url_without_scheme(client, fake_task):
    response = client.post("/api/analyze", json={"url": "example.com"})
    assert response.status_code == 202
    assert response.json()["url"] == "https://example.com"
    assert fake_task.calls[0]["args"] == ["https://example.com"]


def test_analyze_rejects_empty_url(client, fake_task):
    response = client.post("/api/analyze", json={"url": "   "})
    assert response.status_code == 422
    assert fake_task.calls == []


def test_analyze_status_success(client, monkeypatch):
    result_payload = {"url": "https://example.com", "total": 0, "real": 0, "fake": 0, "headlines": []}
    monkeypatch.setattr(
        "app.routers.analyze._task_result",
        lambda task_id: FakeTaskResult("SUCCESS", result_payload),
    )
    response = client.get("/api/analyze/abc")
    assert response.status_code == 200
    assert response.json() == {"task_id": "abc", "status": "SUCCESS", "result": result_payload}


def test_analyze_status_failure(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.analyze._task_result",
        lambda task_id: FakeTaskResult("FAILURE", Exception("boom")),
    )
    response = client.get("/api/analyze/abc")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILURE"
    assert "boom" in body["error"]


def test_analyze_status_pending(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.analyze._task_result",
        lambda task_id: FakeTaskResult("STARTED"),
    )
    response = client.get("/api/analyze/abc")
    assert response.json() == {"task_id": "abc", "status": "STARTED"}


@pytest.fixture
def ws_client(monkeypatch):
    async def not_finished(websocket, task_id):
        return False

    monkeypatch.setattr("app.routers.analyze._send_finished_or_none", not_finished)
    return TestClient(app)


def test_websocket_streams_events_in_order(ws_client, monkeypatch):
    async def fake_stream(task_id):
        yield {"type": "status", "stage": "scraping"}
        yield {"type": "status", "stage": "analyzing", "total": 1}
        yield {"type": "result", "result": {"url": "https://example.com", "total": 1, "real": 1, "fake": 0, "headlines": []}}

    monkeypatch.setattr("app.routers.analyze.stream.event_stream", fake_stream)

    with ws_client.websocket_connect("/ws/analyze/t1") as ws:
        assert ws.receive_json() == {"type": "status", "stage": "scraping"}
        assert ws.receive_json() == {"type": "status", "stage": "analyzing", "total": 1}
        assert ws.receive_json()["type"] == "result"
        with pytest.raises(Exception):
            ws.receive_json()  # server closed after terminal event


def test_websocket_streams_error_event(ws_client, monkeypatch):
    async def fake_stream(task_id):
        yield {"type": "error", "detail": "page failed to load"}

    monkeypatch.setattr("app.routers.analyze.stream.event_stream", fake_stream)

    with ws_client.websocket_connect("/ws/analyze/t1") as ws:
        assert ws.receive_json() == {"type": "error", "detail": "page failed to load"}


def test_websocket_sends_finished_result_immediately(client, monkeypatch):
    async def send_finished(websocket, task_id):
        await websocket.send_json({"type": "result", "result": {"url": "u", "total": 0}})
        return True

    monkeypatch.setattr("app.routers.analyze._send_finished_or_none", send_finished)

    with client.websocket_connect("/ws/analyze/t1") as ws:
        assert ws.receive_json() == {"type": "result", "result": {"url": "u", "total": 0}}
