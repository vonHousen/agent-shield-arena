"""FastAPI dashboard application for live arena events."""

from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common.src.event_emitter import DEFAULT_EVENTS_PATH
from dashboard.src.event_watcher import watch_events

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def create_app(events_file: Path = DEFAULT_EVENTS_PATH) -> FastAPI:
    """Create the dashboard FastAPI application.

    Args:
        events_file: JSONL file used as the arena event stream.
    """
    app = FastAPI(title="AgentShield Arena Dashboard")
    app.state.events_file = events_file

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        """Serve the dashboard single-page application."""
        return FileResponse(INDEX_FILE)

    @app.websocket("/ws")
    async def websocket_events(websocket: WebSocket) -> None:
        """Stream replayed and live arena events to a connected browser."""
        await websocket.accept()

        try:
            async for event in watch_events(app.state.events_file):
                await websocket.send_text(event.model_dump_json())
        except WebSocketDisconnect:
            return

    return app


app = create_app()


def main(
    events_file: Path = typer.Option(DEFAULT_EVENTS_PATH, help="JSONL file used as the arena event stream."),
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the dashboard server to."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind the dashboard server to."),
) -> None:
    """Run the dashboard development server."""
    uvicorn.run(create_app(events_file), host=host, port=port)


if __name__ == "__main__":
    typer.run(main)
