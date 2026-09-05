"""URL analysis endpoints: async task enqueue, status polling, WebSocket streaming."""
import uuid

from celery.result import AsyncResult
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..celery_app import celery_app
from ..schemas import AnalyzeRequest
from ..services import stream
from ..tasks import analyze_url_task

router = APIRouter()


@router.post("/api/analyze", status_code=202)
def analyze(request: AnalyzeRequest) -> dict:
    """Validate the URL and enqueue the analysis as a Celery background task."""
    task_id = str(uuid.uuid4())
    analyze_url_task.apply_async(args=[request.url], task_id=task_id)
    return {"task_id": task_id, "status": "queued", "url": request.url}


def _task_result(task_id: str) -> AsyncResult:
    return AsyncResult(task_id, app=celery_app)


@router.get("/api/analyze/{task_id}")
def analyze_status(task_id: str) -> dict:
    """Return the current status and, if finished, the result or error."""
    try:
        result = _task_result(task_id)
    except Exception:
        return {"task_id": task_id, "status": "PENDING"}
    if result.state == "SUCCESS":
        return {"task_id": task_id, "status": "SUCCESS", "result": result.result}
    if result.state == "FAILURE":
        return {"task_id": task_id, "status": "FAILURE", "error": str(result.result)}
    return {"task_id": task_id, "status": result.state}


async def _send_finished_or_none(websocket: WebSocket, task_id: str) -> bool:
    """If the task already finished, send its terminal event and return True."""
    try:
        result = _task_result(task_id)
    except Exception:
        return False
    if result.state == "SUCCESS":
        await websocket.send_json({"type": "result", "result": result.result})
        return True
    if result.state == "FAILURE":
        await websocket.send_json({"type": "error", "detail": str(result.result)})
        return True
    return False


@router.websocket("/ws/analyze/{task_id}")
async def analyze_ws(websocket: WebSocket, task_id: str) -> None:
    """Stream task progress events to the client until the terminal event."""
    await websocket.accept()
    if await _send_finished_or_none(websocket, task_id):
        await websocket.close()
        return

    try:
        async for event in stream.event_stream(task_id):
            if event is None:
                if await _send_finished_or_none(websocket, task_id):
                    break
                continue
            await websocket.send_json(event)
            if event.get("type") in ("result", "error"):
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_json({"type": "error", "detail": str(exc)})
    finally:
        await websocket.close()
