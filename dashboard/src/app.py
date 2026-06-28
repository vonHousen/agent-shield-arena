"""FastAPI dashboard application for live arena events."""

from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common.src.event_emitter import DEFAULT_EVENTS_PATH
from common.src.logging import setup_logging
from dashboard.src.event_watcher import ResetSignal, watch_events

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_LOG_FILE = Path("data/logs/dashboard.log")
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
INDEX_FILE = STATIC_DIR / "index.html"
RESET_MESSAGE = '{"type": "reset"}'


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
            async for message in watch_events(app.state.events_file):
                if isinstance(message, ResetSignal):
                    await websocket.send_text(RESET_MESSAGE)
                else:
                    await websocket.send_text(message.model_dump_json())
        except WebSocketDisconnect:
            return

    return app


app = create_app()


def main(
    events_file: Path = typer.Option(DEFAULT_EVENTS_PATH, help="JSONL file used as the arena event stream."),
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the dashboard server to."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind the dashboard server to."),
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG-level logging."),
    log_file: Path = typer.Option(DEFAULT_LOG_FILE, help=f"Log file path. Defaults to {DEFAULT_LOG_FILE}."),
) -> None:
    """Run the dashboard development server."""
    setup_logging(verbose=verbose, log_file=log_file)

    if reload:
        uvicorn.run(
            "dashboard.src.app:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["dashboard", "common"],
        )
    else:
        uvicorn.run(create_app(events_file), host=host, port=port)


if __name__ == "__main__":
    typer.run(main)
