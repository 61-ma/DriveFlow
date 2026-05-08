from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import MessageRequest, RevisionRequest, SessionActionRequest
from .routers.travel_tools import router as travel_tools_router
from .service import TravelAssistantService

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Robotaxi Travel Assistant Demo")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.include_router(travel_tools_router)

service = TravelAssistantService()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/session/start")
def start_session():
    return service.start_session()


@app.post("/api/session/message")
def session_message(payload: MessageRequest):
    try:
        return service.handle_message(payload.session_id, payload.text)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    try:
        return service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/plan/revise")
def revise_plan(payload: RevisionRequest):
    try:
        return service.revise_plan(payload.session_id, payload.user_feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/plan/confirm")
def confirm_plan(payload: SessionActionRequest):
    try:
        return service.confirm_plan(payload.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/plan/share")
def share_plan(payload: SessionActionRequest):
    try:
        return service.share_plan(payload.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/mock/scenes")
def mock_scenes():
    return service.get_mock_scenes()
